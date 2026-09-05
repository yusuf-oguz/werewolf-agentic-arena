from __future__ import annotations
from game.state import GameState, Player
from game.llm import call_llm
from agents.base import BaseAgent
from agents.baseline import _speech_instruction

MAX_RETRIES = 2


class ReflectionAgent(BaseAgent):
    def bid(self, state: GameState, speech_round: int = 1) -> int:
        import re
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
        caller = f"{self.player.name}[Reflection].bid_r{speech_round}"
        draft = call_llm(f"{caller}.draft", prompt, self._system_prompt())

        current_bid = draft.strip()
        for _ in range(MAX_RETRIES):
            critique = call_llm(
                f"{caller}.critique",
                f"{context}\n\nYou are about to declare a speaking interest bid of: {current_bid}\n"
                "Evaluate this bid on four criteria:\n"
                "1. Is it consistent with your current strategic position?\n"
                "2. Does it accurately reflect how much valuable information you have to share?\n"
                "3. Does it avoid signalling your true role?\n"
                "4. Does this bid increase your probability of winning the game given your role and the current game state?\n"
                "If all four pass, reply with only: APPROVE\n"
                "Otherwise reply with: REVISE: <integer 0-5>",
                self._system_prompt(),
            )
            if critique.strip().upper().startswith("APPROVE"):
                break
            revision_note = critique.replace("REVISE:", "").strip()
            revised = call_llm(
                f"{caller}.revise",
                f"{context}\n\nYour current bid: {current_bid}\n"
                f"Revision instruction: {revision_note}\n\n"
                "Reply with only a single integer (0, 1, 2, 3, 4, or 5).",
                self._system_prompt(),
            )
            m_rev = re.search(r"[0-5]", revised.strip())
            if m_rev:
                current_bid = m_rev.group()

        m = re.search(r"[0-5]", current_bid)
        return int(m.group()) if m else 3

    def speak(self, state: GameState, speech_round: int = 1, speech_order: list | None = None) -> str:
        context = state.history_text(self.player)
        instruction = _speech_instruction(speech_round, speech_order)
        draft = call_llm(
            f"{self.player.name}[Reflection].speak.draft",
            f"{context}\n\n{instruction}",
            self._system_prompt(),
        )

        for _ in range(MAX_RETRIES):
            critique = call_llm(
                f"{self.player.name}[Reflection].speak.critique",
                f"{context}\n\nYour draft speech:\n{draft}\n\n"
                "Evaluate this speech on four criteria:\n"
                "1. Consistent with past statements (no contradictions)?\n"
                "2. Does NOT reveal your true role?\n"
                "3. Persuasive and natural-sounding?\n"
                "4. Does this speech increase your probability of winning the game given your role and the current game state?\n"
                "If all four pass, reply with only: APPROVE\n"
                "Otherwise reply with: REVISE: <short instruction>",
                self._system_prompt(),
            )
            if critique.strip().upper().startswith("APPROVE"):
                break
            revision_note = critique.replace("REVISE:", "").strip()
            draft = call_llm(
                f"{self.player.name}[Reflection].speak.revise",
                f"{context}\n\nYour previous draft:\n{draft}\n\n"
                f"Revision instruction: {revision_note}\n\n"
                "Write ONLY the improved spoken statement — no internal thoughts or meta-commentary. "
                "Or reply with only PASS to stay silent.",
                self._system_prompt(),
            )

        return draft

    def vote(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        context = state.history_text(self.player)

        draft = call_llm(
            f"{self.player.name}[Reflection].vote.draft",
            f"{context}\n\nIt is time to vote. Choose ONE player to eliminate from: {names}\n"
            "Reply with the player's name followed by a one-sentence reason.\n"
            "Your reason is recorded for analysis but is NOT shown to other players — be honest.\n"
            "Format: <name> — <reason>",
            self._system_prompt(),
        )

        for _ in range(MAX_RETRIES):
            critique = call_llm(
                f"{self.player.name}[Reflection].vote.critique",
                f"{context}\n\nYou are about to vote for: {draft.strip()}\n"
                "Evaluate this vote on four criteria:\n"
                "1. Consistent with your past statements (no contradictions)?\n"
                "2. Does NOT reveal your true role?\n"
                "3. Is your honest reason strategically sound?\n"
                "4. Does this vote increase your probability of winning the game given your role and the current game state?\n"
                "If all four pass, reply with only: APPROVE\n"
                "If not, reply: REVISE: <name of better target — one-sentence reason>",
                self._system_prompt(),
            )
            if critique.strip().upper().startswith("APPROVE"):
                break
            revision_note = critique.replace("REVISE:", "").strip()
            draft = call_llm(
                f"{self.player.name}[Reflection].vote.revise",
                f"{context}\n\nRevision: {revision_note}\n"
                f"Choose ONE player to vote for from: {names}\n"
                "Reply with the player's name followed by a one-sentence reason.\n"
                "Your reason is recorded for analysis but is NOT shown to other players — be honest.\n"
                "Format: <name> — <reason>",
                self._system_prompt(),
            )

        return draft

    def night_action(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        context = state.history_text(self.player)

        draft = call_llm(
            f"{self.player.name}[Reflection].night.draft",
            f"{context}\n\n{self._night_task(candidates)}",
            self._system_prompt(),
        )

        for _ in range(MAX_RETRIES):
            critique = call_llm(
                f"{self.player.name}[Reflection].night.critique",
                f"{context}\n\nYou chose: {draft.strip()}\n"
                "Evaluate this night action on four criteria:\n"
                "1. Is it consistent with information you have gathered so far?\n"
                "2. Does it avoid signalling your true role?\n"
                "3. Is it the most strategically sound choice given your role?\n"
                "4. Does this action increase your probability of winning the game given the current game state?\n"
                "If all four pass, reply with only: APPROVE\n"
                "If not, reply: REVISE: <name of better target>",
                self._system_prompt(),
            )
            if critique.strip().upper().startswith("APPROVE"):
                break
            revision_note = critique.replace("REVISE:", "").strip()
            draft = call_llm(
                f"{self.player.name}[Reflection].night.revise",
                f"{context}\n\nRevision: {revision_note}\n"
                f"Choose ONE player from: {names}\n"
                "Reply with only the player's name.",
                self._system_prompt(),
            )

        return self._pick_name(draft, [p.name for p in candidates], f"{self.player.name}[Reflection].night")
