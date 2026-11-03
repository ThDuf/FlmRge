"""Tests du panneau des groupes de l'écran de course : une ligne par pack,
« tête de course » pour le premier, « peloton » pour le plus gros,
« lanterne rouge » pour le dernier, « groupe <cycliste> » pour les autres."""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame  # noqa: E402
import main  # noqa: E402


def place_isolated(ui, positions):
    """Place les coureurs seuls aux cases indiquées (un groupe par coureur)."""
    track = ui.game.track
    riders = [r for p in ui.game.players for r in p.get_runners()]
    for x, lane, r in list(track.get_all_runners()):
        track.get_cell(x, lane).remove_runner(lane)
    for r, x in zip(riders, positions):
        track.get_cell(x, 0).set_runner(r, 0)


class TestGroupNames(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="Avenue Corso Paseo")

    def test_four_isolated_riders(self):
        """4 coureurs isolés : tête / groupe cycliste x2 / lanterne rouge."""
        place_isolated(self.ui, [20, 15, 10, 5])
        names = self.ui._group_names()
        labels = [n[0] for n in names]
        self.assertEqual(labels[0], "Tête de course")
        self.assertEqual(labels[-1], "Lanterne rouge")
        self.assertTrue(labels[1].startswith("Groupe "))
        self.assertTrue(labels[2].startswith("Groupe "))
        self.assertNotEqual(labels[1], labels[2])  # cyclistes différents
        # positions : le plus avancé en premier
        self.assertEqual(names[0][2], 20)
        self.assertEqual(names[-1][2], 5)

    def test_biggest_group_is_peloton(self):
        """Le plus gros pack s'appelle « peloton » (même entre les deux)."""
        track = self.ui.game.track
        riders = [r for p in self.ui.game.players for r in p.get_runners()]
        for x, lane, r in list(track.get_all_runners()):
            track.get_cell(x, lane).remove_runner(lane)
        track.get_cell(30, 0).set_runner(riders[0], 0)          # tête, seul
        track.get_cell(20, 0).set_runner(riders[1], 0)          # peloton (3)
        track.get_cell(20, 1).set_runner(riders[2], 1)
        track.get_cell(21, 0).set_runner(riders[3], 0)
        names = self.ui._group_names()
        labels = [n[0] for n in names]
        self.assertEqual(labels, ["Tête de course", "Peloton"])

    def test_single_group_is_peloton(self):
        place_isolated(self.ui, [10, 10, 11, 11])
        # 2 cases consécutives -> un seul groupe de 4
        names = self.ui._group_names()
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0][0], "Peloton")

    def test_panel_renders(self):
        """Le panneau se dessine sans erreur avec plusieurs groupes."""
        pygame.display.set_mode((1200, 800))
        self.ui.width, self.ui.height = 1200, 800
        self.ui.screen = pygame.display.set_mode((1200, 800))
        place_isolated(self.ui, [20, 15, 10, 5])
        self.ui.screen.fill(main.BG)
        self.ui._draw_groups_panel()
        self.assertTrue(self.ui._group_names())


if __name__ == '__main__':
    unittest.main()
