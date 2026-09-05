"""
Generates and persists the full 840-game schedule.

Each game is a unique role assignment across 8 pattern slots:
  - 2 werewolves chosen from C(8,2) = 28 pairs
  - 1 seer chosen from remaining 6
  - 1 doctor chosen from remaining 5
  Total: 28 * 6 * 5 = 840 configurations

The schedule is stored as a CSV so it can be opened in Excel.
Columns: game_id, ww1, ww2, seer, doctor, v1, v2, v3, v4, status, winner, rounds
"""
from __future__ import annotations
import csv
import itertools
from pathlib import Path

PATTERNS = ["Baseline", "Reflection", "ReAct", "ToT",
            "Baseline2", "Reflection2", "ReAct2", "ToT2"]

SCHEDULE_PATH = Path(__file__).parent.parent / "logs" / "schedule.csv"
FIELDNAMES = [
    "game_id", "ww1", "ww2", "seer", "doctor",
    "v1", "v2", "v3", "v4",
    "status", "winner", "rounds",
]


def generate_schedule() -> list[dict]:
    rows = []
    game_id = 1
    slots = list(range(8))

    for ww1, ww2 in itertools.combinations(slots, 2):
        remaining_after_wolves = [s for s in slots if s not in (ww1, ww2)]
        for seer in remaining_after_wolves:
            remaining_after_seer = [s for s in remaining_after_wolves if s != seer]
            for doctor in remaining_after_seer:
                villagers = [s for s in remaining_after_seer if s != doctor]
                rows.append({
                    "game_id": game_id,
                    "ww1": PATTERNS[ww1],
                    "ww2": PATTERNS[ww2],
                    "seer": PATTERNS[seer],
                    "doctor": PATTERNS[doctor],
                    "v1": PATTERNS[villagers[0]],
                    "v2": PATTERNS[villagers[1]],
                    "v3": PATTERNS[villagers[2]],
                    "v4": PATTERNS[villagers[3]],
                    "status": "pending",
                    "winner": "",
                    "rounds": "",
                })
                game_id += 1
    return rows


def load_or_create_schedule() -> list[dict]:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SCHEDULE_PATH.exists():
        with open(SCHEDULE_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    rows = generate_schedule()
    _write_schedule(rows)
    print(f"[Schedule] Created {len(rows)}-game schedule at {SCHEDULE_PATH}")
    return rows


def next_pending(rows: list[dict]) -> dict | None:
    for row in rows:
        if row["status"] == "pending":
            return row
    return None


def mark_done(rows: list[dict], game_id: int, winner: str, rounds: int) -> None:
    for row in rows:
        if int(row["game_id"]) == game_id:
            row["status"] = "done"
            row["winner"] = winner
            row["rounds"] = str(rounds)
            break
    _write_schedule(rows)


def _write_schedule(rows: list[dict]) -> None:
    with open(SCHEDULE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
