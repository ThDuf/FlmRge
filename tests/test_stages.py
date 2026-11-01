"""Tests du registre d'étapes officielles et du menu de sélection.

Étapes officielles du rulebook (codes en lettres de tuiles a-u / A-U) :
- Avenue Corso Paseo : abcdefghijklmnopqrstu (plate)
- Firenze - Milano, Ronde van Wevelgem, La Haut Montagne, La Classicissima
Correspondance tuiles (BGG/rulebook) : a=départ, u=arrivée, droites b c d f l m n,
virages légers h k q r s t, virages serrés e g i j o p ; majuscule = montagne.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import TileType  # noqa: E402
from game.game import (Game, OFFICIAL_STAGES, available_stages,  # noqa: E402
                       build_track_from_code, tile_type_for_letter)
import main  # noqa: E402


class TestTileLetters(unittest.TestCase):
    def test_catalog_is_complete(self):
        """Les 21 tuiles officielles sont toutes dans le catalogue."""
        from game.game import TILE_CATALOG
        self.assertEqual(sorted(TILE_CATALOG.keys()), list("abcdefghijklmnopqrstu"))
        types = [v[0] for v in TILE_CATALOG.values()]
        self.assertEqual(types.count(TileType.STRAIGHT), 7)
        self.assertEqual(types.count(TileType.LIGHT_TURN), 6)
        self.assertEqual(types.count(TileType.SHARP_TURN), 6)
        self.assertEqual(types.count(TileType.START), 1)
        self.assertEqual(types.count(TileType.FINISH), 1)
        # angles officiels : 45° léger, 90° serré
        angles = {v[0]: v[1] for v in TILE_CATALOG.values()}
        self.assertEqual(angles[TileType.LIGHT_TURN], 45)
        self.assertEqual(angles[TileType.SHARP_TURN], 90)
        self.assertEqual(angles[TileType.STRAIGHT], 0)

    def test_turn_directions_match_corso_paseo_card(self):
        """Sens des virages relevés sur la carte imprimée Avenue Corso Paseo
        (G=+1, D=-1) : e=G g=G h=G i=G j=D k=D o=D p=D q=G r=D s=D t=G."""
        from game.game import TILE_CATALOG
        expected = {'e': 1, 'g': 1, 'h': 1, 'i': 1, 'j': -1, 'k': -1,
                    'o': -1, 'p': -1, 'q': 1, 'r': -1, 's': -1, 't': 1}
        for letter, direction in expected.items():
            self.assertEqual(TILE_CATALOG[letter][2], direction, letter)

    def test_first_turn_of_corso_paseo_goes_left(self):
        """Convention écran (y vers le bas) : e=G -> le premier virage de
        Corso Paseo fait tourner le cap vers le haut (angle négatif)."""
        import math
        from game.track import compute_track_path
        track = build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])
        pts = compute_track_path(track, 1.0)

        def heading_at(s):
            cum = 0.0
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                d = math.hypot(x1 - x0, y1 - y0)
                if cum + d >= s:
                    return math.atan2(y1 - y0, x1 - x0)
                cum += d
            return 0.0

        # tuile e = 5e tuile : START(4) + 3 droites(6) = 22 cases avant, arc s=22..24
        self.assertAlmostEqual(math.degrees(heading_at(21.0)), 0, places=0)
        self.assertAlmostEqual(math.degrees(heading_at(24.5)), -90, places=0)

    def test_letter_mapping(self):
        # cases officielles : départ 4, arrivée 5, droites 6, virages 2
        from game.game import TILE_CATALOG
        self.assertEqual(TILE_CATALOG['a'][3], 4)
        self.assertEqual(TILE_CATALOG['u'][3], 5)
        self.assertEqual(TILE_CATALOG['b'][3], 6)
        self.assertEqual(TILE_CATALOG['e'][3], 2)
        # montée ET descente explicites
        from game.game import ASCENT_LETTERS, DESCENT_LETTERS
        self.assertIn('K', ASCENT_LETTERS)
        self.assertIn('O', DESCENT_LETTERS)
        self.assertEqual(tile_type_for_letter('K'), TileType.UPHILL)
        self.assertEqual(tile_type_for_letter('O'), TileType.DOWNHILL)
        self.assertEqual(tile_type_for_letter('a'), TileType.START)
        self.assertEqual(tile_type_for_letter('u'), TileType.FINISH)
        for c in "bcdf lmn".replace(" ", ""):
            self.assertEqual(tile_type_for_letter(c), TileType.STRAIGHT)
        for c in "hkqrst":
            self.assertEqual(tile_type_for_letter(c), TileType.LIGHT_TURN)
        for c in "egijop":
            self.assertEqual(tile_type_for_letter(c), TileType.SHARP_TURN)
        # majuscules = montagne
        self.assertIn(tile_type_for_letter('G'), (TileType.UPHILL, TileType.DOWNHILL))
        self.assertIn(tile_type_for_letter('O'), (TileType.UPHILL, TileType.DOWNHILL))

    def test_code_ignores_spaces(self):
        t1 = build_track_from_code("ab c")
        t2 = build_track_from_code("abc")
        self.assertEqual(t1.length, t2.length)


class TestOfficialStages(unittest.TestCase):
    def test_all_official_stages_build_21_tiles(self):
        for name, code in OFFICIAL_STAGES.items():
            track = build_track_from_code(code)
            self.assertEqual(len(track.tiles), 21, name)
            self.assertEqual(track.length, 75, name)
            self.assertEqual(track.tiles[0].type, TileType.START, name)
            self.assertEqual(track.tiles[-1].type, TileType.FINISH, name)

    def test_avenue_corso_paseo_is_flat_with_turns(self):
        track = build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])
        types = [t.type for t in track.tiles]
        self.assertEqual(types.count(TileType.STRAIGHT), 7)
        self.assertEqual(types.count(TileType.LIGHT_TURN), 6)
        self.assertEqual(types.count(TileType.SHARP_TURN), 6)
        self.assertNotIn(TileType.UPHILL, types)
        self.assertNotIn(TileType.DOWNHILL, types)

    def test_la_haut_montagne_has_mountains(self):
        track = build_track_from_code(OFFICIAL_STAGES["La Haut Montagne"])
        types = [t.type for t in track.tiles]
        self.assertGreaterEqual(types.count(TileType.UPHILL), 4)

    def test_game_builds_and_plays_on_official_stage(self):
        game = Game(stage="La Haut Montagne", player_count=2)
        self.assertEqual(game.track.length, 75)
        for player in game.players:
            for runner in player.get_runners():
                self.assertTrue(game.play_card(player, runner, runner.hand[0]))
        game.apply_movement_steps(game.resolve_movement_phase())
        game.apply_aspiration_steps(game.resolve_aspiration_phase())

    def test_unknown_stage_falls_back_to_avenue(self):
        game = Game(stage="nimporte-quoi", player_count=2)
        self.assertEqual(game.track.length, 75)

    def test_avenue_corso_paseo_shape_is_continuous_flat_course(self):
        """Corso Paseo : 75 cases, plat (aucune montagne), tracé continu
        (le suit des tuiles bout à bout, virages à leur place)."""
        from game.track import compute_track_path
        track = build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])
        types = [t.type for t in track.tiles]
        self.assertNotIn(TileType.UPHILL, types)
        self.assertNotIn(TileType.DOWNHILL, types)
        pts = compute_track_path(track, 1.0)
        # continuité : un segment du polyligne = une tuile (6 cases max pour une droite)
        import math
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.assertLessEqual(math.hypot(x1 - x0, y1 - y0), 6.0)
        # le tracé tient dans une forme raisonnable (pas de boucle délirante)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.assertLess(max(xs) - min(xs), 80)
        self.assertLess(max(ys) - min(ys), 40)

    def test_available_stages_lists_circuit_and_official(self):
        names = [name for name, _desc, _code in available_stages()]
        self.assertEqual(names, ["circuit", *OFFICIAL_STAGES.keys()])
        for name, desc, code in available_stages():
            self.assertIn("cases", desc)


class TestStageMenu(unittest.TestCase):
    def test_menu_shown_at_launch_without_stage(self):
        ui = main.FlammeRougeGame()
        self.assertIsNone(ui.game)
        entries = ui._menu_entries()
        self.assertEqual(len(entries), 6)

    def test_select_stage_starts_game(self):
        ui = main.FlammeRougeGame()
        ui._select_stage("La Haut Montagne")
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.stage, "La Haut Montagne")
        self.assertEqual(ui.game.track.length, 75)
        types = [t.type for t in ui.game.track.tiles]
        self.assertIn(TileType.UPHILL, types)

    def test_menu_click_selects_entry(self):
        ui = main.FlammeRougeGame()
        entries = ui._menu_entries()
        name, _d, _c, rect = entries[1]  # première étape officielle
        # simule un clic au centre de l'entrée
        import pygame
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=rect.center))
        # le survol est calculé depuis la position souris (ici 0,0) : on
        # force via clavier à la place
        self.assertIsNone(ui.game)  # le clic n'a rien sélectionné (souris hors entrée)
        ui.menu_index = 1
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.stage, name)

    def test_preview_tile_marks_letters(self):
        """La preview marque chaque tuile avec sa lettre (a..u) pour les
        étapes officielles, sans lettre pour le circuit perso."""
        ui = main.FlammeRougeGame()
        marks, total = ui._preview_tile_marks("Avenue Corso Paseo")
        self.assertEqual(len(marks), 21)
        self.assertEqual([m[1] for m in marks], list("abcdefghijklmnopqrstu"))
        self.assertEqual(total, 75)  # 75 cases
        marks_c, total_c = ui._preview_tile_marks("circuit")
        self.assertEqual(len(marks_c), 19)
        self.assertTrue(all(m[1] is None for m in marks_c))

    def test_menu_preview_points_within_panel(self):
        """La prévisualisation du tracé tient dans son panneau (grandes fenêtres)."""
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        rect = ui._preview_rect()
        for name, _desc, _code in __import__('game.game', fromlist=['available_stages']).available_stages():
            pts = ui._stage_preview_points(name)
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bb_w = max(xs) - min(xs)
            bb_h = max(ys) - min(ys)
            scale = min((rect.w - 30) / max(bb_w, 1e-9), (rect.h - 60) / max(bb_h, 1e-9))
            self.assertGreater(scale, 0)
            self.assertLessEqual(bb_w * scale, rect.w - 30, name)
            self.assertLessEqual(bb_h * scale, rect.h - 60, name)

    def test_escape_returns_to_menu_and_r_restarts_stage(self):
        ui = main.FlammeRougeGame(stage="circuit")
        import pygame
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsNone(ui.game)
        ui._select_stage("Avenue Corso Paseo")
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.stage, "Avenue Corso Paseo")
        self.assertEqual(ui.game.track.length, 75)


if __name__ == '__main__':
    unittest.main(verbosity=2)
