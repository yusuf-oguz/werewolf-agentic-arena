"""
Hipotez: İlk konuşanlar oylamada daha çok hedef alınıyor mu?
Her round için:
- Konuşma sırası (speech_round=1'deki pozisyon)
- O round'da oy ile elenen oyuncu
- Elenenin konuşma sırasındaki pozisyonu
"""
import json
from pathlib import Path
from collections import defaultdict

LOGS_DIR = Path(r"d:\_Development\Projects\University_Studies\yzv445\gitten_cektiklerim\src\projects\p271\logs\games")
PLAYER_NAMES_FALLBACK = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

results = []

for path in sorted(LOGS_DIR.glob("*.json")):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    result = data["result"]
    players_list = result.get("players", [])
    if players_list:
        id_to_name = {p["id"]: p["name"] for p in players_list}
    else:
        id_to_name = {i: PLAYER_NAMES_FALLBACK[i] for i in range(8)}

    # Group speeches by round, then by speech_round within day
    # speeches list: [{round, player_id, text}, ...]
    # We need to know the order within each (game_round, speech_round)
    # The list is already in insertion order = speaking order

    speeches = result.get("speeches", [])
    votes    = result.get("votes", [])
    elims    = result.get("eliminations", [])

    # Build round -> ordered list of player_ids (first speech_round only = first half of speeches per round)
    # N=2 speech rounds per day: speeches per game_round = 2 * n_alive
    # We want speech_round=1 order (first N speeches in the round)
    round_speeches = defaultdict(list)
    for s in speeches:
        round_speeches[s["round"]].append(s["player_id"])

    # Vote tally per round
    round_votes = defaultdict(lambda: defaultdict(int))  # round -> target_id -> count
    for v in votes:
        round_votes[v["round"]][v["target_id"]] += 1

    # Day eliminations per round
    day_elims = {e["round"]: e for e in elims if e["cause"] == "vote"}

    game_id = data["game_id"]

    for rnum, pid_order in round_speeches.items():
        if rnum not in day_elims:
            continue

        elim = day_elims[rnum]
        elim_name = elim["player"]

        # Find elim player_id from name
        elim_pid = next((pid for pid, name in id_to_name.items() if name == elim_name), None)
        if elim_pid is None:
            continue

        # pid_order has duplicates (speech_round=1 and speech_round=2, both same order)
        # First half = speech_round 1 order
        n_alive = len(set(pid_order))
        first_round_order = pid_order[:n_alive]  # first speech_round

        if elim_pid not in first_round_order:
            continue

        position = first_round_order.index(elim_pid) + 1  # 1-indexed
        n_players = len(first_round_order)
        relative_pos = position / n_players  # 0..1, lower = earlier

        vote_count = round_votes[rnum].get(elim_pid, 0)
        total_votes = sum(round_votes[rnum].values())

        results.append({
            "game": game_id,
            "round": rnum,
            "eliminated": elim_name,
            "role": elim["role"],
            "speech_position": position,
            "n_players": n_players,
            "relative_pos": round(relative_pos, 3),
            "votes_received": vote_count,
            "total_votes": total_votes,
        })

print(f"{'Game':>5} {'Rnd':>4} {'Player':<10} {'Role':<10} {'Pos':>4} {'N':>3} {'Rel':>6} {'Votes':>6}")
print("-" * 60)
for r in results:
    print(f"{r['game']:>5} {r['round']:>4} {r['eliminated']:<10} {r['role']:<10} "
          f"{r['speech_position']:>4} {r['n_players']:>3} {r['relative_pos']:>6.3f} "
          f"{r['votes_received']:>4}/{r['total_votes']}")

# Summary
if results:
    avg_rel = sum(r["relative_pos"] for r in results) / len(results)
    print(f"\nOrtalama relatif pozisyon (elenenler): {avg_rel:.3f}")
    print(f"(0=en erken, 1=en geç; rastgele beklenti=0.5)")
    print(f"\nn = {len(results)} round")

    # Early (top half) vs late (bottom half)
    early = [r for r in results if r["relative_pos"] <= 0.5]
    late  = [r for r in results if r["relative_pos"] >  0.5]
    print(f"İlk yarıdan elenen: {len(early)} ({100*len(early)/len(results):.0f}%)")
    print(f"İkinci yarıdan elenen: {len(late)} ({100*len(late)/len(results):.0f}%)")
