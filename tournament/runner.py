from __future__ import annotations
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.state import Player, Role, Pattern
from game.engine import run_game
from agents.baseline import BaselineAgent
from agents.reflection import ReflectionAgent
from agents.react import ReActAgent
from agents.tot import ToTAgent
from tournament.schedule import load_or_create_schedule, next_pending, mark_done
from tournament.logger import write_game_log

ALL_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

PATTERN_MAP = {
    "Baseline":    (Pattern.BASELINE,   BaselineAgent),
    "Reflection":  (Pattern.REFLECTION, ReflectionAgent),
    "ReAct":       (Pattern.REACT,      ReActAgent),
    "ToT":         (Pattern.TOT,        ToTAgent),
    "Baseline2":   (Pattern.BASELINE,   BaselineAgent),
    "Reflection2": (Pattern.REFLECTION, ReflectionAgent),
    "ReAct2":      (Pattern.REACT,      ReActAgent),
    "ToT2":        (Pattern.TOT,        ToTAgent),
}


def _build_players(row: dict) -> list[Player]:
    role_keys = ["ww1", "ww2", "seer", "doctor", "v1", "v2", "v3", "v4"]
    roles = [
        Role.WEREWOLF, Role.WEREWOLF,
        Role.SEER, Role.DOCTOR,
        Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
    ]
    # Shuffle names so no pattern is tied to a fixed identity across games
    names = random.sample(ALL_NAMES, len(ALL_NAMES))
    players = []
    for i, (key, role) in enumerate(zip(role_keys, roles)):
        pattern_label = row[key]
        pattern_enum, agent_cls = PATTERN_MAP[pattern_label]
        p = Player(id=i, name=names[i], role=role, pattern=pattern_enum)
        p._agent = agent_cls(p)
        players.append(p)
    return players


def run_tournament(n_games: int = 1, verbose: bool = True) -> None:
    rows = load_or_create_schedule()
    done = sum(1 for r in rows if r["status"] == "done")
    total = len(rows)
    print(f"[Tournament] Schedule loaded: {done}/{total} done, running {n_games} more.")

    played = 0
    while played < n_games:
        row = next_pending(rows)
        if row is None:
            print("[Tournament] All games completed.")
            break

        game_id = int(row["game_id"])
        print(f"\n[Game {game_id}/{total}] ww=({row['ww1']},{row['ww2']}) "
              f"seer={row['seer']} doctor={row['doctor']}")

        players = _build_players(row)
        result = run_game(players, verbose=verbose)

        write_game_log(game_id, row, result)
        mark_done(rows, game_id, result["winner"], result["rounds"])

        print(f"[Game {game_id}] Done — winner: {result['winner']}, "
              f"rounds: {result['rounds']}, "
              f"tokens: {result['api']['total_tokens']}, "
              f"calls: {result['api']['total_calls']}, "
              f"time: {result['api']['total_elapsed_sec']}s")

        played += 1

    done_now = sum(1 for r in rows if r["status"] == "done")
    print(f"\n[Tournament] Session complete. Total progress: {done_now}/{total}")
