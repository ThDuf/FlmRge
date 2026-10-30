"""Smoke test de rendu : exécute les méthodes de dessin à plusieurs tailles."""
import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main
from game.game import Phase

ui = main.FlammeRougeGame()

def render_all():
    ui.screen.fill(main.WHITE)
    ui._draw_track()
    ui._draw_runners()
    ui._draw_ui()
    if ui.show_decks:
        ui._draw_decks()

# Phase d'énergie, plusieurs tailles de fenêtre
for w, h in [(900, 600), (1200, 800), (1600, 1000), (1920, 1080)]:
    ui.width, ui.height = w, h
    render_all()
print("ENERGY: rendu OK a 4 tailles")

# Jouer les cartes puis mouvement
for player in ui.game.players:
    for runner in player.get_runners():
        ui.game.play_card(player, runner, runner.hand[0])
ui.game.resolve_movement_phase()
render_all()
print("MOVEMENT: rendu OK")

# Aspiration pas-à-pas complète
steps = ui.game.resolve_aspiration_phase()
for step in steps:
    ui.game.apply_slipstream_step(step)
    render_all()
print(f"ASPIRATION: rendu OK ({len(steps)} etapes)")

# Phase terminale + decks affichés
ui._finish_aspiration_phase()
ui.show_decks = True
render_all()
print("TERMINAL + decks: rendu OK")

# Fin de partie (overlay gagnant)
ui.game.game_over = True
ui.game.winner = ui.game.players[0]
render_all()
print("GAME_OVER: rendu OK")
