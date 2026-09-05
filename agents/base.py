from __future__ import annotations
import re
from abc import ABC, abstractmethod
from game.state import GameState, Player, Role
from game.llm import call_llm


GAME_RULES = (
    "GAME RULES:\n"
    "- There are 8 players: 2 werewolves, 1 seer, 1 doctor, 4 villagers.\n"
    "- Each round has two phases: Night, then Day.\n"
    "- Night phase: Werewolves secretly choose one player to eliminate. "
    "The seer investigates one player and privately learns their true role. "
    "The doctor chooses one player to protect from elimination that night. "
    "Villagers take no action at night.\n"
    "- Day phase: All surviving players discuss and then vote. "
    "The player with the most votes is eliminated and their role is revealed to everyone. "
    "Ties are broken randomly.\n"
    "- Discussion works as follows: there are 2 discussion rounds per day. "
    "At the start of each round, every surviving player simultaneously declares a speaking interest bid (0–5). "
    "Bids are revealed at the same time, and the speaking order is determined by bid value — "
    "higher bids speak first, lower bids speak later. "
    "A player who bids 0 passes and does not speak that round. "
    "You will be told the speaking order at the start of each discussion round — "
    "do not expect players to speak outside their turn.\n"
    "- Werewolves win if their number equals or exceeds the number of remaining non-werewolf players.\n"
    "- The village wins if all werewolves are eliminated.\n"
    "- Only you know your own role. Other players' roles are hidden "
    "unless revealed by elimination or announced by another player.\n"
    "- Team dynamics: werewolves form one team; villagers, seer, and doctor form the opposing team. "
    "All players may use any strategy to win — including manipulation, bluffing, lying, and social pressure. "
    "Werewolves must avoid detection and eliminate the village; "
    "the village must identify and eliminate the werewolves through observation, logic, and persuasion."
)

ROLE_INSTRUCTIONS: dict[Role, str] = {
    Role.WEREWOLF: (
        "You are a werewolf. You know who your fellow werewolf is, but no one else does. "
        "Your goal is to avoid detection and eliminate villagers. "
        "During the day, blend in, deflect suspicion, and vote out non-werewolves. "
        "Never reveal that you are a werewolf."
    ),
    Role.SEER: (
        "You are the seer. Each night you investigate one player and privately learn their true role. "
        "Your investigation result is known only to you — you decide when and whether to share it. "
        "Use this information to guide the village, but be careful: "
        "if werewolves identify you, they will kill you. "
        "Your goal is to help the village eliminate all werewolves."
    ),
    Role.DOCTOR: (
        "You are the doctor. Each night you choose one player to protect from elimination. "
        "Your goal is to guess who the werewolves will target that night — "
        "if you protect the right person, the werewolves cannot eliminate anyone that round. "
        "You may protect yourself. Your protection is anonymous: "
        "no one is told who you protected or whether your protection succeeded. "
        "Your goal is to help the village survive."
    ),
    Role.VILLAGER: (
        "You are a villager. You have no special abilities and take no action at night. "
        "Your only tools are daytime discussion and voting. "
        "Use logic, observation, and persuasion to identify and vote out werewolves. "
        "Your goal is to help the village eliminate all werewolves. "
        "The seer and doctor are on your team — they share your goal of eliminating the werewolves. "
        "The seer privately investigates players each night and may or may not reveal what they learn; "
        "the doctor secretly protects someone each night. "
        "Keep this alliance in mind when reasoning about who to trust."
    ),
}


class BaseAgent(ABC):
    def __init__(self, player: Player):
        self.player = player

    def _system_prompt(self) -> str:
        return (
            "You are playing a game of Werewolf (also known as Mafia).\n"
            f"{GAME_RULES}\n\n"
            f"{ROLE_INSTRUCTIONS[self.player.role]}\n"
            "Be concise. Do not break character."
        )

    def _extract_name(self, raw: str, valid_names: list[str]) -> str | None:
        """Return the first valid name found in raw, or None if none match."""
        cleaned = raw.strip().rstrip(".,!")
        for name in valid_names:
            if name.lower() in cleaned.lower():
                return name
        return None

    def _pick_name(self, raw: str, valid_names: list[str], caller: str) -> str:
        """Extract a valid player name from raw; retry once with a correction prompt if not found."""
        result = self._extract_name(raw, valid_names)
        if result is not None:
            return result
        names_str = ", ".join(valid_names)
        retry_raw = call_llm(
            f"{caller}.format_retry",
            f"Your previous answer was: \"{raw}\"\n"
            f"That did not match any valid player name.\n"
            f"Choose exactly ONE name from this list: {names_str}\n"
            "Reply with only the player's name, nothing else.",
            self._system_prompt(),
        )
        result = self._extract_name(retry_raw, valid_names)
        return result if result is not None else valid_names[0]

    def _night_task(self, candidates: list) -> str:
        names = ", ".join(p.name for p in candidates)
        if self.player.role == Role.SEER:
            return (
                f"It is night. Choose ONE player to investigate.\n"
                f"You will privately learn whether they are a werewolf or not.\n"
                f"Choose from: {names}\n"
                "Reply with only the player's name, nothing else."
            )
        elif self.player.role == Role.DOCTOR:
            return (
                f"It is night. Choose ONE player to protect from elimination tonight.\n"
                f"If the werewolves target the same player, no one will be eliminated this round.\n"
                f"You may protect yourself. Your choice is anonymous.\n"
                f"Choose from: {names}\n"
                "Reply with only the player's name, nothing else."
            )
        else:  # WEREWOLF
            return (
                f"It is night. Choose ONE player to eliminate.\n"
                f"Choose from: {names}\n"
                "Reply with only the player's name, nothing else."
            )

    def bid(self, state: GameState, speech_round: int = 1) -> int:
        """Return speaking interest bid (0-5) for this discussion round.
        0 = pass (will not speak). Higher = more eager to speak first.
        Bids are collected simultaneously before speaking order is revealed.
        Default implementation: single LLM call. Subclasses may override."""
        context = state.history_text(self.player)
        prompt = (
            f"{context}\n\n"
            f"Before discussion round {speech_round} begins, you must declare your speaking interest.\n"
            "Rate how eager you are to speak FIRST this round on a scale of 0 to 5:\n"
            "  0 = I will pass and say nothing this round\n"
            "  1 = I have little to say, prefer to listen\n"
            "  2 = I have something minor to add\n"
            "  3 = I have a moderate point to make\n"
            "  4 = I have something important to say\n"
            "  5 = I urgently need to speak first\n"
            "Everyone submits their bid simultaneously — you cannot see others' bids yet.\n"
            "After all bids are revealed, higher bids speak first.\n"
            "Reply with only a single integer (0, 1, 2, 3, 4, or 5)."
        )
        caller = f"{self.player.name}[{self.player.pattern.value}].bid_r{speech_round}"
        raw = call_llm(caller, prompt, self._system_prompt())
        # Extract first digit found
        import re
        m = re.search(r"[0-5]", raw.strip())
        return int(m.group()) if m else 3  # default to 3 if parse fails

    @abstractmethod
    def speak(self, state: GameState, speech_round: int = 1) -> str:
        """Return a speech string for the day discussion phase.
        speech_round=1: opening statement, speech_round=2: reactive response."""

    @abstractmethod
    def vote(self, state: GameState) -> str:
        """Return the name of the player to vote for elimination."""

    @abstractmethod
    def night_action(self, state: GameState) -> str:
        """Return the name of the target player for the night action.
        Werewolf: player to kill. Seer: player to investigate. Doctor: player to protect.
        Villagers do not call this method."""
