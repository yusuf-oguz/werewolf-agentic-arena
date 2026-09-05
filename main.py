from project_base import ProjectBase, ProjectDef


class P271Project(ProjectBase):
    @classmethod
    def define(cls) -> ProjectDef:
        return ProjectDef(
            key="p271",
            name="Werewolf Agentic Arena",
            desc="A tournament arena where AI agents using different agentic reasoning patterns compete in Werewolf (Mafia), measuring how reasoning architecture affects performance in a social deduction setting.",
            student_id="150220322",
            scope=(
                "Implements a complete Werewolf game engine where 8 LLM agents — each using one of four "
                "agentic reasoning patterns — play against each other. The core research question is: "
                "does the choice of reasoning architecture (not the LLM model) measurably affect gameplay "
                "quality in a social deduction game requiring deception, inference, and coordination? "
                "All agents use the same underlying LLM (DeepSeek V3); only the prompt structure differs. "
                "A Python engine acts as moderator, enforcing rules, managing night/day phases, a bidding "
                "system for speaking order, and logging every action. Results are saved per game and "
                "aggregated across the tournament. An interactive web dashboard visualises all game logs."
            ),
            key_contributions=[
                "Game engine: Python moderator enforcing Werewolf rules, night/day phases, bid-based speaking order, voting, and elimination",
                "Baseline agent (control): single LLM call per action — direct prompt, no reasoning steps",
                "Reflection agent (Catalog 1): draft → critique → revise loop applied to all four actions",
                "ReAct agent (Catalog 2): think-act-observe loop with six game-state query tools",
                "Tree of Thoughts agent (Catalog 2): multi-branch parallel generation with evaluator selection",
                "Bid system: agents bid 0–5 per discussion round to claim speaking order; bid 0 = pass",
                "Tournament runner: configurable pattern schedules, per-game JSON logs, aggregated metrics",
                "Interactive dashboard: Flask web app for browsing games, timelines, API call traces, and statistics",
            ],
            results=(
                "23 games played across all four patterns. Werewolves won 16/23 games (70%), consistent "
                "with findings in the academic literature on LLM social deduction games. "
                "Key cost findings: ToT uses ~4× more LLM calls than Baseline per game (72 vs 17); "
                "ReAct adds latency beyond its call count due to tool round-trips (~188s vs 66s for Baseline). "
                "Qualitative observations include successful deception by Reflection werewolves, effective "
                "Seer information sharing, and a Baseline hallucination where an agent voted for itself. "
                "Statistical comparison between patterns requires more games with a fixed design."
            ),
        )


if __name__ == "__main__":
    pass
