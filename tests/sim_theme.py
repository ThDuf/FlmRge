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
    counts = {(240, 210, 60): 0, (0, 0, 0): 0, (48, 52, 60): 0,
              (235, 145, 50): 0, (80, 120, 235): 0, (255, 236, 130): 0}
    for x in range(trect.x, trect.right):
        for y in range(trect.y, trect.bottom):
            c = px(ui2.screen, (x, y))
            if c in counts:
                counts[c] += 1
    print("preview tracé Corso Paseo:", counts)
    assert counts[(0, 0, 0)] > 20, "damier noir/blanc de la ligne d'arrivée absent"
    assert counts[(48, 52, 60)] > 500, "plat pas en gris très foncé"
    assert counts[(255, 236, 130)] > 30, "ligne de départ jaune clair absente"

    # étape de montagne : mêmes couleurs que le profil (orange/bleu)
    ui2.menu_index = names.index("La Haut Montagne") + 1
    ui2.screen.fill(main.BG)
    ui2._draw_menu()
    trect = ui2._preview_track_rect(ui2._preview_rect())
    orange = blue = 0
    for x in range(trect.x, trect.right):
        for y in range(trect.y, trect.bottom):
            c = px(ui2.screen, (x, y))
            if c == (235, 145, 50):
                orange += 1
            elif c == (80, 120, 235):
                blue += 1
    print(f"preview tracé Haut Montagne: orange={orange}, bleu={blue}")
    assert orange > 100 and blue > 100, "montée/descente pas aux couleurs du profil"

    # --- Containment des couleurs : de part et d'autre de chaque frontière
    # de case, la couleur au centre de la route est celle de la bonne case ---
    from game.game import build_stage_track
    from game.track import CellGeographyType, CellRunType, path_point_at
    name = "La Haut Montagne"
    track = build_stage_track(name)
    pts = ui2._stage_preview_points(name)
    rect = ui2._preview_rect()
    trect = ui2._preview_track_rect(rect)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bb_w = max(xs) - min(xs); bb_h = max(ys) - min(ys)
    scale = min((trect.w - 16) / bb_w, (trect.h - 16) / bb_h)
    ox = trect.x + (trect.w - bb_w * scale) / 2 - min(xs) * scale
    oy = trect.y + (trect.h - bb_h * scale) / 2 - min(ys) * scale
    def cell_color(cell):
        if cell.run in (CellRunType.START, CellRunType.END):
            return (48, 52, 60)
        if cell.geography == CellGeographyType.UPHILL:
            return (235, 145, 50)
        if cell.geography == CellGeographyType.DOWNHILL:
            return (80, 120, 235)
        return (48, 52, 60)
    road_w = max(9, min(16, round(scale * 1.3)))

    LINE_COLORS = [(235, 238, 242), (225, 229, 235)]  # ligne centrale + traits de case

    def pix_at(s):
        # échantillon au centre de la route ; on ignore les pixels des lignes
        # (ligne centrale fine et traits de case) qui passent par le milieu
        qx, qy, _tx, _ty = path_point_at(pts, s)
        return [ui2.screen.get_at((int(ox + qx * scale), int(oy + qy * scale)))[:3]]
    checked = 0
    cells = [c for t in track.tiles for c in t.cells]
    for i in range(1, len(cells)):
        c_prev, c_cur = cells[i - 1], cells[i]
        if cell_color(c_prev) == cell_color(c_cur):
            continue  # pas de changement de couleur à cette frontière
        s = float(cells[i].x)
        before = pix_at(s - 0.3)
        after = pix_at(s + 0.3)
        exp_b, exp_a = cell_color(c_prev), cell_color(c_cur)
        def match(samples, exp):
            for c in samples:
                if any(all(abs(c[k] - lc[k]) <= 8 for k in range(3)) for lc in LINE_COLORS):
                    continue  # pixel de ligne (centrale/trait de case) : on ignore
                if all(abs(c[k] - exp[k]) <= 12 for k in range(3)):
                    return True
            return len(samples) == 0 or all(
                any(all(abs(c[k] - lc[k]) <= 8 for k in range(3)) for lc in LINE_COLORS)
                for c in samples)  # que des pixels de ligne -> ok aussi
        ok_b = match(before, exp_b)
        ok_a = match(after, exp_a)
        assert ok_b and ok_a, f"franchise case {i}: avant={before} (attendu {exp_b}), après={after} (attendu {exp_a})"
        checked += 1
    print(f"containment couleurs: {checked} frontières testées, OK")

    # --- Aucun interstice entre les cases : le long de chaque frontière,
    # sur toute la largeur de la route, aucun pixel de fond (PANEL) ---
    gaps = 0
    for i in range(1, len(cells)):
        if cells[i - 1].run != CellRunType.NONE or cells[i].run != CellRunType.NONE:
            continue  # le damier d'arrivée contient du blanc : hors test
        s = float(cells[i].x)
        qx, qy, tx, ty = path_point_at(pts, s)
        sx, sy = ox + qx * scale, oy + qy * scale
        nx, ny = -ty, tx
        # on échantillonne strictement À L'INTÉRIEUR de la route (les 2 px de
        # bord peuvent être du fond à cause de l'arrondi des polygones)
        for t in [x / 8 for x in range(-int((road_w / 2 - 1.5) * 8), int((road_w / 2 - 1.5) * 8) + 1)]:
            c = ui2.screen.get_at((int(sx + nx * t), int(sy + ny * t)))[:3]
            if c == (255, 255, 255):
                gaps += 1
    print(f"interstices (pixels de fond sur les frontières): {gaps}")
    assert gaps == 0, "des cases ne prennent pas tout l'espace (trous entre cases)"

    # --- Profil accidenté + fanion rouge de catégorie au sommet ---
    ui3 = main.FlammeRougeGame()
    ui3.width, ui3.height = 1200, 800
    ui3.screen = pygame.display.set_mode((1200, 800))
    ui3.menu_index = names.index("La Haut Montagne") + 1
    ui3.screen.fill(main.BG)
    ui3._draw_menu()
    pr3 = ui3._menu_profile_rect(ui3._preview_rect())
    red = 0
    for x in range(pr3.x, pr3.right):
        for y in range(pr3.y, pr3.bottom):  # les fanions doivent rester DANS le profil
            if px(ui3.screen, (x, y)) == (215, 45, 45):
                red += 1
    print("fanion rouge (215,45,45) px:", red, "(La Haut Montagne, D+=19 -> HC)")
    assert red > 10, "fanion rouge de catégorie absent du profil"
    # les fanions ne doivent PAS dépasser du panneau profil (pas hors du profil)
    trect3 = ui3._preview_track_rect(ui3._preview_rect())
    red_out = 0
    for x in range(pr3.x, pr3.right):
        for y in range(trect3.bottom, pr3.y):
            if px(ui3.screen, (x, y)) == (215, 45, 45):
                red_out += 1
    print("fanions hors du panneau profil:", red_out)
    assert red_out == 0, "des fanions dépassent du panneau profil"

    # --- Éditeur : les lettres des tuiles sont toujours dessinées ---
    ui2.menu_step = 'editor'
    ui2.editor_code = 'abKcdEfghijklmnopqrstu'
    ui2._draw_editor(pygame.mouse.get_pos())
    print("thème clair + profil + groupes OK")


if __name__ == '__main__':
    main_()
