from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    WEREWOLF = "werewolf"
    SEER     = "seer"
    DOCTOR   = "doctor"
    VILLAGER = "villager"


class Phase(str, Enum):
    NIGHT = "night"
    DAY   = "day"


class Pattern(str, Enum):
    BASELINE   = "Baseline"
    REFLECTION = "Reflection"
    REACT      = "ReAct"
    TOT        = "ToT"


@dataclass
class Player:
    id: int
    name: str
    role: Role
    pattern: Pattern
    alive: bool = True


@dataclass
class EliminationEvent:
    round: int
    phase: Phase
    player_id: int
    player_name: str
    role: Role
    cause: str  # "werewolf_kill" | "vote"


@dataclass
class VoteRecord:
    round: int
    voter_id: int
    target_id: int
    reason: str = ""


@dataclass
class SpeechRecord:
    round: int
    player_id: int
    text: str
    speech_round: int = 1
    position: int = 0   # 0-based position in bid order for this speech_round


@dataclass
class PassRecord:
    round: int
    speech_round: int
    player_id: int
    position: int = 0   # 0-based position in bid order


@dataclass
class BidRecord:
    round: int
    speech_round: int  # 1 or 2
    player_id: int
    bid: int  # 0-5; 0 = pass this speech round


@dataclass
class NightActionRecord:
    round: int
    actor_id: int
    role: Role
    target_id: int
    result: str | None = None  # seer: "werewolf"/"not werewolf", doctor: None


@dataclass
class RoundSummary:
    round: int

    # Static facts (rule-based, filled by engine)
    night_kill: str | None              # victim name; None = doctor saved
    day_eliminated: str | None          # voted-out name
    day_eliminated_role: Role | None    # role revealed on elimination
    votes: list[tuple[str, str, str]]   # [(voter_name, target_name, reason), ...]

    # Private knowledge (shown only to the relevant role)
    seer_check: tuple[str, str] | None  # (target_name, "werewolf"/"not werewolf")
    doctor_protected: str | None        # name of player protected this round

    # LLM-extracted from speeches
    accusations: list[tuple[str, str]]  # [(accuser, accused), ...]
    claims: list[tuple[str, str]]       # [(player, claim_text), ...]


@dataclass
class GameState:
    players: list[Player]
    round: int = 0
    phase: Phase = Phase.NIGHT
    eliminations: list[EliminationEvent] = field(default_factory=list)
    votes: list[VoteRecord] = field(default_factory=list)
    speeches: list[SpeechRecord] = field(default_factory=list)
    passes: list[PassRecord] = field(default_factory=list)
    night_actions: list[NightActionRecord] = field(default_factory=list)
    summaries: list[RoundSummary] = field(default_factory=list)
    bids: list[BidRecord] = field(default_factory=list)

    def bids_for(self, round: int, speech_round: int) -> list[BidRecord]:
        return [b for b in self.bids if b.round == round and b.speech_round == speech_round]

    def bid_text(self, speech_round: int) -> str:
        """Returns a public summary of bids for the given speech_round of the current round."""
        records = self.bids_for(self.round, speech_round)
        if not records:
            return ""
        lines = []
        for b in sorted(records, key=lambda x: -x.bid):
            p = self.get_player(b.player_id)
            action = "will pass" if b.bid == 0 else f"bid {b.bid}/5"
            lines.append(f"  {p.name}: {action}")
        return "Speaking interest bids (higher = speaks first):\n" + "\n".join(lines)

    # ── convenience ───────────────────────────────────────────

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def alive_werewolves(self) -> list[Player]:
        return [p for p in self.alive_players() if p.role == Role.WEREWOLF]

    def alive_villagers(self) -> list[Player]:
        return [p for p in self.alive_players() if p.role != Role.WEREWOLF]

    def get_player(self, player_id: int) -> Player:
        return next(p for p in self.players if p.id == player_id)

    def is_game_over(self) -> tuple[bool, str | None]:
        wolves = len(self.alive_werewolves())
        villagers = len(self.alive_villagers())
        if wolves == 0:
            return True, "village"
        if wolves >= villagers:
            return True, "werewolf"
        return False, None

    # ── game history as plain text (fed into agent prompts) ───

    def history_text(self, for_player: Player) -> str:
        lines: list[str] = []

        lines.append(f"=== GAME HISTORY (Round {self.round}) ===")
        lines.append(f"Your name: {for_player.name} | Your role: {for_player.role.value}")
        lines.append("")

        # ── CURRENT STATUS BLOCK ──────────────────────────────────
        lines.append("=== CURRENT STATUS ===")
        alive_names = [p.name + (" (you)" if p.id == for_player.id else "") for p in self.alive_players()]
        lines.append(f"Still in game:   {', '.join(alive_names)}")

        if self.eliminations:
            elim_parts = []
            for e in self.eliminations:
                cause = "killed at night" if e.cause == "werewolf_kill" else f"voted out R{e.round}"
                elim_parts.append(f"{e.player_name} ({cause}, role: {e.role.value})")
            lines.append(f"Eliminated:      {'; '.join(elim_parts)}")
            lines.append("NOTE: Eliminated players are NO LONGER in the game and cannot be voted for.")
        lines.append("=" * 22)
        lines.append("")

        # ── WEREWOLF PRIVATE KNOWLEDGE ────────────────────────────
        if for_player.role == Role.WEREWOLF:
            allies = [p for p in self.players if p.role == Role.WEREWOLF and p.id != for_player.id]
            if allies:
                lines.append(f"Your werewolf allies: {', '.join(p.name for p in allies)}")
            current_round_wolf_votes = [
                a for a in self.night_actions
                if a.round == self.round and a.role == Role.WEREWOLF and a.actor_id != for_player.id
            ]
            if current_round_wolf_votes:
                for a in current_round_wolf_votes:
                    actor = self.get_player(a.actor_id)
                    target = self.get_player(a.target_id)
                    lines.append(f"Your ally {actor.name} has chosen to target: {target.name}")
            lines.append("")

        # ── PAST ROUNDS: summarised ───────────────────────────────
        past_summaries = [s for s in self.summaries if s.round < self.round]
        if past_summaries:
            lines.append("=== PAST ROUNDS (summarised) ===")
            for s in past_summaries:
                lines.append(f"--- Round {s.round} Summary ---")

                # Night
                if s.night_kill:
                    note = " (no prior information existed to guide this choice)" if s.round == 1 else ""
                    lines.append(f"  Night: {s.night_kill} killed by werewolves{note}")
                else:
                    lines.append(f"  Night: No one killed — doctor saved someone")

                # Day
                if s.day_eliminated:
                    role_str = s.day_eliminated_role.value if s.day_eliminated_role else "unknown"
                    lines.append(f"  Day:   {s.day_eliminated} voted out (role: {role_str})")

                # Votes (reasons are private — not shown to other players)
                if s.votes:
                    vote_parts = ", ".join(f"{v}→{t}" for v, t, r in s.votes)
                    lines.append(f"  Votes: {vote_parts}")

                # Accusations & claims (LLM-extracted)
                if s.accusations:
                    acc_parts = ", ".join(f"{a} accused {b}" for a, b in s.accusations)
                    lines.append(f"  Accusations: {acc_parts}")
                if s.claims:
                    for player, claim in s.claims:
                        lines.append(f"  Claim — {player}: \"{claim}\"")

                # Private: seer
                if for_player.role == Role.SEER and s.seer_check:
                    target, result = s.seer_check
                    lines.append(f"  [Your investigation] {target} → {result}")

                # Private: doctor
                if for_player.role == Role.DOCTOR and s.doctor_protected:
                    lines.append(f"  [You protected] {s.doctor_protected}")

                lines.append("")
            lines.append("=" * 32)
            lines.append("")

        # ── CURRENT ROUND: full text ──────────────────────────────
        lines.append(f"=== ROUND {self.round} (current) ===")

        # Current round night result (if day phase)
        if self.phase == Phase.DAY:
            night_elim = next(
                (e for e in self.eliminations if e.round == self.round and e.phase == Phase.NIGHT), None
            )
            if night_elim:
                note = " No prior information existed to guide this choice." if self.round == 1 else ""
                lines.append(f"Night result: {night_elim.player_name} was killed (role: {night_elim.role.value}).{note}")
            else:
                lines.append("Night result: No one was killed — the doctor saved someone.")
            lines.append("")

        # Seer private: current round check (not yet in summaries)
        if for_player.role == Role.SEER:
            current_check = next(
                (a for a in self.night_actions
                 if a.actor_id == for_player.id and a.round == self.round), None
            )
            if current_check:
                target = self.get_player(current_check.target_id)
                lines.append(f"[Your investigation this round] {target.name} → {current_check.result}")
                lines.append("")

        # Doctor private: current round protection
        if for_player.role == Role.DOCTOR:
            current_protect = next(
                (a for a in self.night_actions
                 if a.actor_id == for_player.id and a.round == self.round), None
            )
            if current_protect:
                target = self.get_player(current_protect.target_id)
                lines.append(f"[You protected this round] {target.name}")
                lines.append("")

        # Current round bids (public — shown before speeches)
        for sr in [1, 2]:
            bid_summary = self.bid_text(sr)
            if bid_summary:
                lines.append(f"--- Round {self.round} Discussion Round {sr} Bids ---")
                lines.append(bid_summary)
                lines.append("")

        # Current round speeches
        current_speeches = [s for s in self.speeches if s.round == self.round]
        if current_speeches:
            lines.append(f"--- Round {self.round} Speeches ---")
            for s in current_speeches:
                p = self.get_player(s.player_id)
                lines.append(f"  {p.name}: {s.text}")
            lines.append("")

        # Current round votes
        current_votes = [v for v in self.votes if v.round == self.round]
        if current_votes:
            lines.append(f"--- Round {self.round} Votes (so far) ---")
            for v in current_votes:
                voter = self.get_player(v.voter_id)
                target = self.get_player(v.target_id)
                lines.append(f"  {voter.name} → {target.name}")
            lines.append("")

        return "\n".join(lines)

    # ── tool outputs for ReAct ─────────────────────────────────

    def tool_alive_players(self) -> str:
        return ", ".join(p.name for p in self.alive_players())

    def tool_voting_history(self) -> str:
        lines = []
        # Past rounds from summaries (reasons are private — not shown)
        for s in self.summaries:
            for voter, target, reason in s.votes:
                lines.append(f"Round {s.round}: {voter} voted for {target}")
        # Current round from raw votes
        for v in self.votes:
            if v.round == self.round:
                voter = self.get_player(v.voter_id)
                target = self.get_player(v.target_id)
                lines.append(f"Round {v.round}: {voter.name} voted for {target.name}")
        return "\n".join(lines) if lines else "No votes yet."

    def tool_speech_log(self, player_name: str) -> str:
        lines = []
        # Past rounds: claims and accusations from summaries
        for s in self.summaries:
            for player, claim in s.claims:
                if player.lower() == player_name.lower():
                    lines.append(f"Round {s.round} (claim): {claim}")
            for accuser, accused in s.accusations:
                if accuser.lower() == player_name.lower():
                    lines.append(f"Round {s.round} (accused): {accused}")
        # Current round: full speech text
        for s in self.speeches:
            if s.round == self.round:
                p = self.get_player(s.player_id)
                if p.name.lower() == player_name.lower():
                    lines.append(f"Round {s.round}: {s.text}")
        return "\n".join(lines) if lines else f"No speeches from {player_name}."

    def tool_elimination_history(self) -> str:
        if not self.eliminations:
            return "No eliminations yet."
        return "\n".join(
            f"Round {e.round} ({e.phase.value}): {e.player_name} eliminated — was {e.role.value}"
            for e in self.eliminations
        )

    def tool_suspicion_graph(self) -> str:
        tally: dict[str, int] = {}
        # Past rounds from summaries
        for s in self.summaries:
            for _, target, _reason in s.votes:
                tally[target] = tally.get(target, 0) + 1
        # Current round from raw votes
        for v in self.votes:
            if v.round == self.round:
                target = self.get_player(v.target_id)
                tally[target.name] = tally.get(target.name, 0) + 1
        if not tally:
            return "No votes yet — suspicion graph empty."
        lines = sorted(tally.items(), key=lambda x: -x[1])
        return "\n".join(f"  {name}: {count} vote(s) against" for name, count in lines)

    def tool_player_summary(self, player_name: str) -> str:
        lines = []
        for s in self.summaries:
            facts = []
            for accuser, accused in s.accusations:
                if accused.lower() == player_name.lower():
                    facts.append(f"accused by {accuser}")
                if accuser.lower() == player_name.lower():
                    facts.append(f"accused {accused}")
            for voter, target, reason in s.votes:
                if voter.lower() == player_name.lower():
                    facts.append(f"voted for {target}")
                if target.lower() == player_name.lower():
                    facts.append(f"received vote from {voter}")
            for player, claim in s.claims:
                if player.lower() == player_name.lower():
                    facts.append(f"claimed: \"{claim}\"")
            if facts:
                lines.append(f"Round {s.round}: " + "; ".join(facts))
        return "\n".join(lines) if lines else f"No recorded history for {player_name}."
