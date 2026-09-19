"""
dashboard.py - Werewolf Arena interactive dashboard
Usage:
    python dashboard.py           # localhost:5000
    python dashboard.py --port 8080
"""

import json
import os
import argparse
from pathlib import Path
from collections import defaultdict
from html import escape
from flask import Flask, render_template_string, abort, jsonify

BASE_DIR     = Path(__file__).resolve().parent
LOGS_DIR     = BASE_DIR / "logs"
SUMMARY_FILE = LOGS_DIR / "game_summary.jsonl"
GAMES_DIR    = LOGS_DIR / "games"
TRACES_DIR   = LOGS_DIR / "traces"

app = Flask(__name__)

# --------------------------------------------------------------------------- #
# Shared constants (same as show_game.py)
# --------------------------------------------------------------------------- #
SLOT_ORDER   = ["ww1", "ww2", "seer", "doctor", "v1", "v2", "v3", "v4"]
ROLE_LABELS  = {"ww1":"Werewolf","ww2":"Werewolf","seer":"Seer",
                "doctor":"Doctor","v1":"Villager","v2":"Villager",
                "v3":"Villager","v4":"Villager"}
PLAYER_NAMES = ["Alice","Bob","Carol","Dave","Eve","Frank","Grace","Hank"]
ROLE_COLOR   = {"Werewolf":"#c0392b","Seer":"#8e44ad",
                "Doctor":"#27ae60","Villager":"#2980b9"}
PATTERN_COLOR = {"Baseline":"#7f8c8d","Baseline2":"#7f8c8d",
                 "Reflection":"#e67e22","Reflection2":"#e67e22",
                 "ReAct":"#16a085","ReAct2":"#16a085",
                 "ToT":"#8e44ad","ToT2":"#8e44ad"}
PATTERNS_CANONICAL = ["Baseline","Reflection","ReAct","ToT"]

# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def load_summaries():
    if not SUMMARY_FILE.exists():
        return []
    games = []
    with open(SUMMARY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    games.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return games


def load_game(game_id):
    path = GAMES_DIR / f"{int(game_id):04d}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_trace(game_id):
    path = TRACES_DIR / f"{int(game_id):04d}.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def build_player_info(players_list, schedule):
    """Build player info from the game's actual player list (post-randomization)."""
    info = {}
    role_keys = SLOT_ORDER  # ww1,ww2,seer,doctor,v1..v4 — ordered by player id
    for p in players_list:
        slot = role_keys[p["id"]]
        info[p["name"]] = {
            "role": ROLE_LABELS[slot],
            "pattern": schedule.get(slot, p.get("pattern", "?")),
            "player_id": p["id"],
        }
    return info


def compute_stats(games):
    if not games:
        return {}
    total = len(games)
    village_wins = sum(1 for g in games if g.get("winner") == "village")
    ww_wins = total - village_wins
    avg_rounds = sum(g.get("rounds", 0) for g in games) / total
    avg_detect = sum(g.get("detection_accuracy", 0) for g in games) / total
    avg_vote_acc = sum(g.get("vote_accuracy", 0) for g in games) / total

    # per-pattern stats
    pat_stats = {p: {"games":0,"tokens":0,"calls":0,"elapsed":0} for p in PATTERNS_CANONICAL}
    for g in games:
        per = g.get("api", {}).get("per_pattern", {})
        for p in PATTERNS_CANONICAL:
            # merge Baseline + Baseline2 etc.
            for key in [p, p+"2"]:
                if key in per:
                    pat_stats[p]["games"]   += 1
                    pat_stats[p]["tokens"]  += per[key].get("tokens", 0)
                    pat_stats[p]["calls"]   += per[key].get("calls", 0)
                    pat_stats[p]["elapsed"] += per[key].get("elapsed_sec", 0)

    return {
        "total": total,
        "village_wins": village_wins,
        "ww_wins": ww_wins,
        "village_win_pct": village_wins / total * 100,
        "ww_win_pct": ww_wins / total * 100,
        "avg_rounds": avg_rounds,
        "avg_detect": avg_detect,
        "avg_vote_acc": avg_vote_acc,
        "pat_stats": pat_stats,
    }


def parse_call_log(call_log):
    parsed = []
    for entry in call_log:
        caller = entry["caller"]
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
# Shared CSS
# --------------------------------------------------------------------------- #
COMMON_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #1a1a2e; color: #e0e0e0;
    padding: 0; line-height: 1.5; min-height: 100vh;
}
a { color: #f0c040; text-decoration: none; }
a:hover { text-decoration: underline; }

.navbar {
    background: #0f0f1e;
    border-bottom: 1px solid #2a2a4a;
    padding: 12px 32px;
    display: flex; align-items: center; gap: 24px;
    position: sticky; top: 0; z-index: 100;
}
.navbar .brand { color: #f0c040; font-weight: 700; font-size: 1.1rem; }
.navbar .nav-link { color: #aaa; font-size: 0.9rem; }
.navbar .nav-link:hover { color: #fff; text-decoration: none; }

.page { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }

h1 { color: #f0c040; margin-bottom: 6px; font-size: 1.5rem; }
h2 { color: #ccc; font-size: 1.05rem; margin: 24px 0 12px; }
h3 { color: #f0c040; font-size: 1rem; margin: 20px 0 10px; }

.card {
    background: #16213e; border-radius: 10px;
    padding: 18px 22px; border: 1px solid #2a2a4a;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin-bottom: 28px;
}
.summary-card {
    background: #16213e; border-radius: 8px;
    padding: 14px 18px; border-left: 4px solid #f0c040;
}
.summary-card .label { font-size: 0.72rem; color: #888;
    text-transform: uppercase; letter-spacing: 0.06em; }
.summary-card .value { font-size: 1.3rem; color: #f0f0f0;
    font-weight: 600; margin-top: 4px; }
.summary-card .sub { font-size: 0.75rem; color: #666; margin-top: 2px; }

.pattern-badge {
    display: inline-block; font-size: 0.7rem; padding: 1px 7px;
    border-radius: 3px; font-weight: 600; vertical-align: middle;
}
.role-badge {
    display: inline-block; font-size: 0.72rem; padding: 1px 7px;
    border-radius: 3px; font-weight: 600; vertical-align: middle;
}

table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th {
    text-align: left; padding: 8px 12px;
    background: #0f1120; color: #888;
    border-bottom: 2px solid #2a2a4a;
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
}
td { padding: 8px 12px; border-bottom: 1px solid #1e1e3a; color: #ccc; }
tr:hover td { background: #1a1a30; }

.winner-village { color: #27ae60; font-weight: 600; }
.winner-ww      { color: #c0392b; font-weight: 600; }

input[type=number], input[type=text] {
    background: #0f1120; border: 1px solid #3a3a5a;
    color: #eee; padding: 8px 12px; border-radius: 6px;
    font-size: 0.95rem; outline: none; width: 120px;
}
input:focus { border-color: #f0c040; }
button {
    background: #f0c040; color: #1a1a2e;
    border: none; padding: 8px 18px; border-radius: 6px;
    font-weight: 700; cursor: pointer; font-size: 0.9rem;
}
button:hover { background: #ffd060; }

.search-row {
    display: flex; gap: 10px; align-items: center; margin-bottom: 20px;
    flex-wrap: wrap;
}
.filter-select {
    background: #0f1120; border: 1px solid #3a3a5a;
    color: #eee; padding: 7px 12px; border-radius: 6px;
    font-size: 0.85rem; outline: none; cursor: pointer;
}
.filter-select:focus { border-color: #f0c040; }

.pat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin-bottom: 28px;
}
.pat-card {
    background: #0f1120; border-radius: 8px; padding: 14px 16px;
    border-left: 4px solid var(--pc);
}
.pat-card .pat-name { font-weight: 700; color: var(--pc); font-size: 0.95rem; }
.pat-card .pat-stat { font-size: 0.78rem; color: #888; margin-top: 4px; }
.pat-card .pat-val  { color: #ccc; }

.players-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px; margin-bottom: 24px;
}
.player-card {
    background: #16213e; border-radius: 8px;
    padding: 10px 14px; border-top: 3px solid var(--rc);
    position: relative;
}
.player-card.eliminated { opacity: 0.45; }
.player-card .pname { font-weight: 600; }
.player-card .prole { font-size: 0.78rem; color: var(--rc); margin-top: 2px; }
.player-card .ppat  { font-size: 0.75rem; color: #888; margin-top: 2px; }
.elim-badge {
    position: absolute; top: 8px; right: 8px;
    font-size: 0.6rem; background: #c0392b; color: #fff;
    border-radius: 3px; padding: 1px 5px;
}

.round-block {
    background: #16213e; border-radius: 10px;
    padding: 18px 20px; margin-bottom: 16px;
    border: 1px solid #2a2a4a;
}
.phase-label {
    display: inline-block; font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 4px;
    margin-bottom: 10px; font-weight: 700;
}
.phase-night { background:#1a1a3e; color:#88aaff; border:1px solid #336; }
.phase-day   { background:#3e2a00; color:#ffcc66; border:1px solid #663; }

.speech-item {
    display: flex; gap: 12px; margin-bottom: 12px; align-items: flex-start;
}
.pass-item {
    display: flex; gap: 12px; margin-bottom: 8px; align-items: center;
    opacity: 0.45;
}
.pass-label {
    font-size: 0.78rem; color: #888; font-style: italic;
}
.speech-avatar {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.8rem; flex-shrink: 0;
    border: 2px solid var(--rc); color: var(--rc); background: #1a1a2e;
}
.speech-body { flex: 1; }
.speech-meta { font-size: 0.73rem; color: #888; margin-bottom: 3px; }
.speech-meta .sname { color: #ddd; font-weight: 600; }
.speech-text {
    background: #0f1120; border-left: 3px solid var(--rc);
    padding: 8px 12px; border-radius: 0 6px 6px 0;
    font-size: 0.87rem; color: #ccc;
}

.vote-row {
    display: flex; gap: 8px; align-items: center;
    font-size: 0.85rem; margin-bottom: 5px;
}
.vote-chip {
    background: #2a2a4a; border-radius: 4px; padding: 3px 8px; font-size: 0.8rem;
}
.vote-arrow { color: #666; }

.elim-item {
    display: flex; align-items: center; gap: 10px;
    background: #3a1010; border-radius: 6px;
    padding: 8px 14px; margin-top: 10px;
    font-size: 0.87rem; border: 1px solid #5a1010;
}
.night-action-row {
    display: flex; align-items: center; gap: 10px;
    background: #0f1a2e; border-radius: 6px;
    padding: 7px 14px; margin-top: 6px;
    font-size: 0.87rem; border: 1px solid #1a2a4a;
    border-left: 3px solid var(--nc, #88aaff);
}
.night-icon { font-size: 1rem; flex-shrink: 0; }

details { margin-top: 10px; }
details > summary {
    cursor: pointer; font-size: 0.8rem; color: #778;
    padding: 4px 0; user-select: none; list-style: none;
}
details > summary::before { content: '+ '; }
details[open] > summary::before { content: '- '; }
details > summary:hover { color: #aab; }

.call-log-table { font-size: 0.77rem; }
.call-log-table th { font-size: 0.7rem; }

.api-call-block {
    border: 1px solid #1e2a3a; border-radius: 5px;
    margin-bottom: 5px; overflow: hidden;
}
.api-call-header {
    background: #0d1520; padding: 5px 10px;
    cursor: pointer; font-size: 0.75rem;
    display: flex; align-items: center; gap: 4px;
    user-select: none;
}
.api-call-header:hover { background: #111a28; }
.api-call-body { padding: 8px 12px; background: #080c18; }
.api-section-label {
    font-size: 0.65rem; color: #445; text-transform: uppercase;
    letter-spacing: 0.07em; margin: 6px 0 3px;
}
.api-section-label:first-child { margin-top: 0; }
.api-pre {
    white-space: pre-wrap; font-size: 0.77rem;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    margin: 0; line-height: 1.45;
}
.api-system   { color: #6a8a6a; }
.api-prompt   { color: #99aacc; }
.api-response { color: #88ee88; }

hr { border: none; border-top: 1px solid #2a2a4a; margin: 24px 0; }
.muted { color: #666; font-size: 0.85rem; }
.tag-village { background:#1a3a1a; color:#27ae60; border:1px solid #27ae6044;
               padding:2px 8px; border-radius:4px; font-size:0.8rem; font-weight:600; }
.tag-ww      { background:#3a1010; color:#c0392b; border:1px solid #c0392b44;
               padding:2px 8px; border-radius:4px; font-size:0.8rem; font-weight:600; }
"""

# --------------------------------------------------------------------------- #
# HOME page
# --------------------------------------------------------------------------- #
HOME_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Werewolf Arena - Dashboard</title>
<style>{{ css }}</style>
</head><body>

<nav class="navbar">
  <span class="brand">&#127940; Werewolf Arena</span>
  <a href="/" class="nav-link">Dashboard</a>
</nav>

<div class="page">
  <h1>Dashboard</h1>
  <p class="muted" style="margin-bottom:24px">
    {{ stats.total }} game{{ 's' if stats.total != 1 else '' }} recorded &nbsp;·&nbsp;
    <span id="last-updated"></span>
  </p>

  {% if stats.total == 0 %}
    <p class="muted">No games recorded yet.</p>
  {% else %}

  <!-- Summary cards -->
  <div class="summary-grid">
    <div class="summary-card" style="border-color:#27ae60">
      <div class="label">Village Wins</div>
      <div class="value">{{ stats.village_wins }}</div>
      <div class="sub">{{ "%.1f"|format(stats.village_win_pct) }}%</div>
    </div>
    <div class="summary-card" style="border-color:#c0392b">
      <div class="label">Werewolf Wins</div>
      <div class="value">{{ stats.ww_wins }}</div>
      <div class="sub">{{ "%.1f"|format(stats.ww_win_pct) }}%</div>
    </div>
    <div class="summary-card">
      <div class="label">Avg Rounds</div>
      <div class="value">{{ "%.1f"|format(stats.avg_rounds) }}</div>
    </div>
    <div class="summary-card">
      <div class="label">Avg Detection Acc.</div>
      <div class="value">{{ "%.1f"|format(stats.avg_detect * 100) }}%</div>
    </div>
  </div>

  <!-- Per-pattern API stats -->
  <h2>Pattern - API Usage (all games)</h2>
  <div class="pat-grid">
    {% for p, s in stats.pat_stats.items() %}
    {% set pc = pattern_color[p] %}
    <div class="pat-card" style="--pc:{{ pc }}">
      <div class="pat-name">{{ p }}</div>
      <div class="pat-stat">Calls &nbsp;<span class="pat-val">{{ s.calls }}</span></div>
      <div class="pat-stat">Tokens &nbsp;<span class="pat-val">{{ "{:,}".format(s.tokens) }}</span></div>
      <div class="pat-stat">Time &nbsp;<span class="pat-val">{{ "%.1f"|format(s.elapsed) }}s</span></div>
    </div>
    {% endfor %}
  </div>

  {% endif %}

  <!-- Game list -->
  <hr>
  <h2>Games</h2>

  <div class="search-row">
    <input type="number" id="goto-input" placeholder="Game #" min="1">
    <button onclick="gotoGame()">Go to game</button>
    <select class="filter-select" id="filter-winner" onchange="filterGames()">
      <option value="">All outcomes</option>
      <option value="village">Village wins</option>
      <option value="werewolf">Werewolf wins</option>
    </select>
    <select class="filter-select" id="filter-rounds" onchange="filterGames()">
      <option value="">Any rounds</option>
      <option value="1">1 round</option>
      <option value="2">2 rounds</option>
      <option value="3">3 rounds</option>
      <option value="4">4+ rounds</option>
    </select>
    <span class="muted" id="filter-count"></span>
  </div>

  <table id="games-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Outcome</th>
        <th>Rounds</th>
        <th>Detection</th>
        <th>Vote Acc.</th>
        <th>Tokens</th>
        <th>Time (s)</th>
        <th>Timestamp</th>
      </tr>
    </thead>
    <tbody>
      {% for g in games %}
      <tr class="game-row"
          data-winner="{{ g.winner }}"
          data-rounds="{{ g.rounds }}"
          onclick="location.href='/game/{{ g.game_id }}'">
        <td><strong>{{ g.game_id }}</strong></td>
        <td>
          {% if g.winner == 'village' %}
            <span class="tag-village">Village</span>
          {% else %}
            <span class="tag-ww">Werewolf</span>
          {% endif %}
        </td>
        <td>{{ g.rounds }}</td>
        <td>{{ "%.1f"|format(g.detection_accuracy * 100) }}%</td>
        <td>{{ "%.1f"|format(g.get('vote_accuracy', 0) * 100) }}%</td>
        <td>{{ "{:,}".format(g.api.total_tokens) }}</td>
        <td>{{ "%.1f"|format(g.api.total_elapsed_sec) }}</td>
        <td class="muted">{{ g.timestamp }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

</div>

<script>
function gotoGame() {
  var v = document.getElementById('goto-input').value.trim();
  if (v) location.href = '/game/' + v;
}
document.getElementById('goto-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') gotoGame();
});

function filterGames() {
  var winner = document.getElementById('filter-winner').value;
  var rounds = document.getElementById('filter-rounds').value;
  var rows = document.querySelectorAll('.game-row');
  var shown = 0;
  rows.forEach(function(row) {
    var w = row.dataset.winner;
    var r = parseInt(row.dataset.rounds);
    var wMatch = !winner || w === winner;
    var rMatch = !rounds || (rounds === '4' ? r >= 4 : r === parseInt(rounds));
    var visible = wMatch && rMatch;
    row.style.display = visible ? '' : 'none';
    if (visible) shown++;
  });
  document.getElementById('filter-count').textContent = shown + ' game' + (shown !== 1 ? 's' : '');
}

document.getElementById('filter-count').textContent = '{{ games|length }} game' + ({{ games|length }} !== 1 ? 's' : '');
document.getElementById('last-updated').textContent = 'Loaded ' + new Date().toLocaleTimeString();
</script>
</body></html>
"""

# --------------------------------------------------------------------------- #
# GAME DETAIL page
# --------------------------------------------------------------------------- #
GAME_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Game #{{ game_id }} - Werewolf Arena</title>
<style>{{ css }}</style>
</head><body>

<nav class="navbar">
  <span class="brand">&#127940; Werewolf Arena</span>
  <a href="/" class="nav-link">Dashboard</a>
  <span class="muted" style="font-size:0.85rem">/ Game #{{ game_id }}</span>
  {% if prev_id %}<a href="/game/{{ prev_id }}" class="nav-link">&#8592; #{{ prev_id }}</a>{% endif %}
  {% if next_id %}<a href="/game/{{ next_id }}" class="nav-link">#{{ next_id }} &#8594;</a>{% endif %}
</nav>

<div class="page">
  <h1>Game #{{ game_id }}</h1>
  <p class="muted" style="margin-bottom:20px">{{ timestamp }}</p>

  <!-- Summary cards -->
  <div class="summary-grid">
    <div class="summary-card" style="border-color:{{ winner_color }}">
      <div class="label">Outcome</div>
      <div class="value" style="color:{{ winner_color }}">{{ winner_label }}</div>
    </div>
    <div class="summary-card">
      <div class="label">Rounds</div><div class="value">{{ rounds }}</div>
    </div>
    <div class="summary-card">
      <div class="label">Detection Accuracy</div>
      <div class="value">{{ "%.1f"|format(detection * 100) }}%</div>
    </div>
    <div class="summary-card">
      <div class="label">Vote Accuracy</div>
      <div class="value">{{ "%.1f"|format(vote_accuracy * 100) }}%</div>
      <div class="label" style="font-size:0.7rem;margin-top:4px">
        {% for pat, acc in vote_accuracy_by_pattern.items() %}
          {{ pat }}: {{ "%.0f"|format(acc * 100) }}%{% if not loop.last %} &nbsp;·&nbsp; {% endif %}
        {% endfor %}
      </div>
    </div>
    <div class="summary-card">
      <div class="label">API Calls</div>
      <div class="value">{{ api.total_calls }}</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Tokens</div>
      <div class="value">{{ "{:,}".format(api.total_tokens) }}</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Time</div>
      <div class="value">{{ "%.1f"|format(api.total_elapsed_sec) }}s</div>
    </div>
    <div class="summary-card" style="border-color:#4a6a8a">
      <div class="label">LLM Model</div>
      <div class="value" style="font-size:0.78rem;color:#aac;word-break:break-all;margin-top:4px">{{ llm_model }}</div>
    </div>
  </div>

  <!-- Players -->
  <h2>Players</h2>
  <div class="players-grid">
    {% for name, info in player_info.items() %}
    {% set rc = role_color[info.role] %}
    {% set pc = pattern_color.get(info.pattern, '#888') %}
    {% set elim = elim_map.get(name) %}
    <div class="player-card {{ 'eliminated' if elim else '' }}" style="--rc:{{ rc }}">
      {% if elim %}
        <span class="elim-badge">R{{ elim.round }} {{ 'killed' if elim.cause == 'werewolf_kill' else 'voted' }}</span>
      {% endif %}
      <div class="pname">{{ name }}</div>
      <div class="prole">{{ info.role }}</div>
      <div class="ppat">
        <span class="pattern-badge" style="background:{{ pc }}22;color:{{ pc }};border:1px solid {{ pc }}44">
          {{ info.pattern }}
        </span>
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- Detail toggle -->
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;flex-wrap:wrap">
    <h2 style="margin:0">Game Timeline</h2>
    <label style="font-size:0.82rem;color:#888;cursor:pointer">
      <input type="checkbox" id="toggle-detail" style="margin-right:4px" onchange="toggleDetail()">
      Show API call steps
    </label>
    <label style="font-size:0.82rem;color:#888;cursor:pointer" id="calllog-label">
      <input type="checkbox" id="toggle-calllog" style="margin-right:4px" onchange="toggleCallLog()" disabled>
      Full call log
    </label>
  </div>

  {% for rnum in range(1, rounds + 1) %}
  {% set rdata = rounds_data[rnum] %}
  <div class="round-block">
    <h3 style="margin-top:0">Round {{ rnum }}</h3>

    {% set night_elims = rdata.eliminations | selectattr('phase','eq','night') | list %}
    {% set has_night = rdata.night_actions or night_elims %}
    {% if has_night %}
      <span class="phase-label phase-night">Night</span>

      {% for a in rdata.night_actions %}
        {% set nsteps = call_steps.get(a.actor, {}).get(rnum, {}).get('night', []) %}
        {% if a.role == 'seer' %}
        <div class="night-action-row" style="--nc:#8e44ad">
          <span class="night-icon">&#128065;</span>
          <span>
            <strong>{{ a.actor }}</strong> (Seer) investigated
            <strong>{{ a.target }}</strong> →
            {% if a.result == 'werewolf' %}
              <span style="color:#c0392b;font-weight:600">WEREWOLF</span>
            {% else %}
              <span style="color:#27ae60;font-weight:600">not werewolf</span>
            {% endif %}
          </span>
        </div>
        {% elif a.role == 'doctor' %}
        <div class="night-action-row" style="--nc:#27ae60">
          <span class="night-icon">&#128138;</span>
          <span><strong>{{ a.actor }}</strong> (Doctor) protected <strong>{{ a.target }}</strong></span>
        </div>
        {% elif a.role == 'werewolf' %}
        <div class="night-action-row" style="--nc:#c0392b">
          <span class="night-icon">&#128049;</span>
          <span><strong>{{ a.actor }}</strong> (Werewolf) targeted <strong>{{ a.target }}</strong></span>
        </div>
        {% endif %}
        {% if nsteps %}
        <div class="detail-block" style="display:none;margin:4px 0 4px 36px">
          {% for st in nsteps %}
          <div class="api-call-block">
            <div class="api-call-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
              <span style="color:#778">{{ st.action }}</span>
              <span style="color:#556;margin-left:8px">{{ st.prompt_tokens }}+{{ st.completion_tokens }} tk</span>
              <span style="color:#445;margin-left:8px">{{ "%.2f"|format(st.elapsed_sec) }}s</span>
            </div>
            <div class="api-call-body" style="display:none">
              {% if st.get('system') %}<div class="api-section-label">System</div><pre class="api-pre api-system">{{ st.system }}</pre>{% endif %}
              {% if st.get('prompt') %}<div class="api-section-label">Prompt</div><pre class="api-pre api-prompt">{{ st.prompt }}</pre>{% endif %}
              {% if st.get('response') %}<div class="api-section-label">Response</div><pre class="api-pre api-response">{{ st.response }}</pre>{% endif %}
            </div>
          </div>
          {% endfor %}
        </div>
        {% endif %}
      {% endfor %}

      {% for e in night_elims %}
      <div class="elim-item" style="margin-top:8px">
        <span>&#128565;</span>
        <span><strong>{{ e.player }}</strong> ({{ e.role }}) was killed by werewolves</span>
      </div>
      {% endfor %}
      <br>
    {% endif %}

    {% if rdata.discussion or rdata.bids %}
      {# Render discussion rounds in order, showing bid table at start of each speech_round #}
      {% set ns = namespace(cur_sr=0) %}
      {% for item in rdata.discussion %}
        {% set sr = item.speech_round %}
        {% if sr != ns.cur_sr %}
          {% set ns.cur_sr = sr %}
          {# Bid table header for this speech_round #}
          {% if ns.cur_sr > 1 %}<br>{% endif %}
          <span class="phase-label phase-day">Day, Discussion Round {{ sr }}</span>
          {% if rdata.bids.get(sr) %}
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px">
            {% for b in rdata.bids[sr] | sort(attribute='bid', reverse=true) %}
            {% set binfo = player_info.get(b.name, {}) %}
            {% set brc = role_color.get(binfo.get('role',''), '#888') %}
            {% set bid_val = b.bid %}
            {% if bid_val == 0 %}{% set bid_color = '#445' %}
            {% elif bid_val <= 2 %}{% set bid_color = '#666' %}
            {% elif bid_val == 3 %}{% set bid_color = '#889' %}
            {% elif bid_val == 4 %}{% set bid_color = '#f0a030' %}
            {% else %}{% set bid_color = '#e04040' %}{% endif %}
            {% set bsteps = call_steps.get(b.name, {}).get(rnum, {}).get('bid', {}).get(sr, []) %}
            <div style="background:#0f1120;border:1px solid #2a2a4a;border-radius:5px;padding:4px 10px;font-size:0.8rem;display:flex;align-items:center;gap:6px">
              <span style="color:{{ brc }};font-weight:600">{{ b.name }}</span>
              <span style="color:{{ bid_color }};font-weight:700;font-size:0.95rem">{{ bid_val }}</span>
              {% if bid_val == 0 %}<span style="color:#445;font-size:0.7rem">pass</span>{% endif %}
              {% if bsteps %}
              <span class="detail-block" style="display:none">
                <details style="margin:0"><summary style="font-size:0.68rem;color:#556;padding:0">bid log</summary>
                {% for st in bsteps %}
                <div class="api-call-block" style="margin-top:3px">
                  <div class="api-call-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
                    <span style="color:#778">{{ st.action }}</span>
                    <span style="color:#556;margin-left:6px">{{ st.prompt_tokens }}+{{ st.completion_tokens }} tk</span>
                    <span style="color:#445;margin-left:6px">{{ "%.2f"|format(st.elapsed_sec) }}s</span>
                  </div>
                  <div class="api-call-body" style="display:none">
                    {% if st.get('system') %}<div class="api-section-label">System</div><pre class="api-pre api-system">{{ st.system }}</pre>{% endif %}
                    {% if st.get('prompt') %}<div class="api-section-label">Prompt</div><pre class="api-pre api-prompt">{{ st.prompt }}</pre>{% endif %}
                    {% if st.get('response') %}<div class="api-section-label">Response</div><pre class="api-pre api-response">{{ st.response }}</pre>{% endif %}
                  </div>
                </div>
                {% endfor %}
                </details>
              </span>
              {% endif %}
            </div>
            {% endfor %}
          </div>
          {% else %}<br>{% endif %}
        {% endif %}
        {# Render the item (speech or pass) #}
        {% set pname = player_names.get(item.player_id, '') %}
        {% set info = player_info.get(pname, {}) %}
        {% set rc = role_color.get(info.get('role',''), '#888') %}
        {% set pc = pattern_color.get(info.get('pattern',''), '#888') %}
        {% if item.type == 'speech' %}
        {% set spsteps = call_steps.get(pname, {}).get(rnum, {}).get('speak', {}).get(sr, []) %}
        <div class="speech-item" style="--rc:{{ rc }}">
          <div class="speech-avatar">{{ pname[:2] }}</div>
          <div class="speech-body">
            <div class="speech-meta">
              <span class="sname">{{ pname }}</span> &nbsp;·&nbsp; {{ info.get('role','') }}
              <span class="pattern-badge" style="background:{{ pc }}22;color:{{ pc }};border:1px solid {{ pc }}44">{{ info.get('pattern','') }}</span>
            </div>
            <div class="speech-text">{{ item.text }}</div>
            {% if spsteps %}
            <div class="detail-block" style="display:none;margin-top:6px">
              {% for st in spsteps %}
              <div class="api-call-block">
                <div class="api-call-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
                  <span style="color:#778">{{ st.action }}</span>
                  <span style="color:#556;margin-left:8px">{{ st.prompt_tokens }}+{{ st.completion_tokens }} tk</span>
                  <span style="color:#445;margin-left:8px">{{ "%.2f"|format(st.elapsed_sec) }}s</span>
                </div>
                <div class="api-call-body" style="display:none">
                  {% if st.get('system') %}<div class="api-section-label">System</div><pre class="api-pre api-system">{{ st.system }}</pre>{% endif %}
                  {% if st.get('prompt') %}<div class="api-section-label">Prompt</div><pre class="api-pre api-prompt">{{ st.prompt }}</pre>{% endif %}
                  {% if st.get('response') %}<div class="api-section-label">Response</div><pre class="api-pre api-response">{{ st.response }}</pre>{% endif %}
                </div>
              </div>
              {% endfor %}
            </div>
            {% endif %}
          </div>
        </div>
        {% elif item.type == 'pass' %}
        <div class="pass-item" style="--rc:{{ rc }}">
          <div class="speech-avatar">{{ pname[:2] }}</div>
          <span class="pass-label">{{ pname }} passed</span>
        </div>
        {% endif %}
      {% endfor %}
      {# If no discussion items but bids exist (all passed before speaking), show bid tables #}
      {% if not rdata.discussion and rdata.bids %}
        {% for sr in rdata.bids | sort %}
        <span class="phase-label phase-day">Day, Discussion Round {{ sr }}</span>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px">
          {% for b in rdata.bids[sr] | sort(attribute='bid', reverse=true) %}
          {% set binfo = player_info.get(b.name, {}) %}
          {% set brc = role_color.get(binfo.get('role',''), '#888') %}
          {% set bid_val = b.bid %}
          {% if bid_val == 0 %}{% set bid_color = '#445' %}
          {% elif bid_val <= 2 %}{% set bid_color = '#666' %}
          {% elif bid_val == 3 %}{% set bid_color = '#889' %}
          {% elif bid_val == 4 %}{% set bid_color = '#f0a030' %}
          {% else %}{% set bid_color = '#e04040' %}{% endif %}
          <div style="background:#0f1120;border:1px solid #2a2a4a;border-radius:5px;padding:4px 10px;font-size:0.8rem;display:flex;align-items:center;gap:6px">
            <span style="color:{{ brc }};font-weight:600">{{ b.name }}</span>
            <span style="color:{{ bid_color }};font-weight:700;font-size:0.95rem">{{ bid_val }}</span>
            {% if bid_val == 0 %}<span style="color:#445;font-size:0.7rem">pass</span>{% endif %}
          </div>
          {% endfor %}
        </div>
        {% endfor %}
      {% endif %}
      <br>
    {% endif %}

    {% if rdata.votes %}
      <span class="phase-label phase-day">Day, Voting</span><br>
      {% set tally = namespace(d={}) %}
      {% for v in rdata.votes %}
      {% set voter = player_names[v.voter_id] %}
      {% set target = player_names[v.target_id] %}
      {% set vrc = role_color[player_info[voter].role] %}
      {% set trc = role_color[player_info[target].role] %}
      {% set vsteps = call_steps.get(voter, {}).get(rnum, {}).get('vote', []) %}
      {% set vreason = v.get('reason', '') %}
      <div class="vote-row" style="flex-wrap:wrap;gap:4px">
        <span class="vote-chip" style="color:{{ vrc }}">{{ voter }}</span>
        <span class="vote-arrow">&#8594;</span>
        <span class="vote-chip" style="color:{{ trc }}">{{ target }}</span>
        {% if vreason %}
        <span style="font-size:0.78rem;color:#778;font-style:italic;margin-left:4px">"{{ vreason }}"</span>
        {% endif %}
        {% if vsteps %}
        <div class="detail-block" style="display:none;width:100%;margin-top:4px">
          {% for st in vsteps %}
          <div class="api-call-block">
            <div class="api-call-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
              <span style="color:#778">{{ st.action }}</span>
              <span style="color:#556;margin-left:8px">{{ st.prompt_tokens }}+{{ st.completion_tokens }} tk</span>
              <span style="color:#445;margin-left:8px">{{ "%.2f"|format(st.elapsed_sec) }}s</span>
            </div>
            <div class="api-call-body" style="display:none">
              {% if st.get('system') %}<div class="api-section-label">System</div><pre class="api-pre api-system">{{ st.system }}</pre>{% endif %}
              {% if st.get('prompt') %}<div class="api-section-label">Prompt</div><pre class="api-pre api-prompt">{{ st.prompt }}</pre>{% endif %}
              {% if st.get('response') %}<div class="api-section-label">Response</div><pre class="api-pre api-response">{{ st.response }}</pre>{% endif %}
            </div>
          </div>
          {% endfor %}
        </div>
        {% endif %}
      </div>
      {% endfor %}
      <!-- tally -->
      <div style="margin-top:8px;font-size:0.8rem;color:#888">
        Tally:
        {% set tally_dict = {} %}
        {% for v in rdata.votes %}
          {% set target = player_names[v.target_id] %}
          {% if target not in tally_dict %}{% set _ = tally_dict.update({target: []}) %}{% endif %}
          {% set _ = tally_dict[target].append(player_names[v.voter_id]) %}
        {% endfor %}
        {% for target, voters in tally_dict | dictsort(by='value', reverse=true) %}
        {% set trc = role_color[player_info[target].role] %}
        <span style="color:{{ trc }}">{{ target }}</span> ×{{ voters|length }}
        {% if not loop.last %} &nbsp;|&nbsp; {% endif %}
        {% endfor %}
      </div>
    {% endif %}

    {% set day_elims = rdata.eliminations | selectattr('phase','eq','day') | list %}
    {% if day_elims %}
      {% for e in day_elims %}
      <div class="elim-item">
        <span>&#9993;</span>
        <span><strong>{{ e.player }}</strong> ({{ e.role }}) was voted out</span>
      </div>
      {% endfor %}
    {% endif %}

  </div>
  {% endfor %}

  <!-- Full call log (shown/hidden by checkbox) -->
  <div id="calllog-section" style="display:none;margin-bottom:16px">
    <div class="card" style="padding:14px 18px">
      <div style="font-size:0.8rem;color:#888;margin-bottom:8px">
        {{ call_log|length }} API calls total, click a row to expand prompt/response
      </div>
      <table class="call-log-table" id="call-log-table">
        <tr>
          <th>#</th><th>Caller</th>
          <th>Prompt tk</th><th>Completion tk</th><th>Total tk</th><th>Time (s)</th>
        </tr>
        {% for entry in call_log %}
        {% set pc = pattern_color.get(entry.pattern, '#888') %}
        {% set seq = loop.index %}
        {% set tr_entry = trace_map.get(seq) %}
        <tr class="call-row {{ 'has-trace' if tr_entry else '' }}"
            {% if tr_entry %}onclick="toggleTrace({{ seq }})"{% endif %}
            style="{{ 'cursor:pointer' if tr_entry else '' }}">
          <td>{{ seq }}</td>
          <td>
            <span style="color:{{ pc }}">{{ entry.player }}</span>
            <span style="color:#556">[{{ entry.pattern }}]</span>
            .{{ entry.action }}
            {% if tr_entry %}<span style="color:#336;font-size:0.7rem;margin-left:4px">&#9660;</span>{% endif %}
          </td>
          <td>{{ entry.prompt_tokens }}</td>
          <td>{{ entry.completion_tokens }}</td>
          <td>{{ entry.tokens }}</td>
          <td>{{ "%.2f"|format(entry.elapsed_sec) }}</td>
        </tr>
        {% if tr_entry %}
        <tr id="trace-{{ seq }}" style="display:none">
          <td colspan="6" style="padding:0">
            <div style="background:#080c18;padding:12px 16px;border-left:3px solid #2a3a5a">
              {% if tr_entry.system %}
              <div style="margin-bottom:10px">
                <div style="font-size:0.7rem;color:#556;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">System prompt</div>
                <pre style="white-space:pre-wrap;font-size:0.78rem;color:#7a9a7a;font-family:inherit;margin:0">{{ tr_entry.system }}</pre>
              </div>
              {% endif %}
              <div style="margin-bottom:10px">
                <div style="font-size:0.7rem;color:#556;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">User prompt</div>
                <pre style="white-space:pre-wrap;font-size:0.78rem;color:#aac;font-family:inherit;margin:0">{{ tr_entry.prompt }}</pre>
              </div>
              <div>
                <div style="font-size:0.7rem;color:#556;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">Model response</div>
                <pre style="white-space:pre-wrap;font-size:0.78rem;color:#aaffaa;font-family:inherit;margin:0">{{ tr_entry.response }}</pre>
              </div>
            </div>
          </td>
        </tr>
        {% endif %}
        {% endfor %}
      </table>
    </div>
  </div>

  <!-- API section -->
  <hr>
  <h2>API Usage by Pattern</h2>
  <div class="pat-grid">
    {% for pat, s in api.per_pattern.items() %}
    {% set pc = pattern_color.get(pat, '#888') %}
    <div class="pat-card" style="--pc:{{ pc }}">
      <div class="pat-name">{{ pat }}</div>
      <div class="pat-stat">Calls &nbsp;<span class="pat-val">{{ s.calls }}</span></div>
      <div class="pat-stat">Tokens &nbsp;<span class="pat-val">{{ "{:,}".format(s.tokens) }}</span></div>
      <div class="pat-stat">Time &nbsp;<span class="pat-val">{{ "%.1f"|format(s.elapsed_sec) }}s</span></div>
    </div>
    {% endfor %}
  </div>

  {% if survival_avg %}
  <h2>Survival (avg rounds) by Pattern</h2>
  <div class="pat-grid">
    {% for pat, avg in survival_avg.items() %}
    {% set pc = pattern_color.get(pat, '#888') %}
    <div class="pat-card" style="--pc:{{ pc }}">
      <div class="pat-name">{{ pat }}</div>
      <div class="pat-stat">Avg survived &nbsp;<span class="pat-val" style="font-size:1.1rem;font-weight:700;color:{{ pc }}">{{ "%.1f"|format(avg) }}</span> rounds</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

</div>

<script>
function toggleDetail() {
  var show = document.getElementById('toggle-detail').checked;
  document.querySelectorAll('.detail-block').forEach(function(el) {
    el.style.display = show ? '' : 'none';
  });
  var clCb = document.getElementById('toggle-calllog');
  var clLabel = document.getElementById('calllog-label');
  if (!show) {
    clCb.checked = false;
    clCb.disabled = true;
    clLabel.style.opacity = '0.4';
    document.getElementById('calllog-section').style.display = 'none';
  } else {
    clCb.disabled = false;
    clLabel.style.opacity = '1';
  }
}
function toggleCallLog() {
  var show = document.getElementById('toggle-calllog').checked;
  document.getElementById('calllog-section').style.display = show ? '' : 'none';
}
function toggleTrace(seq) {
  var row = document.getElementById('trace-' + seq);
  if (!row) return;
  row.style.display = row.style.display === 'none' ? '' : 'none';
}
// Full call log label starts disabled
document.getElementById('calllog-label').style.opacity = '0.4';
// Highlight has-trace rows on hover
document.querySelectorAll('.has-trace').forEach(function(row) {
  row.addEventListener('mouseenter', function() { row.style.background = '#1a2030'; });
  row.addEventListener('mouseleave', function() { row.style.background = ''; });
});
</script>
</body></html>
"""

# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def home():
    games = load_summaries()
    stats = compute_stats(games)
    return render_template_string(
        HOME_TEMPLATE,
        css=COMMON_CSS,
        games=list(reversed(games)),
        stats=stats,
        pattern_color=PATTERN_COLOR,
    )


@app.route("/game/<int:game_id>")
def game_detail(game_id):
    data = load_game(game_id)
    if data is None:
        abort(404)

    result   = data["result"]
    schedule = data["schedule"]

    players_list = result.get("players", [])
    # Fallback for old logs that lack the "players" field
    if not players_list:
        players_list = [
            {"id": i, "name": PLAYER_NAMES[i], "role": None, "pattern": schedule.get(SLOT_ORDER[i], "?")}
            for i in range(len(SLOT_ORDER))
        ]

    player_info = build_player_info(players_list, schedule)
    # id -> name lookup (used in template for votes/speeches)
    player_names = {p["id"]: p["name"] for p in players_list}

    elim_map = {e["player"]: e for e in result["eliminations"]}

    # Build name->id reverse lookup for votes (new format uses names, old format used ids)
    name_to_id = {p["name"]: p["id"] for p in players_list}

    # Group by round
    rounds_data = defaultdict(lambda: {"speeches": [], "passes": [], "votes": [], "eliminations": [], "night_actions": [], "bids": {}, "discussion": []})
    for s in result.get("speeches", []):
        rounds_data[s["round"]]["speeches"].append(s)
    for p in result.get("passes", []):
        rounds_data[p["round"]]["passes"].append(p)
    for v in result.get("votes", []):
        # Normalize votes: new format has "voter"/"target" names; old format has voter_id/target_id
        if "voter_id" not in v and "voter" in v:
            v = dict(v)
            v["voter_id"] = name_to_id.get(v["voter"], 0)
            v["target_id"] = name_to_id.get(v["target"], 0)
        rounds_data[v["round"]]["votes"].append(v)
    for e in result.get("eliminations", []):
        rounds_data[e["round"]]["eliminations"].append(e)
    for a in result.get("night_actions", []):
        rounds_data[a["round"]]["night_actions"].append(a)
    # Bids: group by (round, speech_round) -> list of {name, bid} sorted desc
    for b in result.get("bids", []):
        pid = b.get("player_id")
        pname = player_names.get(pid, f"P{pid}")
        key = b["speech_round"]
        rounds_data[b["round"]]["bids"].setdefault(key, [])
        rounds_data[b["round"]]["bids"][key].append({"name": pname, "bid": b["bid"]})

    # Build unified discussion timeline per round: merge speeches+passes ordered by (speech_round, position)
    # Each item: {type:"speech"|"pass", speech_round, position, player_id, text?, player_name, info, ...}
    for rnum, rdata in rounds_data.items():
        items = []
        for s in rdata["speeches"]:
            items.append({
                "type": "speech",
                "speech_round": s.get("speech_round", 1),
                "position": s.get("position", 0),
                "player_id": s["player_id"],
                "text": s["text"],
            })
        for p in rdata["passes"]:
            items.append({
                "type": "pass",
                "speech_round": p.get("speech_round", 1),
                "position": p.get("position", 0),
                "player_id": p["player_id"],
            })
        # Sort by (speech_round, position); old logs without position stay in insertion order
        items.sort(key=lambda x: (x["speech_round"], x["position"]))
        rdata["discussion"] = items

    # Load trace for prompt/response data (seq-indexed, 1-based)
    trace = load_trace(game_id)
    has_trace = len(trace) > 0
    trace_map = {e["seq"]: e for e in trace}  # seq -> full trace entry

    # Parse call_log and attach trace data to each entry
    call_log = parse_call_log(result.get("call_log", []))
    for i, entry in enumerate(call_log):
        seq = i + 1
        tr = trace_map.get(seq)
        if tr:
            entry["system"]   = tr.get("system", "")
            entry["prompt"]   = tr.get("prompt", "")
            entry["response"] = tr.get("response", "")

    # Build per-player queues grouped by action type
    # action type: "speak" | "vote" | "night" | "bid"
    player_action_queues = defaultdict(lambda: defaultdict(list))
    for entry in call_log:
        action = entry["action"]
        atype_raw = action.split(".")[0] if "." in action else action
        if "bid" in atype_raw:
            atype = "bid"
        elif "speak" in atype_raw or "speech" in atype_raw:
            atype = "speak"
        elif "vote" in atype_raw:
            atype = "vote"
        elif "night" in atype_raw or "action" in atype_raw:
            atype = "night"
        else:
            atype = "speak"  # format_retry and other misc -> attach to speak
        player_action_queues[entry["player"]][atype].append(entry)

    # Distribute speak calls across (round, speech_round) slots
    # Key: (rnum, sr) -> list of speech items for that player
    player_speech_slots = defaultdict(lambda: defaultdict(list))  # pname -> (rnum,sr) -> count
    for rnum, rdata in rounds_data.items():
        for item in rdata["discussion"]:
            if item["type"] == "speech":
                pname = player_names.get(item["player_id"], "")
                sr = item["speech_round"]
                player_speech_slots[pname][(rnum, sr)].append(item)

    call_steps = {}  # {player: {round: {atype: [entries]}}}

    # Speak: one slot per (rnum, sr) speech occurrence
    for pname in player_names.values():
        queue = list(player_action_queues[pname]["speak"])
        if not queue:
            continue
        slots = sorted(player_speech_slots[pname].keys())  # [(rnum,sr), ...]
        if not slots:
            continue
        per_slot = max(1, len(queue) // len(slots))
        idx = 0
        for i, (rnum, sr) in enumerate(slots):
            if pname not in call_steps:
                call_steps[pname] = {}
            if rnum not in call_steps[pname]:
                call_steps[pname][rnum] = {}
            if i == len(slots) - 1:
                call_steps[pname][rnum].setdefault("speak", {})
                call_steps[pname][rnum]["speak"][sr] = queue[idx:]
            else:
                call_steps[pname][rnum].setdefault("speak", {})
                call_steps[pname][rnum]["speak"][sr] = queue[idx:idx + per_slot]
                idx += per_slot

    # Bid: distribute across rounds (2 speech_rounds each)
    for pname in player_names.values():
        queue = list(player_action_queues[pname]["bid"])
        if not queue:
            continue
        # Collect (rnum, sr) where this player had a bid
        bid_slots = []
        for b in result.get("bids", []):
            if player_names.get(b.get("player_id")) == pname:
                bid_slots.append((b["round"], b["speech_round"]))
        bid_slots.sort()
        if not bid_slots:
            continue
        per_slot = max(1, len(queue) // len(bid_slots))
        idx = 0
        for i, (rnum, sr) in enumerate(bid_slots):
            if pname not in call_steps:
                call_steps[pname] = {}
            if rnum not in call_steps[pname]:
                call_steps[pname][rnum] = {}
            call_steps[pname][rnum].setdefault("bid", {})
            if i == len(bid_slots) - 1:
                call_steps[pname][rnum]["bid"][sr] = queue[idx:]
            else:
                call_steps[pname][rnum]["bid"][sr] = queue[idx:idx + per_slot]
                idx += per_slot

    # Attach vote and night calls per round per player
    vote_counts   = defaultdict(lambda: defaultdict(int))
    night_counts  = defaultdict(lambda: defaultdict(int))
    for rnum, rdata in rounds_data.items():
        for v in rdata["votes"]:
            vote_counts[player_names[v["voter_id"]]][rnum] += 1
        for a in rdata["night_actions"]:
            night_counts[a["actor"]][rnum] += 1

    for pname in player_names.values():
        for atype, counts in [("vote", vote_counts), ("night", night_counts)]:
            queue = player_action_queues[pname][atype]
            if not queue:
                continue
            rounds_acted = []
            for rnum in sorted(rounds_data.keys()):
                for _ in range(counts[pname][rnum]):
                    rounds_acted.append(rnum)
            if not rounds_acted:
                continue
            per_slot = max(1, len(queue) // len(rounds_acted))
            idx = 0
            for i, rnum in enumerate(rounds_acted):
                if pname not in call_steps:
                    call_steps[pname] = {}
                if rnum not in call_steps[pname]:
                    call_steps[pname][rnum] = {}
                if i == len(rounds_acted) - 1:
                    call_steps[pname][rnum][atype] = queue[idx:]
                else:
                    call_steps[pname][rnum][atype] = queue[idx:idx + per_slot]
                    idx += per_slot

    winner = result["winner"]
    n_rounds = result["rounds"]

    # prev/next game
    all_ids = sorted(p.stem for p in GAMES_DIR.glob("*.json") if p.stem.isdigit())
    id_str = f"{game_id:04d}"
    try:
        pos = all_ids.index(id_str)
        prev_id = int(all_ids[pos-1]) if pos > 0 else None
        next_id = int(all_ids[pos+1]) if pos < len(all_ids)-1 else None
    except ValueError:
        prev_id = next_id = None

    return render_template_string(
        GAME_TEMPLATE,
        css=COMMON_CSS,
        game_id=game_id,
        timestamp=data.get("timestamp", ""),
        winner_label="Village wins" if winner == "village" else "Werewolves win",
        winner_color="#27ae60" if winner == "village" else "#c0392b",
        rounds=n_rounds,
        detection=result.get("detection_accuracy", 0),
        vote_accuracy=result.get("vote_accuracy", 0),
        vote_accuracy_by_pattern=result.get("vote_accuracy_by_pattern", {}),
        api=result["api"],
        llm_model=result.get("model", "unknown"),
        survival_avg=result.get("survival_avg_rounds", {}),
        player_info=player_info,
        elim_map=elim_map,
        rounds_data=rounds_data,
        player_names=player_names,
        call_log=call_log,
        call_steps=call_steps,
        role_color=ROLE_COLOR,
        pattern_color=PATTERN_COLOR,
        prev_id=prev_id,
        next_id=next_id,
        has_trace=has_trace,
        trace_map=trace_map,
    )


@app.route("/api/stats")
def api_stats():
    games = load_summaries()
    return jsonify(compute_stats(games))


@app.route("/api/trace/<int:game_id>")
def api_trace(game_id):
    trace = load_trace(game_id)
    if not trace:
        abort(404)
    return jsonify(trace)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"Dashboard -> http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
