"""Vérification headless du thème clair + profil km/D+/drapeau + panneau groupes."""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame  # noqa: E402
import main  # noqa: E402
from game.game import available_stages  # noqa: E402


def px(surf, pos):
    return surf.get_at(pos)[:3]


def main_():
    pygame.display.set_mode((1200, 800))

    # --- Menu : fond clair, profil avec échelle km / D+ / drapeau ---
    ui = main.FlammeRougeGame()
    ui.width, ui.height = 1200, 800
    ui.screen = pygame.display.set_mode((1200, 800))
    names = [n for n, _d, _c in available_stages()]
    ui.menu_index = names.index("Col du Ballon")
    ui.screen.fill(main.BG)
    ui._draw_menu()
    corner = px(ui.screen, (30, 700))
    print("fond menu (30,700):", corner, "-> clair:", sum(corner) > 600)
    pr = ui._menu_profile_rect(ui._preview_rect())
    found = {"orange": 0, "blue": 0, "flag": 0, "gold": 0}
    for x in range(pr.x, pr.right):
        for y in range(pr.y, pr.bottom):
            c = px(ui.screen, (x, y))
            if c[0] > 230 and 160 < c[1] < 225 and c[2] < 180:
                found["orange"] += 1
            elif c[2] > 220 and c[0] < 200 and 130 < c[1] < 215:
                found["blue"] += 1
            elif c == (0, 0, 0) or c == (255, 255, 255):
                found["flag"] += 1  # damier du drapeau
            elif c[0] > 200 and 180 < c[1] < 225 and c[2] < 120:
                found["gold"] += 1  # mât/échelle arrivée (jaune, anti-aliasing inclus)
    print("profil Col du Ballon:", found)
    assert found["orange"] > 50 and found["blue"] > 50, "segments colores manquants"
    assert found["flag"] > 4, "drapeau damier manquant"
    assert found["gold"] > 10, "ligne d'arrivée (mât jaune) manquante"

    # --- Écran de course : bandeau clair + panneau des groupes ---
    ui._select_stage("Avenue Corso Paseo")
    ui.game.auto_place_riders()  # placement auto -> coureurs sur la piste
    ui.screen.fill(main.WHITE)
    frame = ui._frame_rect()
    pygame.draw.rect(ui.screen, (238, 240, 244), frame, border_radius=10)
    ui.screen.set_clip(frame)
    ui._draw_track()
    ui._draw_runners()
    ui.screen.set_clip(None)
    ui._draw_ui()
    hdr = px(ui.screen, (600, 20))
    print("bandeau titre (600,20):", hdr, "-> clair:", sum(hdr) > 600)
    assert sum(hdr) > 600, "bandeau pas clair"
    # panneau groupes en haut à gauche du cadre : coin du panneau = PANEL blanc
    gp = px(ui.screen, (frame.x + 12, frame.y + 12))
    print("panneau groupes (coin):", gp)
    assert sum(gp) > 700, "panneau groupes absent ou sombre"
    groups = ui._group_names()
    print("groupes au départ:", [(g[0], g[2]) for g in groups])
    assert groups and groups[0][0] in ("Peloton", "Tête de course")

    # --- Preview du menu : route épaisse + ligne d'arrivée, PAS de lettres ---
    ui2 = main.FlammeRougeGame()
    ui2.width, ui2.height = 1200, 800
    ui2.screen = pygame.display.set_mode((1200, 800))
    ui2.menu_index = names.index("Avenue Corso Paseo") + 1  # +1 : l'index 0 est l'en-tête de catégorie
    ui2.screen.fill(main.BG)
    ui2._draw_menu()
    rect = ui2._preview_rect()
    trect = ui2._preview_track_rect(rect)
    yellow = black = 0
    for x in range(trect.x, trect.right):
        for y in range(trect.y, trect.bottom):
            c = px(ui2.screen, (x, y))
            if c == (240, 210, 60):
                yellow += 1
            elif c == (0, 0, 0):
                black += 1
    print(f"preview tracé: px arrivée (240,210,60)={yellow}, px noirs drapeau={black}")
    assert yellow > 30, "ligne d'arrivée absente du tracé"
    assert black > 8, "drapeau damier absent du tracé"

    # --- Éditeur : les lettres des tuiles sont toujours dessinées ---
    ui2.menu_step = 'editor'
    ui2.editor_code = 'abKcdEfghijklmnopqrstu'
    ui2._draw_editor(pygame.mouse.get_pos())
    print("thème clair + profil + groupes OK")


if __name__ == '__main__':
    main_()
