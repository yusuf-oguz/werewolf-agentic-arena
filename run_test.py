"""Single-game test with all 4 patterns (2 players each)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from game.state import Player, Role, Pattern
from game.engine import run_game
from agents.baseline import BaselineAgent
from agents.reflection import ReflectionAgent
from agents.react import ReActAgent
from agents.tot import ToTAgent

AGENT_CLASSES = {
    Pattern.BASELINE:   BaselineAgent,
    Pattern.REFLECTION: ReflectionAgent,
    Pattern.REACT:      ReActAgent,
    Pattern.TOT:        ToTAgent,
}

# 8 players: 2 of each pattern
# Roles: 2 werewolf, 1 seer, 1 doctor, 4 villager
setup = [
    ("Alice",   Role.WEREWOLF, Pattern.BASELINE),
    ("Bob",     Role.WEREWOLF, Pattern.REFLECTION),
    ("Carol",   Role.SEER,     Pattern.REACT),
    ("Dave",    Role.DOCTOR,   Pattern.TOT),
    ("Eve",     Role.VILLAGER, Pattern.BASELINE),
    ("Frank",   Role.VILLAGER, Pattern.REFLECTION),
    ("Grace",   Role.VILLAGER, Pattern.REACT),
    ("Hank",    Role.VILLAGER, Pattern.TOT),
]

players = [
    Player(id=i, name=name, role=role, pattern=pattern)
    for i, (name, role, pattern) in enumerate(setup)
]
for p in players:
    p._agent = AGENT_CLASSES[p.pattern](p)

result = run_game(players, verbose=True)

print("\n=== RESULT ===")
print(f"Winner         : {result['winner']}")
print(f"Rounds         : {result['rounds']}")
print(f"Detection acc  : {result['detection_accuracy']}")
print(f"Survival (avg) : {result['survival_avg_rounds']}")
print(f"Total API calls: {result['api']['total_calls']}")
print(f"Total tokens   : {result['api']['total_tokens']}")
print(f"Total time     : {result['api']['total_elapsed_sec']}s")
print("\nPer-pattern API usage:")
for pattern, stats in result['api']['per_pattern'].items():
    print(f"  {pattern:12s}: {stats['calls']} calls, {stats['tokens']} tokens, {stats['elapsed_sec']:.1f}s")
