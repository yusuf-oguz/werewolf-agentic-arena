"""
analyze.py — Per-pattern statistics from logs/game_summary.jsonl

Usage:
    python analyze.py
    python analyze.py --csv          # also write stats to logs/analysis.csv
    python analyze.py --min-games 5  # only show patterns with >= 5 observations
"""
from __future__ import annotations
import json
import sys
import csv
from pathlib import Path
from collections import defaultdict
from statistics import mean

LOGS_DIR     = Path(__file__).parent / "logs"
SUMMARY_PATH = LOGS_DIR / "game_summary.jsonl"

ROLE_GROUPS = {
    "ww1":    "werewolf",
    "ww2":    "werewolf",
    "seer":   "village",
    "doctor": "village",
    "v1":     "village",
    "v2":     "village",
    "v3":     "village",
    "v4":     "village",
}

PATTERNS = ["Baseline", "Reflection", "ReAct", "ToT"]


def load_games() -> list[dict]:
    if not SUMMARY_PATH.exists():
        print(f"[analyze] No summary file found at {SUMMARY_PATH}")
        sys.exit(1)
    games = []
    with open(SUMMARY_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                games.append(json.loads(line))
    return games


def _base_pattern(label: str) -> str:
    """'Reflection2' -> 'Reflection'"""
    return label.rstrip("2")


def compute_stats(games: list[dict]) -> dict[str, dict]:
    """
    Returns per-pattern stats dict:
      wins_as_ww, games_as_ww,
      wins_as_village, games_as_village,
      detection_acc_sum, detection_acc_count,
      survival_sum, survival_count,
      api_calls, api_tokens, api_elapsed, api_games
    """
    stats: dict[str, dict] = {p: defaultdict(float) for p in PATTERNS}

    for g in games:
        winner  = g["winner"]           # "village" or "werewolf"
        roles   = g["roles"]            # {ww1: label, ..., v4: label}
        surv    = g.get("survival_avg", {})
        det_acc = g.get("detection_accuracy", None)
        api     = g.get("api", {}).get("per_pattern", {})

        # Track which base-patterns appear in which faction this game
        for slot, label in roles.items():
            p = _base_pattern(label)
            if p not in stats:
                continue
            faction = ROLE_GROUPS[slot]

            if faction == "werewolf":
                stats[p]["games_as_ww"] += 1
                if winner == "werewolf":
                    stats[p]["wins_as_ww"] += 1
            else:
                stats[p]["games_as_village"] += 1
                if winner == "village":
                    stats[p]["wins_as_village"] += 1
                if det_acc is not None:
                    stats[p]["detection_acc_sum"]   += det_acc
                    stats[p]["detection_acc_count"]  += 1

        # Survival avg — keyed by base pattern in the summary
        for label, rounds in surv.items():
            p = _base_pattern(label)
            if p in stats:
                stats[p]["survival_sum"]   += rounds
                stats[p]["survival_count"] += 1

        # API per pattern — keys are base pattern names in the log
        for label, ap in api.items():
            p = _base_pattern(label)
            if p in stats:
                stats[p]["api_calls"]   += ap.get("calls", 0)
                stats[p]["api_tokens"]  += ap.get("tokens", 0)
                stats[p]["api_elapsed"] += ap.get("elapsed_sec", 0)
                stats[p]["api_games"]   += 1

    return {p: dict(v) for p, v in stats.items()}


def _pct(num: float, den: float) -> str:
    if den == 0:
        return "   n/a"
    return f"{num/den*100:6.1f}%"


def _avg(total: float, count: float, fmt: str = ".2f") -> str:
    if count == 0:
        return "  n/a"
    return f"{total/count:{fmt}}"


def print_report(stats: dict[str, dict], n_games: int, min_games: int = 1) -> None:
    print(f"\n{'='*70}")
    print(f"  Werewolf Agentic Arena — Pattern Analysis  ({n_games} game(s))")
    print(f"{'='*70}\n")

    # ── Win rates ────────────────────────────────────────────────────────────
    print("WIN RATES")
    print(f"  {'Pattern':<12}  {'as WW':>8}  {'as Village':>10}  {'Overall':>8}")
    print(f"  {'-'*12}  {'-'*8}  {'-'*10}  {'-'*8}")
    for p in PATTERNS:
        s = stats[p]
        gw = s.get("games_as_ww", 0)
        gv = s.get("games_as_village", 0)
        total_g = gw + gv
        if total_g < min_games:
            continue
        ww  = _pct(s.get("wins_as_ww", 0),      gw)
        vil = _pct(s.get("wins_as_village", 0),  gv)
        ov  = _pct(s.get("wins_as_ww", 0) + s.get("wins_as_village", 0), total_g)
        print(f"  {p:<12}  {ww}  {vil}  {ov}")

    # ── Detection accuracy ───────────────────────────────────────────────────
    print("\nDETECTION ACCURACY  (village-side games, seer performance)")
    print(f"  {'Pattern':<12}  {'Avg DetAcc':>10}  {'N':>4}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*4}")
    for p in PATTERNS:
        s = stats[p]
        cnt = s.get("detection_acc_count", 0)
        if cnt < min_games:
            continue
        acc = _avg(s.get("detection_acc_sum", 0), cnt)
        print(f"  {p:<12}  {acc:>10}  {int(cnt):>4}")

    # ── Survival rounds ──────────────────────────────────────────────────────
    print("\nAVERAGE SURVIVAL ROUNDS")
    print(f"  {'Pattern':<12}  {'Avg Rounds':>10}  {'N':>4}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*4}")
    for p in PATTERNS:
        s = stats[p]
        cnt = s.get("survival_count", 0)
        if cnt < min_games:
            continue
        avg = _avg(s.get("survival_sum", 0), cnt)
        print(f"  {p:<12}  {avg:>10}  {int(cnt):>4}")

    # ── API efficiency ───────────────────────────────────────────────────────
    print("\nAPI EFFICIENCY  (per game averages)")
    print(f"  {'Pattern':<12}  {'Calls/game':>10}  {'Tokens/game':>12}  {'Sec/game':>9}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*12}  {'-'*9}")
    for p in PATTERNS:
        s = stats[p]
        n = s.get("api_games", 0)
        if n < min_games:
            continue
        calls   = _avg(s.get("api_calls", 0),   n, ".1f")
        tokens  = _avg(s.get("api_tokens", 0),  n, ".0f")
        elapsed = _avg(s.get("api_elapsed", 0), n, ".1f")
        print(f"  {p:<12}  {calls:>10}  {tokens:>12}  {elapsed:>9}")

    print()


def write_csv(stats: dict[str, dict], path: Path) -> None:
    rows = []
    for p in PATTERNS:
        s = stats[p]
        gw = s.get("games_as_ww", 0)
        gv = s.get("games_as_village", 0)
        n_api = s.get("api_games", 0)
        rows.append({
            "pattern":           p,
            "games_as_ww":       int(gw),
            "wins_as_ww":        int(s.get("wins_as_ww", 0)),
            "win_rate_ww":       round(s.get("wins_as_ww", 0) / gw, 4) if gw else None,
            "games_as_village":  int(gv),
            "wins_as_village":   int(s.get("wins_as_village", 0)),
            "win_rate_village":  round(s.get("wins_as_village", 0) / gv, 4) if gv else None,
            "detection_acc_avg": round(s.get("detection_acc_sum", 0) / s.get("detection_acc_count", 1), 4)
                                  if s.get("detection_acc_count", 0) else None,
            "survival_avg":      round(s.get("survival_sum", 0) / s.get("survival_count", 1), 4)
                                  if s.get("survival_count", 0) else None,
            "api_calls_per_game":   round(s.get("api_calls", 0) / n_api, 2) if n_api else None,
            "api_tokens_per_game":  round(s.get("api_tokens", 0) / n_api, 2) if n_api else None,
            "api_elapsed_per_game": round(s.get("api_elapsed", 0) / n_api, 2) if n_api else None,
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"[analyze] CSV written -> {path}")


def main() -> None:
    write_csv_flag = "--csv" in sys.argv
    min_games = 1
    for arg in sys.argv[1:]:
        if arg.startswith("--min-games="):
            min_games = int(arg.split("=")[1])
        elif arg == "--min-games" and sys.argv.index(arg) + 1 < len(sys.argv):
            min_games = int(sys.argv[sys.argv.index(arg) + 1])

    games = load_games()
    if not games:
        print("[analyze] No games found in summary log.")
        return

    stats = compute_stats(games)
    print_report(stats, n_games=len(games), min_games=min_games)

    if write_csv_flag:
        write_csv(stats, LOGS_DIR / "analysis.csv")


if __name__ == "__main__":
    main()
