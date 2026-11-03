import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame, main
for w, h in ((1200, 800), (1400, 900), (1000, 700)):
    pygame.display.set_mode((w, h))
    ui = main.FlammeRougeGame()
    ui.width, ui.height = w, h
    ui.screen = pygame.display.set_mode((w, h))
    pr = ui._preview_rect()
    sr = ui._menu_search_rect()
    print(f"fenetre {w}x{h}: preview={pr} search={sr} chevauchement={pr.colliderect(sr)}")
    ui._draw_menu()
print("OK")
