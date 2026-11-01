"""Tests de la phase de placement des coureurs au départ.

Règles officielles : chaque joueur place ses deux coureurs un par un,
derrière la ligne de départ, sur n'importe quelle file libre (file de droite
prioritaire si la case est vide). Option : placement au hasard.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game, Phase  # noqa: E402
import main  # noqa: E402


class TestPlacementPhase(unittest.TestCase):
    def test_default_game_auto_places(self):
        """Par défaut (tests/sims), placement auto : phase ÉNERGIE direct."""
        game = Game(stage="test", player_count=2)
        self.assertEqual(game.current_phase, Phase.ENERGY)
        self.assertEqual(len(game.track.get_all_runners()), 4)

    def test_manual_placement_starts_in_placement_phase(self):
        game = Game(stage="test", player_count=3, auto_place=False)
        self.assertEqual(game.current_phase, Phase.PLACEMENT)
        self.assertEqual(len(game.placement_queue), 6)  # 3 joueurs x 2 coureurs
        self.assertEqual(game.track.get_all_runners(), [])  # personne sur la piste
        player, runner = game.current_placement()
        self.assertIs(player, game.players[0])
        self.assertIs(runner, player.sprinter)

    def test_can_place_only_behind_start_line_on_free_lane(self):
        game = Game(stage="test", player_count=2, auto_place=False)
        limit = game.track.start_line_x()
        self.assertTrue(game.can_place_at(limit - 1, 0))
        self.assertFalse(game.can_place_at(limit, 0))      # sur/après la ligne
        self.assertFalse(game.can_place_at(limit + 3, 0))
        self.assertTrue(game.place_runner_at(limit - 1, 0))
        self.assertFalse(game.can_place_at(limit - 1, 0))  # file A prise
        self.assertTrue(game.can_place_at(limit - 1, 1))   # file B encore libre
        self.assertFalse(game.place_runner_at(limit, 1))   # interdit

    def test_placement_advances_and_starts_race_when_done(self):
        game = Game(stage="test", player_count=2, auto_place=False)
        limit = game.track.start_line_x()
        n = len(game.placement_queue)
        for i in range(n):
            self.assertIsNotNone(game.current_placement())
            self.assertTrue(game.place_runner_at(limit - 1 - i // 2, i % 2))
        self.assertEqual(game.current_phase, Phase.ENERGY)  # 1er tour lancé
        self.assertEqual(game.turn_count, 1)
        self.assertEqual(len(game.track.get_all_runners()), n)
        for x, _lane, r in game.track.get_all_runners():
            self.assertLess(x, limit)

    def test_auto_place_riders_random_option(self):
        """Le placement aléatoire respecte la règle : au plus proche de la
        ligne (8 coureurs -> cases 1..4 remplies, case 0 vide)."""
        game = Game(stage="test", player_count=4, auto_place=False)
        game.auto_place_riders()
        self.assertEqual(game.current_phase, Phase.ENERGY)
        limit = game.track.start_line_x()
        runners = game.track.get_all_runners()
        self.assertEqual(len(runners), 8)
        for x, _lane, _r in runners:
            self.assertLess(x, limit)
        occupied_x = sorted({x for x, _l, _r in runners})
        self.assertEqual(occupied_x, [1, 2, 3, 4])  # case 0 (la plus loin) vide


class TestPlacementUI(unittest.TestCase):
    def test_ui_starts_in_placement_phase(self):
        ui = main.FlammeRougeGame()  # menu -> sélection d'étape = placement manuel
        ui._select_stage("Avenue Corso Paseo")
        self.assertEqual(ui.game.current_phase, Phase.PLACEMENT)
        label, desc, _color = ui._phase_info()
        self.assertIn("PLACEMENT", label)
        self.assertIn("hasard", desc)
        btn = ui._button_info()
        self.assertIsNotNone(btn)
        self.assertIn("aléatoire", btn[0].lower())

    def test_ui_random_button_places_everyone(self):
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")
        ui._advance_step()  # clic sur "Placement aléatoire"
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        self.assertEqual(len(ui.game.track.get_all_runners()), 4)

    def test_ui_click_places_runner(self):
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")
        limit = ui.game.track.start_line_x()
        px, py, tx, ty = ui._cell_anchor(limit - 1)
        nx, ny = -ty, tx
        geo = ui._track_geometry()
        pos = (px + nx * geo["half"] * 0.5, py + ny * geo["half"] * 0.5)  # file A
        ui._placement_click(pos)
        self.assertEqual(len(ui.game.track.get_all_runners()), 1)
        self.assertIsNotNone(ui.game.current_placement())


if __name__ == '__main__':
    unittest.main(verbosity=2)
