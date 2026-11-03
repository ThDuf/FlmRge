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
    imax = max(range(len(alt)), key=lambda i: alt[i])
    L = 0
    i = imax
    while i > 0 and alt[i] > alt[i-1]:
        L += 1
        i -= 1
    print(f"{name}: {n} km, D+={dplus}, sommet case {imax}, montee avant col = {L} cases")
