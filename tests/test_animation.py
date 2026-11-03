"""Tests des animations fluides des déplacements (glissade le long du circuit).

Vérifie que :
- chaque mouvement / étape d'aspiration pousse une animation (from -> to),
- _advance_step est bloqué tant qu'une animation est en cours,
- le rendu interpole la position pendant l'animation sans planter.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame  # noqa: E402
import main  # noqa: E402
from game.game import Phase  # noqa: E402


def finish_animations(ui):
    for a in ui.animations:
        a["t0"] = -(10 ** 9)  # force la fin (get_ticks gelé à 0 en headless)
    ui._prune_animations()


class TestMovementAnimation(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="Avenue Corso Paseo")
        self.game = self.ui.game

    def _start_movement(self):
        for player in self.game.players:
            for runner in player.get_runners():
                self.game.play_card(player, runner, runner.hand[0])
        self.ui._start_movement_phase()
        self.assertTrue(self.ui.showing_movement)

    def test_each_movement_step_pushes_animation(self):
        self._start_movement()
        move = self.ui.movement_movements[0]
        runner, value = move
        from_x, from_y = runner.x, runner.y
        self.ui._next_movement_step()
        self.assertEqual(len(self.ui.animations), 1)
        a = self.ui.animations[0]
        self.assertEqual(a["rid"], runner.id)
        self.assertEqual((a["from_x"], a["from_lane"]), (from_x, from_y))
        self.assertEqual((a["to_x"], a["to_lane"]), (runner.x, runner.y))
        self.assertGreater(a["dur"], 0)

    def test_no_animation_when_blocked(self):
        """Un coureur bloqué (même case) ne déclenche pas d'animation."""
        self.ui._push_animation("r", 5, 0, 5, 0)
        self.assertEqual(self.ui.animations, [])

    def test_advance_blocked_during_animation(self):
        """Tant qu'une animation est active, ENTRÉE/bouton ne fait rien."""
        self._start_movement()
        self.ui._next_movement_step()          # pousse une animation
        self.assertTrue(self.ui._animations_active())
        remaining = len(self.ui.movement_movements)
        self.ui._advance_step()                # doit être ignoré
        self.assertEqual(len(self.ui.movement_movements), remaining)
        finish_animations(self.ui)
        self.assertFalse(self.ui._animations_active())
        self.ui._advance_step()                # maintenant ça avance
        self.assertEqual(len(self.ui.movement_movements), remaining - 1)

    def test_draw_runners_interpolates_during_animation(self):
        """Le rendu pendant une animation ne plante pas et consomme l'anim."""
        pygame.display.set_mode((1200, 800))
        self._start_movement()
        self.ui._next_movement_step()
        self.assertTrue(self.ui.animations)
        self.ui._draw_runners()  # t au milieu de l'animation : interpolation
        finish_animations(self.ui)
        self.ui._draw_runners()  # animation terminée : position finale
        self.assertEqual(self.ui.animations, [])

    def test_aspiration_step_animates_each_runner(self):
        """Une étape d'aspiration pousse une animation par coureur du pack."""
        game = self.game
        # Deux packs séparés d'exactement une case vide (11) : l'aspiration
        # doit glisser le pack arrière d'une case.
        track = game.track
        riders = [r for p in game.players for r in p.get_runners()]
        for x, lane, r in list(track.get_all_runners()):
            track.get_cell(x, lane).remove_runner(lane)
        track.get_cell(10, 0).set_runner(riders[0], 0)
        track.get_cell(12, 0).set_runner(riders[1], 0)
        game.current_phase = Phase.MOVEMENT
        steps = game.resolve_aspiration_phase()
        self.assertTrue(steps)
        self.ui.aspiration_movements = steps
        self.ui._initialize_aspiration()
        n_runners = len(steps[0])
        self.ui._next_aspiration_step()
        self.assertEqual(len(self.ui.animations), n_runners)
        for a in self.ui.animations:
            self.assertEqual(a["to_x"] - a["from_x"], 1)  # +1 case

    def test_random_turn_clears_animations(self):
        self.ui.animations = [{"rid": "x", "from_x": 1, "from_lane": 0,
                               "to_x": 3, "to_lane": 0, "t0": 1, "dur": 10 ** 9}]
        self.ui._play_random_turn()
        self.assertEqual(self.ui.animations, [])


if __name__ == '__main__':
    unittest.main()
