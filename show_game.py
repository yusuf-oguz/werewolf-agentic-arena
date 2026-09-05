"""
show_game.py  —  Werewolf game log visualizer
Usage:
    python show_game.py logs/games/0001.json
    python show_game.py logs/games/0001.json --detail
    python show_game.py logs/games/0001.json --output my_report.html
"""

import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from html import escape

# --------------------------------------------------------------------------- #
# Player slot -> name/role mapping (from schedule keys)
# --------------------------------------------------------------------------- #
SLOT_ORDER = ["ww1", "ww2", "seer", "doctor", "v1", "v2", "v3", "v4"]
ROLE_LABELS = {
    "ww1": "Werewolf",
    "ww2": "Werewolf",
    "seer": "Seer",
    "doctor": "Doctor",
    "v1": "Villager",
    "v2": "Villager",
    "v3": "Villager",
    "v4": "Villager",
}
# Player names hardcoded in engine.py
PLAYER_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

ROLE_COLOR = {
    "Werewolf": "#c0392b",
    "Seer":     "#8e44ad",
    "Doctor":   "#27ae60",
    "Villager": "#2980b9",
}

PATTERN_COLOR = {
    "Baseline":   "#7f8c8d",
    "Baseline2":  "#7f8c8d",
    "Reflection": "#e67e22",
    "Reflection2":"#e67e22",
    "ReAct":      "#16a085",
    "ReAct2":     "#16a085",
    "ToT":        "#8e44ad",
    "ToT2":       "#8e44ad",
}

# --------------------------------------------------------------------------- #
# Build player info table from schedule
# --------------------------------------------------------------------------- #
def build_player_info(schedule):
    """Returns dict: name -> {role, pattern, player_id}"""
    info = {}
    for i, slot in enumerate(SLOT_ORDER):
        name = PLAYER_NAMES[i]
        pattern = schedule.get(slot, "?")
        role = ROLE_LABELS[slot]
        info[name] = {"role": role, "pattern": pattern, "player_id": i}
    return info


def id_to_name(player_id):
    return PLAYER_NAMES[player_id]


# --------------------------------------------------------------------------- #
# Parse call_log into per-player, per-round grouped structure
# --------------------------------------------------------------------------- #
def parse_call_log(call_log):
    """
    Returns list of dicts:
      {caller_raw, player, pattern, action, step, tokens, elapsed_sec}
    """
    parsed = []
    for entry in call_log:
        caller = entry["caller"]  # e.g. "Bob[Reflection].speak.draft"
        try:
            name_pat, rest = caller.split("]", 1)
            player, pattern = name_pat.split("[")
            rest = rest.lstrip(".")
        except ValueError:
            player, pattern, rest = caller, "?", caller
        parsed.append({
            "caller_raw": caller,
            "player": player,
            "pattern": pattern,
            "action": rest,
            "tokens": entry.get("total_tokens", 0),
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "elapsed_sec": entry.get("elapsed_sec", 0),
        })
    return parsed


# --------------------------------------------------------------------------- #
# Group speeches and votes by round
# --------------------------------------------------------------------------- #
def group_by_round(speeches, votes, eliminations):
    rounds = defaultdict(lambda: {"speeches": [], "votes": [], "eliminations": []})
    for s in speeches:
        rounds[s["round"]]["speeches"].append(s)
    for v in votes:
        rounds[v["round"]]["votes"].append(v)
    for e in eliminations:
        rounds[e["round"]]["eliminations"].append(e)
    return rounds


# --------------------------------------------------------------------------- #
# HTML helpers
# --------------------------------------------------------------------------- #
def _css():
    return """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Segoe UI', system-ui, sans-serif;
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 24px;
        line-height: 1.5;
    }
    h1 { color: #f0c040; margin-bottom: 8px; font-size: 1.6rem; }
    h2 { color: #aaa; font-size: 1.1rem; margin-bottom: 20px; font-weight: 400; }
    h3 { color: #f0c040; margin: 20px 0 10px; font-size: 1.1rem; }
    h4 { color: #ccc; font-size: 0.9rem; margin: 12px 0 6px; text-transform: uppercase;
         letter-spacing: 0.05em; }

    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 28px;
    }
    .summary-card {
        background: #16213e;
        border-radius: 8px;
        padding: 14px 18px;
        border-left: 4px solid #f0c040;
    }
    .summary-card .label { font-size: 0.75rem; color: #888; text-transform: uppercase;
                           letter-spacing: 0.06em; }
    .summary-card .value { font-size: 1.3rem; color: #f0f0f0; font-weight: 600; margin-top: 4px; }

    .players-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 10px;
        margin-bottom: 28px;
    }
    .player-card {
        background: #16213e;
        border-radius: 8px;
        padding: 10px 14px;
        border-top: 3px solid var(--role-color);
        position: relative;
    }
    .player-card.eliminated { opacity: 0.45; }
    .player-card .pname { font-weight: 600; font-size: 1rem; }
    .player-card .prole { font-size: 0.78rem; margin-top: 2px; color: var(--role-color); }
    .player-card .ppattern { font-size: 0.75rem; color: #888; margin-top: 2px; }
    .elim-badge {
        position: absolute; top: 8px; right: 10px;
        font-size: 0.65rem; background: #c0392b; color: #fff;
        border-radius: 4px; padding: 1px 5px;
    }

    .round-block {
        background: #16213e;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 20px;
        border: 1px solid #2a2a4a;
    }
    .phase-label {
        display: inline-block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 10px;
        font-weight: 700;
    }
    .phase-night { background: #1a1a3e; color: #88aaff; border: 1px solid #336; }
    .phase-day   { background: #3e2a00; color: #ffcc66; border: 1px solid #663300; }

    .speech-item {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
        align-items: flex-start;
    }
    .speech-avatar {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.85rem; flex-shrink: 0;
        border: 2px solid var(--role-color);
        color: var(--role-color);
        background: #1a1a2e;
    }
    .speech-body { flex: 1; }
    .speech-meta { font-size: 0.75rem; color: #888; margin-bottom: 3px; }
    .speech-meta .sname { color: #ddd; font-weight: 600; }
    .speech-text {
        background: #0f1120;
        border-left: 3px solid var(--role-color);
        padding: 8px 12px;
        border-radius: 0 6px 6px 0;
        font-size: 0.88rem;
        color: #ccc;
    }

    .vote-row {
        display: flex; gap: 8px; align-items: center;
        font-size: 0.85rem; margin-bottom: 6px;
    }
    .vote-chip {
        background: #2a2a4a; border-radius: 4px; padding: 3px 8px;
        font-size: 0.8rem;
    }
    .vote-arrow { color: #888; }

    .elim-item {
        display: flex; align-items: center; gap: 10px;
        background: #3a1010; border-radius: 6px;
        padding: 8px 14px; margin-top: 10px;
        font-size: 0.87rem; border: 1px solid #5a1010;
    }
    .elim-icon { font-size: 1.1rem; }

    details { margin-top: 10px; }
    details > summary {
        cursor: pointer;
        font-size: 0.8rem;
        color: #778;
        padding: 4px 0;
        user-select: none;
        list-style: none;
    }
    details > summary::before { content: '+ '; }
    details[open] > summary::before { content: '- '; }
    details > summary:hover { color: #aab; }

    .call-log-table {
        width: 100%; border-collapse: collapse; margin-top: 8px;
        font-size: 0.78rem;
    }
    .call-log-table th {
        text-align: left; padding: 4px 8px;
        background: #0f1120; color: #888;
        border-bottom: 1px solid #2a2a4a;
    }
    .call-log-table td {
        padding: 4px 8px; border-bottom: 1px solid #1e1e3a; color: #bbb;
    }
    .call-log-table tr:hover td { background: #1a1a30; }

    .pattern-badge {
        display: inline-block; font-size: 0.7rem; padding: 1px 6px;
        border-radius: 3px; font-weight: 600; margin-left: 5px;
        vertical-align: middle;
    }

    .api-section {
        background: #16213e; border-radius: 10px; padding: 18px 20px;
        margin-bottom: 20px; border: 1px solid #2a2a4a;
    }
    .api-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px; margin-top: 10px;
    }
    .api-card {
        background: #0f1120; border-radius: 6px; padding: 10px 14px;
        border-left: 3px solid var(--pat-color);
    }
    .api-card .pat-name { font-size: 0.8rem; font-weight: 600; color: var(--pat-color); }
    .api-card .api-stat { font-size: 0.75rem; color: #888; margin-top: 3px; }

    hr { border: none; border-top: 1px solid #2a2a4a; margin: 20px 0; }
    """


def _pattern_badge(pattern, color):
    return f'<span class="pattern-badge" style="background:{color}22;color:{color};border:1px solid {color}44">{escape(pattern)}</span>'


def render_html(data, detail=False):
    result = data["result"]
    schedule = data["schedule"]
    game_id = data["game_id"]
    timestamp = data.get("timestamp", "")

    player_info = build_player_info(schedule)

    # Eliminations: {name: {round, phase, cause}}
    elim_map = {}
    for e in result["eliminations"]:
        elim_map[e["player"]] = e

    speeches = result.get("speeches", [])
    votes = result.get("votes", [])
    eliminations = result.get("eliminations", [])
    call_log_raw = result.get("call_log", [])
    call_log = parse_call_log(call_log_raw)

    rounds_data = group_by_round(speeches, votes, eliminations)
    n_rounds = result["rounds"]

    winner = result["winner"]
    winner_label = "Village wins" if winner == "village" else "Werewolves win"
    winner_color = "#27ae60" if winner == "village" else "#c0392b"

    # ------------------------------------------------------------------ #
    # Head
    # ------------------------------------------------------------------ #
    html = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Game #{game_id} — Werewolf Arena</title>
<style>{_css()}</style>
</head>
<body>
"""]

    # ------------------------------------------------------------------ #
    # Header
    # ------------------------------------------------------------------ #
    html.append(f"""
<h1>Werewolf Arena — Game #{game_id}</h1>
<h2>{timestamp}</h2>
""")

    # ------------------------------------------------------------------ #
    # Summary cards
    # ------------------------------------------------------------------ #
    api = result.get("api", {})
    detection = result.get("detection_accuracy", 0)
    html.append('<div class="summary-grid">')
    html.append(f"""
  <div class="summary-card" style="border-color:{winner_color}">
    <div class="label">Outcome</div>
    <div class="value" style="color:{winner_color}">{winner_label}</div>
  </div>
  <div class="summary-card">
    <div class="label">Rounds</div>
    <div class="value">{n_rounds}</div>
  </div>
  <div class="summary-card">
    <div class="label">Detection Accuracy</div>
    <div class="value">{detection:.1%}</div>
  </div>
  <div class="summary-card">
    <div class="label">Total API Calls</div>
    <div class="value">{api.get('total_calls', '?')}</div>
  </div>
  <div class="summary-card">
    <div class="label">Total Tokens</div>
    <div class="value">{api.get('total_tokens', '?'):,}</div>
  </div>
  <div class="summary-card">
    <div class="label">Total Time</div>
    <div class="value">{api.get('total_elapsed_sec', 0):.1f}s</div>
  </div>
""")
    html.append('</div>')

    # ------------------------------------------------------------------ #
    # Player cards
    # ------------------------------------------------------------------ #
    html.append('<h3>Players</h3>')
    html.append('<div class="players-grid">')
    for name, info in player_info.items():
        role = info["role"]
        pattern = info["pattern"]
        rc = ROLE_COLOR.get(role, "#888")
        pc = PATTERN_COLOR.get(pattern, "#888")
        elim = elim_map.get(name)
        elim_cls = " eliminated" if elim else ""
        elim_html = ""
        if elim:
            cause_label = "killed" if elim["cause"] == "werewolf_kill" else "voted out"
            elim_html = f'<span class="elim-badge">R{elim["round"]} {cause_label}</span>'
        html.append(f"""
  <div class="player-card{elim_cls}" style="--role-color:{rc}">
    {elim_html}
    <div class="pname">{escape(name)}</div>
    <div class="prole">{role}</div>
    <div class="ppattern">{_pattern_badge(pattern, pc)}</div>
  </div>""")
    html.append('</div>')

    # ------------------------------------------------------------------ #
    # Rounds
    # ------------------------------------------------------------------ #
    html.append('<hr>')
    html.append('<h3>Game Timeline</h3>')

    for rnum in range(1, n_rounds + 1):
        rdata = rounds_data[rnum]
        html.append(f'<div class="round-block">')
        html.append(f'<h3 style="margin-top:0">Round {rnum}</h3>')

        # Night eliminations (before speeches)
        night_elims = [e for e in rdata["eliminations"] if e["phase"] == "night"]
        if night_elims:
            html.append('<span class="phase-label phase-night">Night</span>')
            for e in night_elims:
                ename = e["player"]
                erole = e["role"].capitalize()
                cause = "killed by werewolves"
                html.append(f"""
  <div class="elim-item">
    <span class="elim-icon">&#128565;</span>
    <span><strong>{escape(ename)}</strong> ({erole}) was {cause}</span>
  </div>""")

        # Speeches
        if rdata["speeches"]:
            html.append('<br><span class="phase-label phase-day">Day — Discussion</span>')
            for s in rdata["speeches"]:
                pid = s["player_id"]
                pname = id_to_name(pid)
                info = player_info.get(pname, {})
                role = info.get("role", "?")
                pattern = info.get("pattern", "?")
                rc = ROLE_COLOR.get(role, "#888")
                pc = PATTERN_COLOR.get(pattern, "#888")
                initials = pname[:2].upper()
                html.append(f"""
  <div class="speech-item" style="--role-color:{rc}">
    <div class="speech-avatar">{initials}</div>
    <div class="speech-body">
      <div class="speech-meta">
        <span class="sname">{escape(pname)}</span>
        &nbsp;·&nbsp;{role}
        {_pattern_badge(pattern, pc)}
      </div>
      <div class="speech-text">{escape(s['text'])}</div>
    </div>
  </div>""")

        # Votes
        if rdata["votes"]:
            html.append('<br><span class="phase-label phase-day">Day — Voting</span><br>')
            vote_tally = defaultdict(list)
            for v in rdata["votes"]:
                voter = id_to_name(v["voter_id"])
                target = id_to_name(v["target_id"])
                trc = ROLE_COLOR.get(player_info.get(target, {}).get("role", ""), "#888")
                vrc = ROLE_COLOR.get(player_info.get(voter, {}).get("role", ""), "#888")
                html.append(f"""
  <div class="vote-row">
    <span class="vote-chip" style="color:{vrc}">{escape(voter)}</span>
    <span class="vote-arrow">&#8594;</span>
    <span class="vote-chip" style="color:{trc}">{escape(target)}</span>
  </div>""")
                vote_tally[target].append(voter)

            # tally summary
            html.append('<div style="margin-top:8px;font-size:0.8rem;color:#888">Tally: ')
            tally_parts = []
            for target, voters in sorted(vote_tally.items(), key=lambda x: -len(x[1])):
                trc = ROLE_COLOR.get(player_info.get(target, {}).get("role", ""), "#888")
                tally_parts.append(f'<span style="color:{trc}">{escape(target)}</span> ×{len(voters)}')
            html.append(" &nbsp;|&nbsp; ".join(tally_parts))
            html.append('</div>')

        # Day eliminations (voted out)
        day_elims = [e for e in rdata["eliminations"] if e["phase"] == "day"]
        if day_elims:
            for e in day_elims:
                ename = e["player"]
                erole = e["role"].capitalize()
                html.append(f"""
  <div class="elim-item" style="margin-top:10px">
    <span class="elim-icon">&#9993;</span>
    <span><strong>{escape(ename)}</strong> ({erole}) was voted out</span>
  </div>""")

        html.append('</div>')  # round-block

    # ------------------------------------------------------------------ #
    # API / call_log section
    # ------------------------------------------------------------------ #
    html.append('<hr>')
    html.append('<div class="api-section">')
    html.append('<h3 style="margin-top:0">API Usage by Pattern</h3>')
    html.append('<div class="api-grid">')
    per_pattern = api.get("per_pattern", {})
    for pat, stats in per_pattern.items():
        pc = PATTERN_COLOR.get(pat, "#888")
        html.append(f"""
  <div class="api-card" style="--pat-color:{pc}">
    <div class="pat-name">{escape(pat)}</div>
    <div class="api-stat">Calls: {stats.get('calls','?')}</div>
    <div class="api-stat">Tokens: {stats.get('tokens',0):,}</div>
    <div class="api-stat">Time: {stats.get('elapsed_sec',0):.1f}s</div>
  </div>""")
    html.append('</div>')

    if detail and call_log:
        html.append("""
  <details style="margin-top:16px">
    <summary>Full Call Log ({} entries)</summary>
    <table class="call-log-table">
      <tr>
        <th>#</th><th>Caller</th>
        <th>Prompt tk</th><th>Completion tk</th><th>Total tk</th><th>Time (s)</th>
      </tr>""".format(len(call_log)))
        for i, entry in enumerate(call_log, 1):
            pc = PATTERN_COLOR.get(entry["pattern"], "#888")
            html.append(f"""
      <tr>
        <td>{i}</td>
        <td><span style="color:{pc}">{escape(entry['player'])}</span>
            <span style="color:#556">[{escape(entry['pattern'])}]</span>
            .{escape(entry['action'])}</td>
        <td>{entry['prompt_tokens']}</td>
        <td>{entry['completion_tokens']}</td>
        <td>{entry['tokens']}</td>
        <td>{entry['elapsed_sec']:.2f}</td>
      </tr>""")
        html.append("</table></details>")

    html.append('</div>')  # api-section

    html.append("</body></html>")
    return "\n".join(html)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Visualize a Werewolf game log as HTML")
    parser.add_argument("input", help="Path to game JSON file")
    parser.add_argument("--detail", action="store_true",
                        help="Include full API call log table")
    parser.add_argument("--output", help="Output HTML path (default: same dir as input, .html)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    html = render_html(data, detail=args.detail)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = input_path.with_suffix(".html")

    out_path.write_text(html, encoding="utf-8")
    print(f"Report saved -> {out_path}")


if __name__ == "__main__":
    main()
