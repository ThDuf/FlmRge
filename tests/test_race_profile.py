"""Tests du profil de course sur l'écran de course : panneau en haut à droite
du cadre du parcours, avec un marqueur par groupe (pastille couleur d'équipe
sur la ligne de profil + libellé) et le badge météo si l'extension est active.

Lancé :  python -m unittest tests.test_race_profile -v
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame  # noqa: E402
import main  # noqa: E402
from game.game import Game  # noqa: E402
from game.track import WeatherType  # noqa: E402


class TestRaceProfile(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="Avenue Corso Paseo")
        self.ui.game.auto_place_riders()

    def _render(self, ui, size=(1280, 800)):
        ui.width, ui.height = size
        ui.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        ui.screen.fill((200, 200, 210))
        ui._draw_header()
        ui._draw_phase_band()
        ui._draw_track()
        ui._draw_runners()
        ui._draw_ui()

    def test_rect_below_track_above_bar(self):
        """Le profil de course est SOUS le parcours (sous le cadre), au-dessus
        de la barre du bas, plein largeur."""
        ui = self.ui
        ui.width, ui.height = 1280, 920
        ui.screen = pygame.display.set_mode((1280, 920), pygame.RESIZABLE)
        frame = ui._frame_rect()
        bar = ui._bar_rect()
        r = ui._race_profile_rect()
        self.assertGreaterEqual(r.x, frame.x)
        self.assertLessEqual(r.right, frame.right)
        self.assertGreaterEqual(r.y, frame.bottom)      # sous le parcours
        self.assertLessEqual(r.bottom, bar.y + 1)       # au-dessus de la barre du bas
        self.assertGreater(r.w, frame.w * 0.8)          # plein largeur

    def test_markers_match_groups(self):
        ui = self.ui
        # éclate les coureurs en 3 groupes pour avoir Tête / Peloton / Lanterne
        track = ui.game.track
        for x, lane, r in list(track.get_all_runners()):
            track.get_cell(x, lane).remove_runner(lane)
        track.get_cell(2, 0).set_runner(ui.game.players[0].sprinter, 0)
        track.get_cell(10, 0).set_runner(ui.game.players[0].roller, 0)
        track.get_cell(11, 0).set_runner(ui.game.players[1].sprinter, 0)
        track.get_cell(20, 0).set_runner(ui.game.players[1].roller, 0)
        groups = ui._group_names()
        self.assertGreaterEqual(len(groups), 3)
        markers = ui._race_profile_markers()
        self.assertEqual(len(markers), len(groups))
        for (label, group, lead_x), (mx, color, name) in zip(groups, markers):
            self.assertEqual(mx, lead_x)
            self.assertEqual(name, label)  # nom COMPLET du groupe sur le profil
            self.assertIsInstance(color, tuple)
        labels = [m[2] for m in markers]
        self.assertIn("Tête de course", labels)
        self.assertIn("Lanterne rouge", labels)

    def test_profile_renders_with_group_markers(self):
        """Le rendu de l'écran de course dessine le profil ET les pastilles
        couleur d'équipe des groupes dessus."""
        ui = self.ui
        self._render(ui, (1280, 800))
        r = ui._race_profile_rect()
        team_colors = set(main.PLAYER_COLORS.values())
        found = set()
        for x in range(r.x, r.right):
            for y in range(r.y, r.bottom):
                p = ui.screen.get_at((x, y))[:3]
                if p in team_colors:
                    found.add(p)
        self.assertTrue(found, "aucune pastille d'équipe trouvée sur le profil")

    def test_profile_renders_at_several_sizes(self):
        for size in [(900, 700), (1280, 920), (1600, 1000)]:
            self._render(self.ui, size)  # pas d'erreur
            r = self.ui._race_profile_rect()
            frame = self.ui._frame_rect()
            bar = self.ui._bar_rect()
            self.assertLessEqual(r.right, frame.right)
            self.assertGreaterEqual(r.y, frame.bottom)   # sous le parcours
            self.assertLessEqual(r.bottom, bar.y + 1)

    def test_weather_badge_on_race_profile_when_meteo(self):
        """Extension Météo active : le badge animé est aussi sur le profil de
        course (météo réelle de la partie, pas l'aperçu seedé)."""
        ui = main.FlammeRougeGame()
        ui.ext_meteo = True
        ui._select_stage("Avenue Corso Paseo")
        ui.game.auto_place_riders()
        w = ui._game_weather()
        self.assertTrue(w)  # au moins un type ([NONE]=soleil si aucun événement)
        self.assertTrue(all(isinstance(x, WeatherType) for x in w))
        # avec extension inactive -> pas de badge
        ui2 = main.FlammeRougeGame(stage="Avenue Corso Paseo")
        self.assertEqual(ui2._game_weather(), [])
        # rendu avec badge
        self._render(ui, (1280, 800))
        r = ui._race_profile_rect()
        badge = pygame.Rect(r.right - 64, r.y + 4, 24, 24)
        hits = sum(1 for x in range(badge.x, badge.right) for y in range(badge.y, badge.bottom)
                   if ui.screen.get_at((x, y))[:3] not in ((200, 200, 210), (255, 255, 255)))
        self.assertGreater(hits, 0, "badge météo absent du profil de course")

    def test_profile_updates_with_movement(self):
        """Les marqueurs suivent les groupes quand les coureurs avancent."""
        ui = self.ui
        before = [m[0] for m in ui._race_profile_markers()]
        ui._play_random_turn()
        for a in ui.animations:
            a["t0"] = -(10 ** 9)
        ui._prune_animations()
        after = [m[0] for m in ui._race_profile_markers()]
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
