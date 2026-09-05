"""
Three-tier logging:

  Tier 1 — logs/game_summary.jsonl
      One JSON line per game. Lightweight metrics only (winner, rounds,
      detection_accuracy, survival, token counts). Never contains prompts.

  Tier 2 — logs/games/<game_id>.json
      Full structural record: speeches, votes, eliminations, call_log with
      token stats. Does NOT store prompt/response text (kept small for the
      dashboard and analysis scripts).

  Tier 3 — logs/traces/<game_id>.jsonl
      One JSON line per API call, in call order. Contains every field from
      Tier 2 call_log PLUS the full system prompt, user prompt, and model
      response. Intended for qualitative analysis and fine-tuning.
      ~2-5 MB per game; only written when TRACE_LOGS env var is set to "1"
      OR always (current default — can be disabled cheaply).
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

LOGS_DIR     = Path(__file__).parent.parent / "logs"
SUMMARY_PATH = LOGS_DIR / "game_summary.jsonl"
GAMES_DIR    = LOGS_DIR / "games"
TRACES_DIR   = LOGS_DIR / "traces"

# Fields stripped from call_log entries before writing to games/<id>.json
# (they live in traces/ instead)
_TRACE_FIELDS = {"system", "prompt", "response"}


def _ensure_dirs() -> None:
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)


def write_game_log(game_id: int, schedule_row: dict, result: dict) -> None:
    _ensure_dirs()
    ts = datetime.now().isoformat(timespec="seconds")

    # ── Tier 1: summary line ─────────────────────────────────
    summary = {
        "game_id":            game_id,
        "timestamp":          ts,
        "winner":             result["winner"],
        "rounds":             result["rounds"],
        "detection_accuracy": result["detection_accuracy"],
        "survival_avg":       result["survival_avg_rounds"],
        "roles": {
            "ww1":    schedule_row["ww1"],
            "ww2":    schedule_row["ww2"],
            "seer":   schedule_row["seer"],
            "doctor": schedule_row["doctor"],
            "v1":     schedule_row["v1"],
            "v2":     schedule_row["v2"],
            "v3":     schedule_row["v3"],
            "v4":     schedule_row["v4"],
        },
        "api": {
            "total_calls":       result["api"]["total_calls"],
            "total_tokens":      result["api"]["total_tokens"],
            "total_elapsed_sec": result["api"]["total_elapsed_sec"],
            "per_pattern":       result["api"]["per_pattern"],
        },
    }
    with open(SUMMARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    # ── Tier 3: trace file (prompt/response per call) ────────
    trace_path = TRACES_DIR / f"{game_id:04d}.jsonl"
    with open(trace_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(result.get("call_log", []), 1):
            trace_entry = {
                "seq":               i,
                "game_id":           game_id,
                "caller":            entry["caller"],
                "prompt_tokens":     entry["prompt_tokens"],
                "completion_tokens": entry["completion_tokens"],
                "total_tokens":      entry["total_tokens"],
                "elapsed_sec":       entry["elapsed_sec"],
                "system":            entry.get("system", ""),
                "prompt":            entry.get("prompt", ""),
                "response":          entry.get("response", ""),
            }
            f.write(json.dumps(trace_entry, ensure_ascii=False) + "\n")

    # ── Tier 2: structural detail (no prompt/response text) ──
    # Strip trace fields from call_log before writing
    clean_call_log = [
        {k: v for k, v in entry.items() if k not in _TRACE_FIELDS}
        for entry in result.get("call_log", [])
    ]
    result_clean = {**result, "call_log": clean_call_log}

    detail = {
        "game_id":   game_id,
        "timestamp": ts,
        "schedule":  schedule_row,
        "result":    result_clean,
    }
    detail_path = GAMES_DIR / f"{game_id:04d}.json"
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)
