import json
from pathlib import Path

logs_dir = Path(r"d:\_Development\Projects\University_Studies\yzv445\gitten_cektiklerim\src\projects\p271\logs\games")

for path in sorted(logs_dir.glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    result = data["result"]
    call_log = result.get("call_log", [])
    rounds = result["rounds"]
    game_id = data["game_id"]

    n = len(call_log)
    per_round = n // rounds if rounds else n

    print(f"Game {game_id} ({rounds} rounds, {n} calls):")
    for r in range(rounds):
        start = r * per_round
        end = start + per_round if r < rounds - 1 else n
        chunk = call_log[start:end]
        if chunk:
            avg_prompt = sum(c["prompt_tokens"] for c in chunk) / len(chunk)
            max_prompt = max(c["prompt_tokens"] for c in chunk)
            first_prompt = chunk[0]["prompt_tokens"]
            last_prompt = chunk[-1]["prompt_tokens"]
            print(f"  Round {r+1}: first={first_prompt:,}  avg={avg_prompt:,.0f}  max={max_prompt:,}  last={last_prompt:,}")
    print()
