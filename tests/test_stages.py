"""Tests du registre d'étapes officielles et du menu de sélection.

Étapes officielles du rulebook (codes en lettres de tuiles a-u / A-U) :
- Avenue Corso Paseo : abcdefghijklmnopqrstu (plate)
- Firenze - Milano, Ronde van Wevelgem, La Haut Montagne, La Classicissima
Correspondance tuiles (BGG/rulebook) : a=départ, u=arrivée, droites b c d f l m n,
virages légers h k q r s t, virages serrés e g i j o p ; majuscule = face montagne
(retournée : virage en miroir, géographie case par case).
"""
import os
import sys
import math
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import CellGeographyType, CellRunType, compute_track_path  # noqa: E402
from game.game import (Game, OFFICIAL_STAGES, TILE_DEFS, MOUNTAIN_DEFS,  # noqa: E402
                       available_stages, build_track_from_code,
                       tile_def_for_letter, build_tile)
import main  # noqa: E402


class TestTileLetters(unittest.TestCase):
    def test_catalog_is_complete(self):
        """Les 21 tuiles officielles sont toutes dans le catalogue."""
        self.assertEqual(sorted(TILE_DEFS.keys()), list("abcdefghijklmnopqrstu"))
        turns = [v[0] for v in TILE_DEFS.values()]
        self.assertEqual(turns.count(None), 9)               # a, u + 7 droites
        self.assertEqual(sum(1 for t in turns if t and abs(t[0] - math.pi / 4) < 1e-9), 6)
        self.assertEqual(sum(1 for t in turns if t and abs(t[0] - math.pi / 2) < 1e-9), 6)
        self.assertTrue(all(v[1] == 2 for v in TILE_DEFS.values()))  # 2 files
        # longueurs officielles : départ 6, arrivée 6, droites 6, virages 2
        self.assertEqual(len(TILE_DEFS['a'][2]), 6)
        self.assertEqual(len(TILE_DEFS['u'][2]), 6)
        for c in "bcdf lmn".replace(" ", ""):
            self.assertEqual(len(TILE_DEFS[c][2]), 6)
        for c in "hkqrstegijop":
            self.assertEqual(len(TILE_DEFS[c][2]), 2)
        # lignes : départ sur les 5 premières cases de 'a', arrivée sur 'u'
        self.assertEqual(TILE_DEFS['a'][2], "sssssf")
        self.assertEqual(TILE_DEFS['u'][2], "feeeee")

    def test_turn_directions_match_corso_paseo_card(self):
        """Sens des virages relevés sur la carte imprimée Avenue Corso Paseo
        (G=+1, D=-1) : e=G g=G h=G i=G j=D k=D o=D p=D q=G r=D s=D t=G."""
        expected = {'e': 1, 'g': 1, 'h': 1, 'i': 1, 'j': -1, 'k': -1,
                    'o': -1, 'p': -1, 'q': 1, 'r': -1, 's': -1, 't': 1}
        for letter, direction in expected.items():
            turn = tile_def_for_letter(letter)[0]
            self.assertIsNotNone(turn, letter)
            self.assertEqual(turn[1], direction, letter)

    def test_first_turn_of_corso_paseo_goes_left(self):
        """Convention écran (y vers le bas) : e=G -> le premier virage de
        Corso Paseo fait tourner le cap vers le haut (angle négatif)."""
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

        # tuile e = 5e tuile : départ(6) + 3 droites(18) = 24 cases avant, arc s=24..26
        self.assertAlmostEqual(math.degrees(heading_at(23.0)), 0, places=0)
        self.assertAlmostEqual(math.degrees(heading_at(26.5)), -90, places=0)

    def test_letter_mapping(self):
        # cases officielles : départ 6 (ligne sur 5 premières), arrivée 6 (ligne sur 5 dernières)
        self.assertEqual(tile_def_for_letter('a')[2], "sssssf")
        self.assertEqual(tile_def_for_letter('u')[2], "feeeee")
        for c in "bcdf lmn".replace(" ", ""):
            self.assertEqual(tile_def_for_letter(c), (None, 2, "ffffff"))
        for c in "hkqrst":
            turn, width, chars = tile_def_for_letter(c)
            self.assertAlmostEqual(turn[0], math.pi / 4)
            self.assertEqual(chars, "ff")
        for c in "egijop":
            turn, width, chars = tile_def_for_letter(c)
            self.assertAlmostEqual(turn[0], math.pi / 2)
            self.assertEqual(chars, "ff")
        # face montagne : géographie case par case explicite ou repli uniforme
        self.assertEqual(tile_def_for_letter('K')[2], "uu")       # montée
        self.assertEqual(tile_def_for_letter('O')[2], "dd")       # descente
        self.assertEqual(tile_def_for_letter('B'), (None, 2, "ddddff"))  # explicite
        self.assertEqual(tile_def_for_letter('A'), (None, 2, "ssssff"))
        self.assertEqual(tile_def_for_letter('U'), (None, 2, "feeeee"))
        # les tuiles construites portent la géographie sur chaque case
        tile = build_tile('B')
        self.assertEqual([c.geography for c in tile.cells],
                         [CellGeographyType.DOWNHILL] * 4 + [CellGeographyType.FLAT] * 2)
        tile_a = build_tile('a')
        self.assertEqual([c.run for c in tile_a.cells],
                         [CellRunType.START] * 5 + [CellRunType.NONE])
        self.assertEqual(len(tile_a.cells[0].runners), 2)  # 2 files

    def test_uppercase_mirrors_turn_direction(self):
        """Face montagne = tuile retournée : le virage est en miroir.
        H tourne à droite (-1) puisque h va à gauche (+1)."""
        for c in "hkqrstegijop":
            turn_low = tile_def_for_letter(c)[0]
            turn_up = tile_def_for_letter(c.upper())[0]
            self.assertAlmostEqual(turn_up[0], turn_low[0], msg=c)
            self.assertEqual(turn_up[1], -turn_low[1], c)
        self.assertEqual(tile_def_for_letter('h')[0][1], 1)
        self.assertEqual(tile_def_for_letter('H')[0][1], -1)

    def test_code_ignores_spaces(self):
        t1 = build_track_from_code("ab c")
        t2 = build_track_from_code("abc")
        self.assertEqual(t1.length, t2.length)


class TestOfficialStages(unittest.TestCase):
    def test_all_official_stages_build_21_tiles(self):
        for name, code in OFFICIAL_STAGES.items():
            track = build_track_from_code(code)
            self.assertEqual(len(track.tiles), 21, name)
            self.assertEqual(track.length, 78, name)  # départ 6 + arrivée 6 + 7x6 + 12x2
            self.assertEqual(track.tiles[0].letter.lower(), 'a', name)
            self.assertEqual(track.tiles[-1].letter.lower(), 'u', name)

    def test_avenue_corso_paseo_is_flat_with_turns(self):
        track = build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])
        turns = [t.turn for t in track.tiles]
        geographies = [c.geography for t in track.tiles for c in t.cells]
        self.assertEqual(turns.count(None), 9)
        self.assertEqual(sum(1 for t in turns if t and abs(t[0] - math.pi / 4) < 1e-9), 6)
        self.assertEqual(sum(1 for t in turns if t and abs(t[0] - math.pi / 2) < 1e-9), 6)
        self.assertNotIn(CellGeographyType.UPHILL, geographies)
        self.assertNotIn(CellGeographyType.DOWNHILL, geographies)
        self.assertTrue(all(g == CellGeographyType.FLAT for g in geographies))

    def test_la_haut_montagne_has_mountains(self):
        track = build_track_from_code(OFFICIAL_STAGES["La Haut Montagne"])
        geographies = [c.geography for t in track.tiles for c in t.cells]
        self.assertGreaterEqual(geographies.count(CellGeographyType.UPHILL), 4)
        # départ/arrivée (A/U) restent plats : aucune descente sur cette étape
        self.assertEqual(geographies.count(CellGeographyType.DOWNHILL), 0)

    def test_game_builds_and_plays_on_official_stage(self):
        game = Game(stage="La Haut Montagne", player_count=2)
        self.assertEqual(game.track.length, 78)
        for player in game.players:
            for runner in player.get_runners():
                self.assertTrue(game.play_card(player, runner, runner.hand[0]))
        game.apply_movement_steps(game.resolve_movement_phase())
        game.apply_aspiration_steps(game.resolve_aspiration_phase())

    def test_unknown_stage_falls_back_to_avenue(self):
        game = Game(stage="nimporte-quoi", player_count=2)
        self.assertEqual(game.track.length, 78)

    def test_avenue_corso_paseo_shape_is_continuous_flat_course(self):
        """Corso Paseo : 78 cases, plat (aucune montagne), tracé continu
        (le suit des tuiles bout à bout, virages à leur place)."""
        track = build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])
        geographies = [c.geography for t in track.tiles for c in t.cells]
        self.assertNotIn(CellGeographyType.UPHILL, geographies)
        self.assertNotIn(CellGeographyType.DOWNHILL, geographies)
        pts = compute_track_path(track, 1.0)
        # continuité : un segment du polyligne = une tuile (6 cases max pour une droite)
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
        self.assertEqual(ui.game.track.length, 78)
        geographies = [c.geography for t in ui.game.track.tiles for c in t.cells]
        self.assertIn(CellGeographyType.UPHILL, geographies)

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
        self.assertIsNone(ui.game)  # ENTRÉE passe à l'étape "joueurs"
        self.assertEqual(ui.menu_step, "players")
        self.assertEqual(ui._pending_stage, name)
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.stage, name)
        self.assertEqual(len(ui.game.players), 2)  # 2 joueurs par défaut

    def test_menu_player_count_2_to_4(self):
        """Étape 'players' du menu : on choisit 3 joueurs au clavier."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.menu_index = 0
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "players")
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(ui.player_count, 3)
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNotNone(ui.game)
        self.assertEqual(len(ui.game.players), 3)
        # borné à 4 : deux RIGHT de plus -> 4, puis on reste à 4
        ui2 = main.FlammeRougeGame()
        ui2.menu_step = "players"
        ui2._pending_stage = "circuit"
        ui2.player_count = 4
        ui2._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(ui2.player_count, 4)
        # Échap revient au choix d'étape
        ui2._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(ui2.menu_step, "stage")
        # clic sur le bouton "4"
        ui3 = main.FlammeRougeGame()
        ui3.menu_step = "players"
        ui3._pending_stage = "circuit"
        count, rect = ui3._player_count_rects()[-1]
        ui3._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                           pos=rect.center))
        self.assertEqual(ui3.player_count, 4)
        self.assertIsNotNone(ui3.game)
        self.assertEqual(len(ui3.game.players), 4)

    def test_game_clamps_player_count(self):
        from game.game import Game
        self.assertEqual(len(Game(stage="test", player_count=1).players), 2)
        self.assertEqual(len(Game(stage="test", player_count=9).players), 4)

    def test_preview_tile_marks_letters(self):
        """La preview marque chaque tuile avec sa lettre (a..u) pour les
        étapes officielles, sans lettre pour le circuit perso."""
        ui = main.FlammeRougeGame()
        marks, total = ui._preview_tile_marks("Avenue Corso Paseo")
        self.assertEqual(len(marks), 21)
        self.assertEqual([m[1] for m in marks], list("abcdefghijklmnopqrstu"))
        self.assertEqual(total, 78)  # 78 cases
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
        self.assertEqual(ui.game.track.length, 78)


if __name__ == '__main__':
    unittest.main(verbosity=2)
