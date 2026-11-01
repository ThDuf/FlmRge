"""Rendu headless du menu (toutes les étapes + étape joueurs) : vérifie le dessin."""
import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame
import main
from game.game import available_stages

ui = main.FlammeRougeGame()
ui.width, ui.height = 1200, 800
ui.screen = pygame.display.set_mode((1200, 800))
names = [n for n, _d, _c in available_stages()]
for i, name in enumerate(names):
    ui.menu_index = i
    ui._draw_menu()
    pygame.display.flip()
ui.menu_step = 'players'
ui._pending_stage = names[-1]
ui._draw_menu()
pygame.display.flip()
print(f"menu rendu OK ({len(names)} etapes + ecran joueurs)")
