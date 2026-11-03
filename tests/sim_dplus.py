import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import main
from game.game import available_stages
ui = main.FlammeRougeGame()
for name, _d, code in available_stages():
    alt = ui._stage_profile(name, code=code)
    n = len(alt) - 1
    dplus = sum(max(0, alt[i+1]-alt[i]) for i in range(n))
    print(f"{name}: {n} km, D+ = {dplus}, alt max {max(alt)}")
