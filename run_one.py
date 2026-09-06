import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tournament.runner import run_tournament
run_tournament(n_games=1, verbose=False)
