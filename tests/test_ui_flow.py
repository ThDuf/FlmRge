"""Test headless du flux UI de main.py (pilotage clavier simulé).

Vérifie le cycle complet d'un tour via la logique de FlammeRougeGame :
énergie -> mouvement -> aspiration (pas-à-pas visuel) -> phase terminale,
avec contrôle de cohérence du plateau à chaque étape.
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

        # Phase d'aspiration : le moteur applique, l'UI ne fait qu'afficher
        movements = game.resolve_aspiration_phase()
        if movements:
            ui.aspiration_movements = movements
            ui._initialize_aspiration()
            self.assertTrue(ui.showing_aspiration)
            self.assertEqual(ui.aspiration_total, len(movements))
            # On déroule le pas-à-pas : le plateau ne doit PAS changer
            snapshot = {(r.id, r.x, r.y) for _x, _y, r in game.track.get_all_runners()}
            steps = 0
            while not ui._next_aspiration_step():
                steps += 1
                self.assertLess(steps, 100, "pas-à-pas d'aspiration sans fin")
                now = {(r.id, r.x, r.y) for _x, _y, r in game.track.get_all_runners()}
                self.assertEqual(now, snapshot, "le pas-à-pas visuel a modifié le plateau !")
            assert_board_consistent(self, ui)
            ui._finish_aspiration_phase()
        else:
            ui._finish_aspiration_phase()

        # Après l'aspiration : fatigue + victoire éventuelle + nouveau tour direct
        # (la phase TERMINALE est transitoire : _finish_aspiration_phase
        #  enchaîne immédiatement sur start_turn si personne n'a gagné)
        self.assertFalse(ui.showing_aspiration)
        assert_board_consistent(self, ui)
        if not game.game_over:
            self.assertEqual(game.current_phase, Phase.ENERGY)
            self.assertEqual(game.turn_count, 2)
            for player in game.players:
                for runner in player.get_runners():
                    self.assertEqual(len(runner.hand), 4)
        assert_board_consistent(self, ui)

    def test_finish_aspiration_resets_display_state(self):
        ui = self.ui
        ui.showing_aspiration = True
        ui.aspiration_step = 2
        ui.aspiration_total = 3
        ui.aspiration_movements = [(None, 1, 2)]
        ui._finish_aspiration_phase()
        self.assertFalse(ui.showing_aspiration)
        self.assertEqual(ui.aspiration_step, 0)
        self.assertEqual(ui.aspiration_movements, [])
        # Phase TERMINALE transitoire : nouveau tour démarré directement
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        self.assertEqual(ui.game.turn_count, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
