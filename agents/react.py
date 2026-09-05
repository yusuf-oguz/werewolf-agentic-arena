from __future__ import annotations
import re
from game.state import GameState, Player
from game.llm import call_llm
from agents.base import BaseAgent
from agents.baseline import _speech_instruction

MAX_STEPS = 4

TOOLS = {
    "get_alive_players":      lambda state, _: state.tool_alive_players(),
    "get_voting_history":     lambda state, _: state.tool_voting_history(),
    "get_speech_log":         lambda state, arg: state.tool_speech_log(arg.strip()),
    "get_elimination_history":lambda state, _: state.tool_elimination_history(),
    "get_suspicion_graph":    lambda state, _: state.tool_suspicion_graph(),
    "get_player_summary":     lambda state, arg: state.tool_player_summary(arg.strip()),
}

TOOL_DESCRIPTIONS = """Available tools (call at most once each per turn):
- get_alive_players() — list of currently alive players
- get_voting_history() — all votes cast so far
- get_speech_log(<player_name>) — speeches and claims by a specific player
- get_elimination_history() — all eliminations with roles revealed
- get_suspicion_graph() — cumulative vote tally showing who has been targeted most
- get_player_summary(<player_name>) — full behavioural history: accusations, votes, claims
"""


class ReActAgent(BaseAgent):
    def bid(self, state: GameState, speech_round: int = 1) -> int:
        task = (
            f"Before discussion round {speech_round} begins, determine your speaking interest bid (0–5).\n"
            "  0 = pass and say nothing this round\n"
            "  1 = little to say, prefer to listen\n"
            "  2 = minor point to add\n"
            "  3 = moderate point to make\n"
            "  4 = important thing to say\n"
            "  5 = urgently need to speak first\n"
            "Everyone bids simultaneously. Higher bids speak first.\n"
            "Use available tools to assess the game state before deciding.\n"
            "Reply with only a single integer (0, 1, 2, 3, 4, or 5)."
        )
        raw = self._react_loop(state, task=task, output_key="BID")
        m = re.search(r"[0-5]", raw.strip())
        return int(m.group()) if m else 3

    def speak(self, state: GameState, speech_round: int = 1, speech_order: list | None = None) -> str:
        instruction = _speech_instruction(speech_round, speech_order)
        task = (
            f"{instruction}\n"
            "If you choose to speak, your final answer should be your statement."
            " If you choose to stay silent, your final answer should be: PASS"
        )
        return self._react_loop(state, task=task, output_key="SPEECH")

    def vote(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        raw = self._react_loop(state, task=(
            f"It is time to vote. Choose ONE player to eliminate from: {names}\n"
            "Reply with the player's name followed by a one-sentence reason.\n"
            "Your reason is recorded for analysis but is NOT shown to other players — be honest.\n"
            "Format: <name> — <reason>"
        ), output_key="VOTE")
        return raw

    def night_action(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        raw = self._react_loop(state, task=self._night_task(candidates), output_key="ACTION")
        return self._pick_name(raw, [p.name for p in candidates], f"{self.player.name}[ReAct].night")

    def _react_loop(self, state: GameState, task: str, output_key: str) -> str:
        action_label = output_key.lower()
        history = state.history_text(self.player)
        system = self._system_prompt()

        messages = (
            f"{history}\n\n"
            f"{TOOL_DESCRIPTIONS}\n"
            f"Task: {task}\n\n"
            "Think step by step. You may call tools to gather information before deciding.\n"
            "Format each step as:\n"
            "Thought: <your reasoning>\n"
            "Tool: <tool_name>(<argument>) OR Action: <your final answer>\n\n"
            "When ready to give your final answer use:\n"
            f"Action: {output_key}: <your answer>"
        )

        transcript = ""
        caller_prefix = f"{self.player.name}[ReAct].{action_label}"

        for step in range(MAX_STEPS):
            response = call_llm(
                f"{caller_prefix}.step{step+1}",
                messages + transcript,
                system,
            )
            transcript += f"\n{response}"

            # Check for action — prefer "Action: VOTE: Alice", fall back to "Action: Alice"
            keyed = re.search(rf"Action:\s*{output_key}:\s*(.+)", response, re.IGNORECASE)
            if keyed:
                return keyed.group(1).strip()
            plain = re.search(r"Action:\s*(.+)", response, re.IGNORECASE)
            if plain:
                candidate = plain.group(1).strip()
                # Reject if it looks like a different key prefix (e.g. "Action: Tool: ...")
                if not re.match(r"^[A-Z_]{2,}:\s*", candidate):
                    return candidate

            # Check for tool call
            tool_match = re.search(r"Tool:\s*(\w+)\(([^)]*)\)", response)
            if tool_match:
                tool_name = tool_match.group(1).strip()
                tool_arg = tool_match.group(2).strip()
                if tool_name in TOOLS:
                    observation = TOOLS[tool_name](state, tool_arg)
                else:
                    observation = f"Unknown tool: {tool_name}"
                transcript += f"\nObservation: {observation}"

        # Fallback: return empty string so callers (_extract_name) use random choice
        return ""
