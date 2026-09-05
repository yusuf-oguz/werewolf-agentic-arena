from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from game.state import GameState, Player
from game.llm import call_llm
from agents.base import BaseAgent
from agents.baseline import _speech_instruction


class ToTAgent(BaseAgent):

    # ── BID — 2-phase branching ────────────────────────────────────────────────

    def bid(self, state: GameState, speech_round: int = 1) -> int:
        import re
        context = state.history_text(self.player)
        system = self._system_prompt()
        caller = f"{self.player.name}[ToT].bid_r{speech_round}"

        # Phase 1 — 4 branches in parallel, each writes analysis (not just a number)
        branch_defs = [
            ("bid=0",   "You will pass and say nothing this round."),
            ("bid=1-2", "You will speak late, only if others miss something important."),
            ("bid=3",   "You will speak in the middle — contribute a moderate point."),
            ("bid=4-5", "You will speak early and boldly — frame the discussion."),
        ]

        def branch_call(i: int, label: str, hint: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Scenario: you choose {label} for discussion round {speech_round}.\n"
                f"({hint})\n\n"
                "Write a short analysis (3-5 sentences) of the advantages and disadvantages "
                "of this speaking position given your role and the current game state. "
                "Do NOT write a number — write analysis only."
            )
            result = call_llm(f"{caller}.phase1.branch{i+1}", prompt, system)
            return i, result

        phase1_analyses: list[str] = [""] * 4
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(branch_call, i, label, hint) for i, (label, hint) in enumerate(branch_defs)]
            for f in futures:
                i, text = f.result()
                phase1_analyses[i] = text

        # Evaluator 1 — pick best category
        eval1_prompt = (
            f"{context}\n\n"
            f"Four speaking position analyses for discussion round {speech_round}:\n\n"
            + "\n\n".join(
                f"[{i+1}] {branch_defs[i][0]}:\n{phase1_analyses[i]}"
                for i in range(4)
            )
            + "\n\nBased on these analyses, which speaking position is best for your goals right now?\n"
            "Reply with only: BEST: <1, 2, 3, or 4>"
        )
        eval1_result = call_llm(f"{caller}.phase1.eval", eval1_prompt, system)
        best1 = _parse_best(eval1_result, 4)

        # Branch 1 (bid=0) → 0, Branch 3 (bid=3) → 3 — exact, return immediately
        if best1 == 0:
            return 0
        if best1 == 2:
            return 3

        # Phase 2 — narrow down within selected range
        if best1 == 1:
            phase2_defs = [("bid=1", "Speak very late, minimal contribution."), ("bid=2", "Speak late but with a meaningful point.")]
        else:  # best1 == 3
            phase2_defs = [("bid=4", "Speak early with an important point."), ("bid=5", "Speak first, urgently frame the discussion.")]

        def branch_call2(i: int, label: str, hint: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Scenario: you choose {label} for discussion round {speech_round}.\n"
                f"({hint})\n\n"
                "Write a short analysis (2-3 sentences) of the pros and cons of this exact bid value."
            )
            result = call_llm(f"{caller}.phase2.branch{i+1}", prompt, system)
            return i, result

        phase2_analyses: list[str] = [""] * 2
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(branch_call2, i, label, hint) for i, (label, hint) in enumerate(phase2_defs)]
            for f in futures:
                i, text = f.result()
                phase2_analyses[i] = text

        eval2_prompt = (
            f"{context}\n\n"
            f"Two candidate bid values for discussion round {speech_round}:\n\n"
            f"[1] {phase2_defs[0][0]}:\n{phase2_analyses[0]}\n\n"
            f"[2] {phase2_defs[1][0]}:\n{phase2_analyses[1]}\n\n"
            "Which is the better choice?\n"
            "Reply with only: BEST: <1 or 2>"
        )
        eval2_result = call_llm(f"{caller}.phase2.eval", eval2_prompt, system)
        best2 = _parse_best(eval2_result, 2)

        # Map back to integer
        if best1 == 1:
            return 1 if best2 == 0 else 2
        else:
            return 4 if best2 == 0 else 5

    # ── SPEAK — 2-phase ────────────────────────────────────────────────────────

    def speak(self, state: GameState, speech_round: int = 1, speech_order: list | None = None) -> str:
        context = state.history_text(self.player)
        system = self._system_prompt()
        phase_instruction = _speech_instruction(speech_round, speech_order)
        caller = f"{self.player.name}[ToT].speak"

        # Phase 1 — Strategist identifies 3 strategies
        strategies_raw = call_llm(
            f"{caller}.strategies",
            f"{context}\n\n{phase_instruction}\n\n"
            "Identify the 3 most promising speaking strategies available to you right now, "
            "given your role and the current game state. Staying silent is a valid strategy.\n"
            "List them as:\n"
            "Strategy 1: <one sentence>\n"
            "Strategy 2: <one sentence>\n"
            "Strategy 3: <one sentence>",
            system,
        )
        strategies = _parse_strategies(strategies_raw)

        # Phase 1 — 3 evaluation branches in parallel (analysis only, no speech text)
        def eval_branch(i: int, strategy: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Proposed speaking strategy: {strategy}\n\n"
                "Write a short analysis (3-4 sentences) of the advantages and disadvantages "
                "of this strategy given your role and the current game state. "
                "Do NOT write the actual speech — evaluate the strategy only."
            )
            result = call_llm(f"{caller}.phase1.branch{i+1}", prompt, system)
            return i, result

        phase1_analyses: list[str] = [""] * len(strategies)
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(eval_branch, i, s) for i, s in enumerate(strategies)]
            for f in futures:
                i, text = f.result()
                phase1_analyses[i] = text

        eval1_prompt = (
            f"{context}\n\n"
            "Three speaking strategy analyses:\n\n"
            + "\n\n".join(
                f"[{i+1}] Strategy: {strategies[i]}\nAnalysis: {phase1_analyses[i]}"
                for i in range(len(strategies))
            )
            + "\n\nWhich strategy is best for your goals this round?\n"
            "Reply with only: BEST: <1, 2, or 3>"
        )
        eval1_result = call_llm(f"{caller}.phase1.eval", eval1_prompt, system)
        best_strategy_idx = _parse_best(eval1_result, len(strategies))
        best_strategy = strategies[best_strategy_idx]

        # Phase 2 — 2 text branches in parallel
        def text_branch(i: int) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Your chosen strategy: {best_strategy}\n\n"
                f"{phase_instruction}\n\n"
                "Execute this strategy. Write your statement (or reply with only PASS to stay silent)."
            )
            result = call_llm(f"{caller}.phase2.branch{i+1}", prompt, system)
            return i, result

        phase2_texts: list[str] = [""] * 2
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(text_branch, i) for i in range(2)]
            for f in futures:
                i, text = f.result()
                phase2_texts[i] = text

        eval2_prompt = (
            f"{context}\n\n"
            f"Strategy: {best_strategy}\n\n"
            "Two candidate speeches (PASS means staying silent):\n\n"
            f"[1]: {phase2_texts[0]}\n\n"
            f"[2]: {phase2_texts[1]}\n\n"
            "Which is more effective given your strategy and game state?\n"
            "Reply with only: BEST: <1 or 2>"
        )
        eval2_result = call_llm(f"{caller}.phase2.eval", eval2_prompt, system)
        best_text_idx = _parse_best(eval2_result, 2)
        return phase2_texts[best_text_idx]

    # ── VOTE — 2-layer ─────────────────────────────────────────────────────────

    def vote(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        context = state.history_text(self.player)
        system = self._system_prompt()
        caller = f"{self.player.name}[ToT].vote"

        # Layer 1 — Strategist picks 3 candidate targets
        strat1_raw = call_llm(
            f"{caller}.layer1.strategist",
            f"{context}\n\nIt is time to vote. Who are the 3 most strategically sound targets "
            f"to vote for from: {names}?\n"
            "You MUST list exactly 3 different names, even if you have a strong preference — "
            "list your top choice first, then two alternatives.\n"
            "Candidate 1: <name>\n"
            "Candidate 2: <name>\n"
            "Candidate 3: <name>",
            system,
        )
        candidates_layer1 = _parse_candidate_names(strat1_raw, [p.name for p in candidates])

        # Layer 1 — 3 scenario branches in parallel
        def scenario_branch(i: int, name: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Scenario: you vote for {name}.\n\n"
                "Write a short analysis (3-5 sentences) of the strategic consequences of this vote: "
                "how does it affect the game outcome, what does it signal to other players, "
                "and does it align with your role's win condition? "
                "Do NOT just state the name — write scenario analysis."
            )
            result = call_llm(f"{caller}.layer1.branch{i+1}", prompt, system)
            return i, result

        layer1_analyses: list[str] = [""] * len(candidates_layer1)
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(scenario_branch, i, n) for i, n in enumerate(candidates_layer1)]
            for f in futures:
                i, text = f.result()
                layer1_analyses[i] = text

        eval1_prompt = (
            f"{context}\n\n"
            "Three voting scenario analyses:\n\n"
            + "\n\n".join(
                f"[{i+1}] Voting for {candidates_layer1[i]}:\n{layer1_analyses[i]}"
                for i in range(len(candidates_layer1))
            )
            + "\n\nWhich vote is strategically best?\n"
            "Reply with only: BEST: <1, 2, or 3>"
        )
        eval1_result = call_llm(f"{caller}.layer1.eval", eval1_prompt, system)
        best_target_idx = _parse_best(eval1_result, len(candidates_layer1))
        chosen_name = candidates_layer1[best_target_idx]

        # Layer 2 — Strategist proposes 3 candidate reasons
        strat2_raw = call_llm(
            f"{caller}.layer2.strategist",
            f"{context}\n\nYou have decided to vote for {chosen_name}.\n"
            "Your vote reason is recorded for analysis but is NOT shown to other players — be honest.\n"
            "Propose 3 different honest one-sentence reasons that explain your true thinking:\n"
            "Reason 1: <sentence>\n"
            "Reason 2: <sentence>\n"
            "Reason 3: <sentence>",
            system,
        )
        reasons = _parse_reason_list(strat2_raw)

        # Layer 2 — 3 reason evaluation branches in parallel
        def reason_branch(i: int, reason: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"You are voting for {chosen_name} with this honest reason: \"{reason}\"\n\n"
                "Evaluate this reason (3-4 sentences): Does it accurately reflect your strategic thinking? "
                "Is it logically consistent with your past statements and observations? "
                "Does it capture the most important factor driving your vote?"
            )
            result = call_llm(f"{caller}.layer2.branch{i+1}", prompt, system)
            return i, result

        layer2_analyses: list[str] = [""] * len(reasons)
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(reason_branch, i, r) for i, r in enumerate(reasons)]
            for f in futures:
                i, text = f.result()
                layer2_analyses[i] = text

        eval2_prompt = (
            f"{context}\n\n"
            f"You are voting for {chosen_name}. Three candidate reasons:\n\n"
            + "\n\n".join(
                f"[{i+1}] \"{reasons[i]}\"\nAnalysis: {layer2_analyses[i]}"
                for i in range(len(reasons))
            )
            + "\n\nWhich reason is most effective?\n"
            "Reply with only: BEST: <1, 2, or 3>"
        )
        eval2_result = call_llm(f"{caller}.layer2.eval", eval2_prompt, system)
        best_reason_idx = _parse_best(eval2_result, len(reasons))
        chosen_reason = reasons[best_reason_idx]

        return f"{chosen_name} — {chosen_reason}"

    # ── NIGHT ACTION — 3-branch scenario analysis ──────────────────────────────

    def night_action(self, state: GameState) -> str:
        candidates = [p for p in state.alive_players() if p.id != self.player.id]
        names = ", ".join(p.name for p in candidates)
        context = state.history_text(self.player)
        system = self._system_prompt()
        caller = f"{self.player.name}[ToT].night"

        # Strategist picks 3 candidate targets
        strat_raw = call_llm(
            f"{caller}.strategist",
            f"{context}\n\n{self._night_task(candidates)}\n\n"
            f"Before deciding, identify the 3 most strategic targets from: {names}\n"
            "You MUST list exactly 3 different names, even if you have a strong preference — "
            "list your top choice first, then two alternatives.\n"
            "Candidate 1: <name>\n"
            "Candidate 2: <name>\n"
            "Candidate 3: <name>",
            system,
        )
        night_candidates = _parse_candidate_names(strat_raw, [p.name for p in candidates])

        # 3 scenario branches in parallel
        def scenario_branch(i: int, name: str) -> tuple[int, str]:
            prompt = (
                f"{context}\n\n"
                f"Scenario: tonight you choose {name} for your night action.\n\n"
                "Write a short analysis (3-5 sentences) of the strategic consequences: "
                "what is the likely game impact, what information does this gain or protect, "
                "and does it advance your win condition?"
            )
            result = call_llm(f"{caller}.branch{i+1}", prompt, system)
            return i, result

        analyses: list[str] = [""] * len(night_candidates)
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(scenario_branch, i, n) for i, n in enumerate(night_candidates)]
            for f in futures:
                i, text = f.result()
                analyses[i] = text

        eval_prompt = (
            f"{context}\n\n"
            "Three night action scenario analyses:\n\n"
            + "\n\n".join(
                f"[{i+1}] Targeting {night_candidates[i]}:\n{analyses[i]}"
                for i in range(len(night_candidates))
            )
            + "\n\nWhich target is the best choice for your night action?\n"
            "Reply with only: BEST: <1, 2, or 3>"
        )
        eval_result = call_llm(f"{caller}.eval", eval_prompt, system)
        best_idx = _parse_best(eval_result, len(night_candidates))
        chosen = night_candidates[best_idx]
        return self._pick_name(chosen, [p.name for p in candidates], f"{caller}.pick")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_strategies(raw: str) -> list[str]:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    strategies = []
    for line in lines:
        for prefix in ("Strategy 1:", "Strategy 2:", "Strategy 3:", "1.", "2.", "3.", "1:", "2:", "3:"):
            if line.lower().startswith(prefix.lower()):
                strategies.append(line[len(prefix):].strip())
                break
        if len(strategies) == 3:
            break
    if not strategies:
        strategies = lines[:3]
    return strategies or ["play cautiously", "observe and deflect", "build alliances"]


def _parse_candidate_names(raw: str, valid_names: list[str]) -> list[str]:
    found = []
    for line in raw.splitlines():
        line = line.strip()
        for name in valid_names:
            if name.lower() in line.lower() and name not in found:
                found.append(name)
                break
        if len(found) == 3:
            break
    # pad to 3 with unused valid names
    for name in valid_names:
        if len(found) >= 3:
            break
        if name not in found:
            found.append(name)
    return found[:3]


def _parse_reason_list(raw: str) -> list[str]:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    reasons = []
    for line in lines:
        for prefix in ("Reason 1:", "Reason 2:", "Reason 3:", "1.", "2.", "3.", "1:", "2:", "3:"):
            if line.lower().startswith(prefix.lower()):
                reasons.append(line[len(prefix):].strip())
                break
        if len(reasons) == 3:
            break
    if not reasons:
        reasons = [l for l in lines if l][:3]
    return reasons or ["suspicious behavior", "inconsistent statements", "voting pattern suggests guilt"]


def _parse_best(raw: str, n: int) -> int:
    import re
    match = re.search(rf"BEST:\s*([1-{n}])", raw, re.IGNORECASE)
    if match:
        return int(match.group(1)) - 1
    match = re.search(rf"\b([1-{n}])\b", raw)
    if match:
        return int(match.group(1)) - 1
    return 0
