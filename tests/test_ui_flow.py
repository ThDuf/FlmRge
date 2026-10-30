"""Test headless du flux UI de main.py (pilotage clavier simulé).

Vérifie le cycle complet d'un tour via la logique de FlammeRougeGame :
énergie -> mouvement -> aspiration (pas-à-pas APPLIQUÉ sur le plateau)
-> fatigue -> nouveau tour, avec contrôle de cohérence à chaque étape.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main  # noqa: E402  (importe pygame en mode dummy)
from game.game import Phase  # noqa: E402


def assert_board_consistent(testcase, ui):
    track = ui.game.track
    seen = set()
    for x, y, runner in track.get_all_runners():
        testcase.assertNotIn(runner.id, seen, f"{runner.id} dupliqué sur la piste")
        seen.add(runner.id)
        testcase.assertEqual((runner.x, runner.y), (x, y))


def sum_positions(ui):
    return sum(r.x for _x, _y, r in ui.game.track.get_all_runners())


class TestUiFlow(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame()

    def _play_energy_phase(self):
        """Joue la première carte de chaque coureur, comme les clics souris."""
        game = self.ui.game
        for player in game.players:
            for runner in player.get_runners():
                card = runner.hand[0]
                self.assertTrue(game.play_card(player, runner, card))
        self.assertTrue(game.all_players_ready())

    def test_full_turn_with_aspiration_steps(self):
        ui = self.ui
        game = ui.game

        # Phase d'énergie
        self.assertEqual(game.current_phase, Phase.ENERGY)
        self._play_energy_phase()
        game.resolve_movement_phase()
        assert_board_consistent(self, ui)

        # Phase d'aspiration : le moteur CALCULE, l'UI applique pas-à-pas
        steps = game.resolve_aspiration_phase()
        if steps:
            ui.aspiration_movements = steps
            ui._initialize_aspiration()
            self.assertTrue(ui.showing_aspiration)
            self.assertEqual(ui.aspiration_total, len(steps))
            expected_total_moves = sum(len(s) for s in steps)

            before = sum_positions(ui)
            done = False
            guard = 0
            while not done:
                done = ui._next_aspiration_step()
                guard += 1
                self.assertLess(guard, 100, "pas-à-pas d'aspiration sans fin")
                assert_board_consistent(self, ui)
            # Chaque mouvement d'étape avance un coureur d'exactement 1 case
            self.assertEqual(sum_positions(ui), before + expected_total_moves)
            # Tout est appliqué : plus aucune aspiration possible
            self.assertEqual(game.track.compute_slipstream_steps(), [])
            ui._finish_aspiration_phase()
        else:
            ui._finish_aspiration_phase()

        # Fatigue + victoire éventuelle + nouveau tour direct
        self.assertFalse(ui.showing_aspiration)
        assert_board_consistent(self, ui)
        if not game.game_over:
            self.assertEqual(game.current_phase, Phase.ENERGY)
            self.assertEqual(game.turn_count, 2)
            for player in game.players:
                for runner in player.get_runners():
                    self.assertEqual(len(runner.hand), 4)
                    self.assertIsNone(runner.played_card)

    def test_finish_aspiration_resets_display_state(self):
        ui = self.ui
        ui.showing_aspiration = True
        ui.aspiration_step = 2
        ui.aspiration_total = 3
        ui.aspiration_movements = [(None, 1, 0, 2, 0)]
        ui._finish_aspiration_phase()
        self.assertFalse(ui.showing_aspiration)
        self.assertEqual(ui.aspiration_step, 0)
        self.assertEqual(ui.aspiration_movements, [])
        # Phase TERMINALE transitoire : nouveau tour démarré directement
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        self.assertEqual(ui.game.turn_count, 2)


class TestHandLayout(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame()

    def test_panels_fit_window(self):
        layout = self.ui._hand_layout()
        self.assertEqual(len(layout), len(self.ui.game.players))
        for player, panel, rows in layout:
            self.assertLessEqual(panel.right, self.ui.width, "panneau hors écran à droite")
            self.assertLessEqual(panel.bottom, self.ui.height, "panneau hors écran en bas")
            self.assertGreaterEqual(panel.x, 0)
            for runner, label, rects in rows:
                self.assertEqual(len(rects), len(runner.hand))
                for rect in rects:
                    self.assertTrue(panel.contains(rect), "carte hors du panneau")

    def test_panels_do_not_overlap(self):
        layout = self.ui._hand_layout()
        for i in range(len(layout) - 1):
            self.assertFalse(layout[i][1].colliderect(layout[i + 1][1]),
                             "les panneaux de joueurs se chevauchent")

    def test_resize_updates_layout(self):
        self.ui.width, self.ui.height = 1600, 1000
        layout = self.ui._hand_layout()
        for player, panel, rows in layout:
            self.assertLessEqual(panel.right, 1600)
            self.assertLessEqual(panel.bottom, 1000)
        # piste repositionnée sans sortir de l'écran
        self.assertGreaterEqual(self.ui._track_top(), 120)

    def test_click_zone_matches_displayed_cards(self):
        """Le clic sur une carte affichée joue bien CETTE carte."""
        ui = self.ui
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        layout = ui._hand_layout()
        player, panel, rows = layout[0]
        runner, label, rects = rows[0]
        card = runner.hand[0]
        ui._handle_click((rects[0].centerx, rects[0].centery))
        self.assertEqual(ui.game.cards_played_per_runner[runner.id], 1)
        self.assertIs(runner.played_card, card)
        # un second clic sur le même coureur ne fait rien
        ui._handle_click((rects[1].centerx, rects[1].centery))
        self.assertEqual(ui.game.cards_played_per_runner[runner.id], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
