import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame, main
pygame.display.set_mode((1200, 800))
ui = main.FlammeRougeGame()
ui.width, ui.height = 1200, 800
ui.screen = pygame.display.set_mode((1200, 800))
ui.screen.fill(main.BG)
ui._draw_menu()
frame = ui._menu_frame_rect()
# pixel juste sous le cadre = ombre (plus sombre que le fond BG)
below = ui.screen.get_at((frame.centerx, frame.bottom + 2))[:3]
bg = main.BG
print("fond:", bg, "sous le cadre:", below)
assert sum(below) < sum(bg) - 10, "pas d'ombre sous le cadre"
# pixel dans le cadre = blanc
inside = ui.screen.get_at((frame.centerx, frame.centery))[:3]
print("dans le cadre:", inside)
assert inside == (255, 255, 255)
print("ombres OK")
