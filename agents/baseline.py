from __future__ import annotations
from game.state import GameState, Player
from game.llm import call_llm
from agents.base import BaseAgent


class BaselineAgent(BaseAgent):
    def speak(self, state: GameState, speech_round: int = 1, speech_order: list | None = None) -> str:
        instruction = _speech_instruction(speech_round, speech_order)
        prompt = f"{state.history_text(self.player)}\n\n{instruction}"
        return call_llm(f"{self.player.name}[Baseline].speak", prompt, self._system_prompt())

    def vote(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        prompt = (
            f"{state.history_text(self.player)}\n\n"
            f"It is time to vote. Choose ONE player to eliminate from: {names}\n"
            "Reply with the player's name followed by a one-sentence reason.\n"
            "Your reason is recorded for analysis but is NOT shown to other players — be honest.\n"
            "Format: <name> — <reason>"
        )
        caller = f"{self.player.name}[Baseline].vote"
        raw = call_llm(caller, prompt, self._system_prompt())
        return raw

    def night_action(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        prompt = (
            f"{state.history_text(self.player)}\n\n"
            f"{self._night_task(candidates)}"
        )
        caller = f"{self.player.name}[Baseline].night"
        raw = call_llm(caller, prompt, self._system_prompt())
        return self._pick_name(raw, [p.name for p in candidates], caller)


def _speech_instruction(speech_round: int, speech_order: list | None = None) -> str:
    order_str = ""
    if speech_order:
        order_str = f" Speaking order this round: {', '.join(speech_order)}."
    common = (
        "Write ONLY what you say out loud to the other players. "
        "Do not include internal thoughts, reasoning, or meta-commentary. "
        "Your reply is your spoken statement — nothing else."
    )
    if speech_round == 1:
        return (
            f"It is discussion round 1 of 2.{order_str} "
            "No one has spoken yet this round. Say whatever you think is appropriate, or stay silent.\n"
            f"If you choose to speak, reply with your spoken statement. {common}\n"
            "If you choose to stay silent, reply with only: PASS"
        )
    else:
        return (
            f"It is discussion round 2 of 2 — the final round before voting.{order_str} "
            "You have heard the first round of speeches. Respond if you wish, or stay silent.\n"
            f"If you choose to speak, reply with your spoken statement. {common}\n"
            "If you choose to stay silent, reply with only: PASS"
        )


def _extract_name(raw: str, valid_names: list[str]) -> str:
    raw = raw.strip().rstrip(".,!")
    for name in valid_names:
        if name.lower() in raw.lower():
            return name
    return valid_names[0]
