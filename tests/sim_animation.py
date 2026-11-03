"""Vérification headless de l'animation fluide : à mi-animation, le coureur
doit être rendu ENTRE sa case de départ et sa case d'arrivée (glissade),
pas téléporté à l'arrivée."""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame  # noqa: E402
import main  # noqa: E402


def main_():
    pygame.display.set_mode((1200, 800))
    ui = main.FlammeRougeGame(stage="Avenue Corso Paseo")
    ui.width, ui.height = 1200, 800
    ui.screen = pygame.display.set_mode((1200, 800))
    game = ui.game
    for p in game.players:
        for r in p.get_runners():
            game.play_card(p, r, r.hand[0])
    ui._start_movement_phase()
    ui._next_movement_step()
    assert ui.animations, "aucune animation poussée"
    a = ui.animations[0]
    print(f"anim: {a['rid']} case {a['from_x']} -> {a['to_x']} (dur {a['dur']}ms)")

    # fige l'animation à mi-parcours
    now = pygame.time.get_ticks()
    a["t0"] = now - a["dur"] // 2

    ui.screen.fill((255, 255, 255))
    frame = ui._frame_rect()
    pygame.draw.rect(ui.screen, (238, 240, 244), frame)
    ui.screen.set_clip(frame)
    ui._draw_track()
    ui._draw_runners()
    ui.screen.set_clip(None)

    geo = ui._track_geometry()

    def screen_pos(x_cell, lane):
        px, py, tx, ty = ui._path_at(geo, (x_cell + 0.5) * geo["cell"])
        nx, ny = -ty, tx
        off = geo["lane_w"] / 2 * (1 if lane == 0 else -1)
        return int(px + nx * off), int(py + ny * off)

    owner = next(p for p in game.players if any(r.id == a["rid"] for r in p.get_runners()))
    color = main.PLAYER_COLORS[owner.color]

    def reddish(c):
        # cercle rouge vif, lettre "S" noire au centre -> rouge assombri :
        # on accepte toute nuance de rouge (foncé à vif)
        return c[0] > 120 and c[1] < 100 and c[2] < 100

    t = 0.5  # on a figé l'anim à mi-durée
    e = 1 - (1 - t) ** 3  # même easing ease-out que _draw_runners
    mid = screen_pos(a["from_x"] + (a["to_x"] - a["from_x"]) * e, a["from_lane"])
    final = screen_pos(a["to_x"], a["to_lane"])
    radius = int(geo["lane_w"] * 0.55)
    samples_mid = [ui.screen.get_at((mid[0] + dx, mid[1] + dy))[:3]
                   for dx, dy in ((radius // 2, 0), (-radius // 2, 0), (0, radius // 2), (0, -radius // 2), (0, 0))]
    cfinal = ui.screen.get_at(final)[:3]
    print("couleur attendue:", color, "| pixels au milieu:", samples_mid, "| pixel à l'arrivée:", cfinal)
    ok_mid = any(reddish(c) for c in samples_mid)
    ok_not_final = not reddish(cfinal)
    print(f"coureur rendu au milieu du trajet: {ok_mid} | PAS téléporté à l'arrivée: {ok_not_final}")
    assert ok_mid and ok_not_final, "interpolation non visible"
    print("animation fluide OK")


if __name__ == '__main__':
    main_()
