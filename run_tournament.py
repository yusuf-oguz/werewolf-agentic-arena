"""
Entry point for the tournament runner.
Usage:
  python run_tournament.py          # run 1 game (default)
  python run_tournament.py 5        # run 5 games
  python run_tournament.py 5 quiet  # run 5 games without per-turn output
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tournament.runner import run_tournament

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
verbose = "quiet" not in sys.argv

run_tournament(n_games=n, verbose=verbose)
