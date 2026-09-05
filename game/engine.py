from __future__ import annotations
import random
from collections import Counter
from .state import (
    GameState, Player, Role, Phase,
    EliminationEvent, VoteRecord, SpeechRecord, PassRecord, NightActionRecord, RoundSummary, BidRecord,
)
from .llm import reset_call_log, get_call_log, call_llm

MAX_ROUNDS = 10


def run_game(players: list[Player], verbose: bool = True) -> dict:
    reset_call_log()
    state = GameState(players=players)

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    for round_num in range(1, MAX_ROUNDS + 1):
        state.round = round_num
        log(f"\n{'='*50}")
        log(f"ROUND {round_num}")

        # ── NIGHT PHASE ───────────────────────────────────
        state.phase = Phase.NIGHT
        log(f"--- Night Phase ---")

        protected_id: int | None = None
        killed_id: int | None = None
        seer_result: tuple[int, str] | None = None

        for player in state.alive_players():
            agent = player._agent  # attached by tournament runner

            if player.role == Role.SEER:
                target_name = agent.night_action(state)
                target = _find_player(state, target_name)
                result = "werewolf" if target.role == Role.WEREWOLF else "not werewolf"
                state.night_actions.append(NightActionRecord(
                    round=round_num, actor_id=player.id, role=Role.SEER,
                    target_id=target.id, result=result,
                ))
                seer_result = (target.id, result)
                log(f"  [Seer] {player.name} investigates {target.name} -> {result}")

            elif player.role == Role.DOCTOR:
                target_name = agent.night_action(state)
                target = _find_player(state, target_name)
                protected_id = target.id
                state.night_actions.append(NightActionRecord(
                    round=round_num, actor_id=player.id, role=Role.DOCTOR,
                    target_id=target.id,
                ))
                log(f"  [Doctor] {player.name} protects {target.name}")

        # Werewolves vote on kill target — two-round symmetric protocol:
        # Round 1: random order, each wolf sees previous wolf's choice via state.
        # Round 2 (only if no consensus): reversed order, same visibility.
        # If still no consensus after round 2: random tiebreak among nominees.
        wolves = [p for p in state.alive_players() if p.role == Role.WEREWOLF]
        random.shuffle(wolves)

        def _wolf_vote_round(order: list) -> list[str]:
            targets = []
            for player in order:
                target_name = player._agent.night_action(state)
                target = _find_player(state, target_name)
                targets.append(target_name)
                state.night_actions.append(NightActionRecord(
                    round=round_num, actor_id=player.id, role=Role.WEREWOLF,
                    target_id=target.id,
                ))
                log(f"  [Werewolf] {player.name} targets {target_name}")
            return targets

        wolf_targets = _wolf_vote_round(wolves)

        # Check consensus
        top = Counter(wolf_targets).most_common(1)[0]
        if top[1] < len(wolves) and len(wolves) > 1:
            # No consensus — strip round-1 werewolf entries and retry reversed
            state.night_actions = [
                a for a in state.night_actions
                if not (a.round == round_num and a.role == Role.WEREWOLF)
            ]
            log(f"  [Werewolf] No consensus — retrying reversed order")
            wolf_targets = _wolf_vote_round(list(reversed(wolves)))
            top = Counter(wolf_targets).most_common(1)[0]

        kill_name = top[0]
        kill_player = _find_player(state, kill_name)
        killed_id = kill_player.id

        if killed_id is not None and killed_id != protected_id:
            victim = state.get_player(killed_id)
            victim.alive = False
            state.eliminations.append(EliminationEvent(
                round=round_num, phase=Phase.NIGHT,
                player_id=victim.id, player_name=victim.name,
                role=victim.role, cause="werewolf_kill",
            ))
            log(f"  [Night result] {victim.name} was killed")
        elif killed_id == protected_id:
            log(f"  [Night result] Doctor saved the target — no elimination")
        else:
            log(f"  [Night result] No kill")

        over, winner = state.is_game_over()
        if over:
            log(f"\n>>> GAME OVER — {winner.upper()} wins after round {round_num} night <<<")
            break

        # ── DAY PHASE ─────────────────────────────────────
        state.phase = Phase.DAY
        log(f"--- Day Phase ---")

        # Announce night result
        if state.eliminations and state.eliminations[-1].round == round_num:
            last = state.eliminations[-1]
            log(f"  Announcement: {last.player_name} was eliminated last night. Their role was {last.role.value}.")

        # Speeches — 2 discussion rounds with bid-ordered speaking
        # Track last-round speaking position for tiebreaking (higher index = spoke later = goes first next round)
        prev_positions: dict[int, int] = {}  # player_id -> position in previous bid order (0-based)

        for speech_round in [1, 2]:
            # Collect bids from all alive players simultaneously (each unaware of others' bids)
            raw_bids: dict[int, int] = {}
            for player in state.alive_players():
                b = player._agent.bid(state, speech_round=speech_round)
                raw_bids[player.id] = max(0, min(5, b))  # clamp to [0,5]
                state.bids.append(BidRecord(round=round_num, speech_round=speech_round,
                                            player_id=player.id, bid=raw_bids[player.id]))

            bid_summary = state.bid_text(speech_round)
            log(f"  -- Discussion round {speech_round} bids --\n{bid_summary}")

            # Sort: descending bid; tiebreak by previous position (higher prev_pos = earlier this round)
            def _sort_key(p: Player) -> tuple:
                return (-raw_bids[p.id], -prev_positions.get(p.id, -1))

            order = sorted(state.alive_players(), key=_sort_key)
            order_names = [p.name for p in order]
            log(f"  -- Discussion round {speech_round} -- order: {', '.join(order_names)}")

            for pos, player in enumerate(order):
                prev_positions[player.id] = pos
                if raw_bids[player.id] == 0:
                    state.passes.append(PassRecord(round=round_num, speech_round=speech_round, player_id=player.id, position=pos))
                    log(f"  [{player.name}]: [bid 0 — passes]")
                    continue
                speech = player._agent.speak(state, speech_round=speech_round, speech_order=order_names)
                if speech and speech.strip().upper() != "PASS":
                    state.speeches.append(SpeechRecord(round=round_num, player_id=player.id, text=speech, speech_round=speech_round, position=pos))
                    log(f"  [{player.name}]: {speech}")
                else:
                    state.passes.append(PassRecord(round=round_num, speech_round=speech_round, player_id=player.id, position=pos))
                    log(f"  [{player.name}]: [passes]")

        # Voting — random order, each voter sees all previous votes via state
        vote_order = state.alive_players()
        random.shuffle(vote_order)
        vote_tally: Counter = Counter()
        for player in vote_order:
            raw_vote = player._agent.vote(state)
            # Parse "<name> — <reason>" format; fall back to raw if no separator
            if " — " in raw_vote:
                name_part, reason_part = raw_vote.split(" — ", 1)
            else:
                name_part, reason_part = raw_vote, ""
            target = _find_player(state, name_part.strip(), exclude_id=player.id)
            state.votes.append(VoteRecord(
                round=round_num, voter_id=player.id, target_id=target.id, reason=reason_part.strip()
            ))
            vote_tally[target.id] += 1
            reason_log = f' — "{reason_part.strip()}"' if reason_part.strip() else ""
            log(f"  [{player.name}] votes for {target.name}{reason_log}")

        # Eliminate most-voted (random tiebreak)
        max_votes = max(vote_tally.values())
        candidates = [pid for pid, cnt in vote_tally.items() if cnt == max_votes]
        eliminated_id = random.choice(candidates)
        eliminated = state.get_player(eliminated_id)
        eliminated.alive = False
        state.eliminations.append(EliminationEvent(
            round=round_num, phase=Phase.DAY,
            player_id=eliminated.id, player_name=eliminated.name,
            role=eliminated.role, cause="vote",
        ))
        log(f"  [Vote result] {eliminated.name} eliminated (role: {eliminated.role.value})")

        over, winner = state.is_game_over()

        # Build round summary before checking game over
        summary = _build_round_summary(state, round_num)
        state.summaries.append(summary)
        log(f"  [Summary R{round_num}] built — accusations: {len(summary.accusations)}, claims: {len(summary.claims)}")

        if over:
            log(f"\n>>> GAME OVER — {winner.upper()} wins after round {round_num} day <<<")
            break
    else:
        # Round cap reached — werewolves win by default
        winner = "werewolf"
        log(f"\n>>> ROUND CAP REACHED — werewolf wins by default <<<")

    return _build_result(state, winner)


def _build_round_summary(state: GameState, round_num: int) -> RoundSummary:
    # Night kill
    night_elim = next(
        (e for e in state.eliminations if e.round == round_num and e.phase == Phase.NIGHT), None
    )
    night_kill = night_elim.player_name if night_elim else None

    # Day elimination
    day_elim = next(
        (e for e in state.eliminations if e.round == round_num and e.phase == Phase.DAY), None
    )
    day_eliminated = day_elim.player_name if day_elim else None
    day_eliminated_role = day_elim.role if day_elim else None

    # Votes for this round
    votes: list[tuple[str, str, str]] = []
    for v in state.votes:
        if v.round == round_num:
            voter = state.get_player(v.voter_id)
            target = state.get_player(v.target_id)
            votes.append((voter.name, target.name, v.reason))

    # Seer check this round
    seer_action = next(
        (a for a in state.night_actions if a.round == round_num and a.role == Role.SEER), None
    )
    seer_check: tuple[str, str] | None = None
    if seer_action:
        target = state.get_player(seer_action.target_id)
        seer_check = (target.name, seer_action.result or "")

    # Doctor protection this round
    doctor_action = next(
        (a for a in state.night_actions if a.round == round_num and a.role == Role.DOCTOR), None
    )
    doctor_protected: str | None = None
    if doctor_action:
        doctor_protected = state.get_player(doctor_action.target_id).name

    # LLM extraction of accusations and claims from speeches
    round_speeches = [s for s in state.speeches if s.round == round_num]
    accusations, claims = _extract_accusations_claims(state, round_speeches, round_num)

    return RoundSummary(
        round=round_num,
        night_kill=night_kill,
        day_eliminated=day_eliminated,
        day_eliminated_role=day_eliminated_role,
        votes=votes,
        seer_check=seer_check,
        doctor_protected=doctor_protected,
        accusations=accusations,
        claims=claims,
    )


def _extract_accusations_claims(
    state: GameState,
    speeches: list,
    round_num: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    if not speeches:
        return [], []

    speech_block = "\n".join(
        f"{state.get_player(s.player_id).name}: {s.text}"
        for s in speeches
    )
    player_names = ", ".join(p.name for p in state.players)

    prompt = (
        f"Players in this game: {player_names}\n\n"
        f"Round {round_num} speeches:\n{speech_block}\n\n"
        "Extract the following from these speeches:\n"
        "1. ACCUSATIONS: when a player directly or indirectly accuses another of being a werewolf.\n"
        "2. CLAIMS: when a player claims a special role (seer, doctor) or makes a significant "
        "strategic claim (e.g. 'I investigated X', 'I protected Y').\n\n"
        "Format your answer EXACTLY as:\n"
        "ACCUSATIONS:\n"
        "<accuser> accused <accused>\n"
        "(one per line, or 'none' if there are none)\n\n"
        "CLAIMS:\n"
        "<player>: <claim>\n"
        "(one per line, or 'none' if there are none)"
    )

    raw = call_llm(f"engine.extract_r{round_num}", prompt)

    accusations: list[tuple[str, str]] = []
    claims: list[tuple[str, str]] = []

    section = None
    valid_names_lower = {p.name.lower(): p.name for p in state.players}

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("ACCUSATIONS"):
            section = "acc"
            continue
        if line.upper().startswith("CLAIMS"):
            section = "claim"
            continue
        if line.lower() == "none":
            continue

        if section == "acc":
            # Expect "X accused Y"
            parts = line.lower().split(" accused ")
            if len(parts) == 2:
                accuser = valid_names_lower.get(parts[0].strip())
                accused = valid_names_lower.get(parts[1].strip())
                if accuser and accused:
                    accusations.append((accuser, accused))
        elif section == "claim":
            # Expect "X: claim text"
            if ": " in line:
                name_part, claim_text = line.split(": ", 1)
                name = valid_names_lower.get(name_part.strip().lower())
                if name and claim_text.strip():
                    claims.append((name, claim_text.strip()))

    return accusations, claims


def _find_player(state: GameState, name: str, exclude_id: int | None = None) -> Player:
    name = name.strip().rstrip(".,!")
    alive = [p for p in state.alive_players() if p.id != exclude_id]
    if not alive:
        alive = state.alive_players()
    for p in alive:
        if p.name.lower() == name.lower():
            return p
    # fuzzy fallback
    for p in alive:
        if p.name.lower() in name.lower() or name.lower() in p.name.lower():
            return p
    return random.choice(alive)


def _build_result(state: GameState, winner: str) -> dict:
    from game.llm import MODEL as _MODEL
    call_log = get_call_log()
    total_tokens = sum(c["total_tokens"] for c in call_log)
    total_calls = len(call_log)
    total_time = round(sum(c["elapsed_sec"] for c in call_log), 2)

    # Detection accuracy: fraction of day eliminations that were werewolves (turn-level)
    day_elims = [e for e in state.eliminations if e.cause == "vote"]
    wolf_elims = [e for e in day_elims if e.role == Role.WEREWOLF]
    detection_accuracy = len(wolf_elims) / len(day_elims) if day_elims else 0.0

    # Vote accuracy: fraction of non-werewolf votes cast for a werewolf (individual-level)
    # Only counts votes by villagers, seer, and doctor — werewolves know who to vote for.
    player_role = {p.id: p.role for p in state.players}
    village_votes = [v for v in state.votes if player_role[v.voter_id] != Role.WEREWOLF]
    correct_village_votes = [v for v in village_votes if player_role[v.target_id] == Role.WEREWOLF]
    vote_accuracy = len(correct_village_votes) / len(village_votes) if village_votes else 0.0

    # Per-pattern vote accuracy (non-werewolf voters only)
    pattern_vote: dict[str, dict] = {}
    player_pattern = {p.id: p.pattern.value for p in state.players}
    for v in village_votes:
        pat = player_pattern[v.voter_id]
        if pat not in pattern_vote:
            pattern_vote[pat] = {"correct": 0, "total": 0}
        pattern_vote[pat]["total"] += 1
        if player_role[v.target_id] == Role.WEREWOLF:
            pattern_vote[pat]["correct"] += 1
    pattern_vote_accuracy = {
        pat: round(d["correct"] / d["total"], 3) if d["total"] else 0.0
        for pat, d in pattern_vote.items()
    }

    # Survival rounds per pattern
    survival: dict[str, list[int]] = {}
    for p in state.players:
        pattern = p.pattern.value
        elim = next((e for e in state.eliminations if e.player_id == p.id), None)
        rounds_survived = elim.round if elim else state.round
        survival.setdefault(pattern, []).append(rounds_survived)

    survival_avg = {k: round(sum(v) / len(v), 2) for k, v in survival.items()}

    # Per-pattern call stats
    pattern_calls: dict[str, dict] = {}
    for c in call_log:
        caller = c["caller"]
        pattern = caller.split("[")[1].split("]")[0] if "[" in caller else "unknown"
        if pattern not in pattern_calls:
            pattern_calls[pattern] = {"calls": 0, "tokens": 0, "elapsed_sec": 0.0}
        pattern_calls[pattern]["calls"] += 1
        pattern_calls[pattern]["tokens"] += c["total_tokens"]
        pattern_calls[pattern]["elapsed_sec"] += c["elapsed_sec"]

    return {
        "winner": winner,
        "rounds": state.round,
        "model": _MODEL,
        "players": [
            {"id": p.id, "name": p.name, "role": p.role.value, "pattern": p.pattern.value}
            for p in state.players
        ],
        "eliminations": [
            {"round": e.round, "phase": e.phase.value, "player": e.player_name,
             "role": e.role.value, "cause": e.cause}
            for e in state.eliminations
        ],
        "detection_accuracy": round(detection_accuracy, 3),
        "vote_accuracy": round(vote_accuracy, 3),
        "vote_accuracy_by_pattern": pattern_vote_accuracy,
        "survival_avg_rounds": survival_avg,
        "api": {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_elapsed_sec": total_time,
            "per_pattern": pattern_calls,
        },
        "call_log": call_log,
        "night_actions": [
            {
                "round": a.round,
                "actor": state.get_player(a.actor_id).name,
                "role": a.role.value,
                "target": state.get_player(a.target_id).name,
                "result": a.result,
            }
            for a in state.night_actions
        ],
        "speeches": [
            {"round": s.round, "speech_round": s.speech_round, "position": s.position, "player_id": s.player_id, "text": s.text}
            for s in state.speeches
        ],
        "passes": [
            {"round": p.round, "speech_round": p.speech_round, "position": p.position, "player_id": p.player_id}
            for p in state.passes
        ],
        "votes": [
            {"round": v.round, "voter": state.get_player(v.voter_id).name,
             "target": state.get_player(v.target_id).name, "reason": v.reason}
            for v in state.votes
        ],
        "bids": [
            {"round": b.round, "speech_round": b.speech_round, "player_id": b.player_id, "bid": b.bid}
            for b in state.bids
        ],
    }
