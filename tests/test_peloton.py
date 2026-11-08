"""Tests de l'extension Peloton (modèle : pavés + zones d'approvisionnement).

Règles officielles (docs/extension-peloton.md) :
- les cases peuvent faire 1 à 3 files (pas seulement 2) ;
- PAVÉS : section à 1 file, AUCUNE aspiration donnée ni reçue dessus (comme une montée) ;
- ZONE D'APPROVISIONNEMENT : 3 files, vitesse minimale 4 si on y commence son tour.

Lancé :  python -m unittest tests.test_peloton -v
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, make_tile, CellGeographyType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game, tile_def_for_letter, build_tile  # noqa: E402


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y):
    cell = track.get_cell(x, y)
    assert cell is not None, f"case ({x},{y}) hors piste"
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


class TestPelotonTiles(unittest.TestCase):
    def test_peloton_tile_defs(self):
        """Tuiles Peloton : v = pavés 1 file, w = appro 3 files, x/y = pavés en virage."""
        v = build_tile('v')
        self.assertEqual(v.width, 1)
        self.assertTrue(all(c.geography == CellGeographyType.COBBLE for c in v.cells))
        w = build_tile('w')
        self.assertEqual(w.width, 3)
        self.assertTrue(all(c.geography == CellGeographyType.SUPPLY for c in w.cells))
        self.assertEqual(tile_def_for_letter('x')[1], 1)

    def test_game_peloton_flag(self):
        g = Game(stage="test", player_count=2, peloton=True)
        self.assertTrue(g.peloton)
        g2 = Game(stage="test", player_count=2)
        self.assertFalse(g2.peloton)

    def test_menu_checkbox_wires_peloton(self):
        import main
        ui = main.FlammeRougeGame()
        ui.ext_peloton = True
        ui._select_stage("Avenue Corso Paseo")
        self.assertTrue(ui.game.peloton)
        ui2 = main.FlammeRougeGame()
        ui2._select_stage("Avenue Corso Paseo")
        self.assertFalse(ui2.game.peloton)


class TestCobblestones(unittest.TestCase):
    def _track(self):
        # tuile plate 0-5, tuile pavés 6-11 (1 file), tuile plate 12-17
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('v'))
        track.add_tile(make_tile("ffffff"))
        return track

    def test_no_slipstream_on_cobbles_giver_or_receiver(self):
        """Pavés : aucune aspiration donnée ni reçue (donneur et receveur)."""
        track = self._track()
        # donneur en case 6 (pavés), receveur en case 4, case 5 vide entre les deux
        giver = place(track, make_runner("g"), 6, 0)
        rear = place(track, make_runner("r"), 4, 0)
        self.assertEqual(track.compute_slipstream_steps(), [])
        track.apply_aspiration()
        self.assertEqual(rear.x, 4)
        # contrôle : même config sur plat -> aspiration
        track2 = Track()
        for _ in range(3):
            track2.add_tile(make_tile("ffffff"))
        place(track2, make_runner("g"), 6, 0)
        rear2 = place(track2, make_runner("r"), 4, 0)
        self.assertEqual(len(track2.compute_slipstream_steps()), 1)

    def test_single_lane_cell(self):
        """Case pavée = 1 file : un 2e coureur ne peut pas s'y mettre (recul)."""
        track = self._track()
        place(track, make_runner("a"), 7, 0)
        b = place(track, make_runner("b"), 6, 0)
        track.move_runner(b, 2)  # viserait case 8 (libre) ; case 7 pleine à 1 file
        self.assertEqual(b.x, 8)  # a pu avancer (case 8 libre)
        # si la case visée est pleine à 1 file -> recul derrière
        track2 = self._track()
        place(track2, make_runner("a"), 8, 0)
        b2 = place(track2, make_runner("b"), 6, 0)
        track2.move_runner(b2, 2)  # case 8 pleine (1 file) -> s'arrête en 7
        self.assertEqual(b2.x, 7)


class TestSupplyZone(unittest.TestCase):
    def test_min_speed_4_when_starting_in_supply(self):
        """Zone d'approvisionnement : commencer son tour là-dedans = minimum 4."""
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('w'))  # cases 6-11 en appro, 3 files
        track.add_tile(make_tile("ffffff"))
        steps, reason = track.effective_steps(6, 2)
        self.assertEqual(steps, 4)
        self.assertIn("approvisionnement", reason)
        # case 5 (plat) : pas de minimum
        steps2, _ = track.effective_steps(5, 2)
        self.assertEqual(steps2, 2)
        # carte >= 4 : inchangé
        steps3, _ = track.effective_steps(6, 7)
        self.assertEqual(steps3, 7)

    def test_three_lanes_fit(self):
        """Case d'approvisionnement = 3 files : 3 coureurs côte à côte."""
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('w'))
        for lane in range(3):
            place(track, make_runner(f"r{lane}"), 6, lane)
        self.assertTrue(track.get_cell(6, 0).is_full())
        self.assertEqual(len(track.get_cell(6, 0).runners), 3)


if __name__ == "__main__":
    unittest.main()
