"""Smoke test de rendu : exécute les méthodes de dessin à plusieurs tailles."""
import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main
from game.game import Phase

# --- Menu de sélection d'étape (au lancement, sans stage) ---
ui_menu = main.FlammeRougeGame()
assert ui_menu.game is None
for w, h in [(900, 600), (1200, 800), (1600, 1000)]:
    ui_menu.width, ui_menu.height = w, h
    ui_menu.screen.fill((28, 32, 38))
    ui_menu._draw_header()
    ui_menu._draw_menu()
    for i, (name, desc, code, rect) in enumerate(ui_menu._menu_entries()):
        assert rect.bottom <= h, f"entrée menu {name} hors écran"
print("MENU: rendu OK a 3 tailles, toutes les entrées visibles")

ui = main.FlammeRougeGame(stage="La Haut Montagne")

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

# Jouer les cartes puis mouvement PAS-À-PAS (bouton "Mouvement suivant" affiché)
for player in ui.game.players:
    for runner in player.get_runners():
        ui.game.play_card(player, runner, runner.hand[0])
ui._start_movement_phase()
while ui.showing_movement:
    render_all()
    assert ui._button_info() is not None, "bouton absent pendant le pas-a-pas mouvement"
    if ui._next_movement_step():
        ui.showing_movement = False
render_all()
print("MOVEMENT pas-a-pas: rendu OK")

# Aspiration pas-à-pas complète (bouton "Aspiration suivante" affiché)
steps = ui.game.resolve_aspiration_phase()
if steps:
    ui.aspiration_movements = steps
    ui._initialize_aspiration()
while ui.showing_aspiration:
    render_all()
    assert ui._button_info() is not None, "bouton absent pendant le pas-a-pas aspiration"
    if ui._next_aspiration_step():
        ui._finish_aspiration_phase()
else:
    ui._finish_aspiration_phase()
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
