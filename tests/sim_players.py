import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame, main
pygame.display.set_mode((1200, 800))
ui = main.FlammeRougeGame()
ui.width, ui.height = 1200, 800
ui.screen = pygame.display.set_mode((1200, 800))
ui.screen.fill(main.BG)
for count in (2, 3, 4):
    ui.player_count = count
    ui._draw_menu()  # 1er écran = joueurs
    pygame.display.flip()
print("écran joueurs (2/3/4) rendu OK")
# vérification pixellique : pour 3 joueurs, le hero contient les 3 couleurs
# d'équipe (chacune avec un R et un S)
ui.player_count = 3
ui.screen.fill(main.BG)
ui._draw_menu()
hero = pygame.Rect(ui._players_frame_rect().right + 16, 60, ui.width - 16 - (ui._players_frame_rect().right + 16), ui.height - 72)
found = {c: 0 for c in [(255, 0, 0), (0, 0, 255), (0, 165, 0)]}
for x in range(hero.x, hero.right, 2):
    for y in range(hero.y, hero.bottom, 2):
        c = ui.screen.get_at((x, y))[:3]
        if c in found:
            found[c] += 1
print("couleurs présentes dans le hero (3 joueurs):", found)
assert all(v > 20 for v in found.values()), "il manque une couleur d'équipe dans le hero"
print("R+S par couleur OK")
# avec une étape en attente (retour Échap) : preview affichée
ui._pending_stage = "Avenue Corso Paseo"
ui._draw_menu()
pygame.display.flip()
print("écran joueurs avec étape en attente OK")
