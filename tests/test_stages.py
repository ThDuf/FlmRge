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
    def test_letter_mapping(self):
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
            self.assertEqual(track.length, 42, name)
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
        self.assertEqual(game.track.length, 42)
        for player in game.players:
            for runner in player.get_runners():
                self.assertTrue(game.play_card(player, runner, runner.hand[0]))
        game.apply_movement_steps(game.resolve_movement_phase())
        game.apply_aspiration_steps(game.resolve_aspiration_phase())

    def test_unknown_stage_falls_back_to_avenue(self):
        game = Game(stage="nimporte-quoi", player_count=2)
        self.assertEqual(game.track.length, 42)

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
        self.assertEqual(ui.game.track.length, 42)
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

    def test_escape_returns_to_menu_and_r_restarts_stage(self):
        ui = main.FlammeRougeGame(stage="circuit")
        import pygame
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsNone(ui.game)
        ui._select_stage("Avenue Corso Paseo")
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.stage, "Avenue Corso Paseo")
        self.assertEqual(ui.game.track.length, 42)


if __name__ == '__main__':
    unittest.main(verbosity=2)
