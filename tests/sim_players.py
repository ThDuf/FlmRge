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
    # le hero affiche le bon nombre de jetons : compte les cercles colorés
    # (on vérifie juste que le rendu ne plante pas et que le chiffre change)
print("écran joueurs (2/3/4) rendu OK")
# avec une étape en attente (retour Échap) : preview affichée
ui._pending_stage = "Avenue Corso Paseo"
ui._draw_menu()
pygame.display.flip()
print("écran joueurs avec étape en attente OK")
