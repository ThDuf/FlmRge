"""Tests headless du moteur d'aspiration (règle officielle Flamme Rouge).

Règle testée : si EXACTEMENT une case vide sépare deux groupes de coureurs,
le groupe arrière avance d'une case (avec cascade tant que de nouvelles
situations d'aspiration apparaissent).

Lancé :  python -m unittest tests.test_aspiration -v
ou       python -m pytest tests/
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, TileType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402


def make_track(min_cells):
    track = Track()
    while track.length < min_cells:
        track.add_tile(TileType.STRAIGHT)
    return track


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y):
    cell = track.get_cell(x, y)
    assert cell is not None, f"case ({x},{y}) hors piste"
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


def positions(track, *runners):
    """Positions (x) des coureurs, dans l'ordre donné."""
    return {r.id: r.x for r in runners}


def assert_consistent(testcase, track):
    """Chaque coureur doit être référencé par exactement une case, avec x/y cohérents."""
    seen = {}
    for x, y, runner in track.get_all_runners():
        testcase.assertNotIn(
            runner.id, seen,
            f"{runner.id} est référencé dans plusieurs cases (duplication d'état !)",
        )
        seen[runner.id] = (x, y)
        testcase.assertEqual((runner.x, runner.y), (x, y),
                             f"{runner.id} : runner.x/y désynchronisés de la piste")


class TestGetGroups(unittest.TestCase):
    def test_adjacent_squares_same_group(self):
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 2, 0)
        r2 = place(t, make_runner('r2'), 3, 1)
        r3 = place(t, make_runner('r3'), 5, 0)
        groups = t.get_groups()
        self.assertEqual(len(groups), 2)
        self.assertEqual([r.id for r in groups[0]], ['r1', 'r2'])
        self.assertEqual([r.id for r in groups[1]], ['r3'])

    def test_same_square_same_group(self):
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 4, 0)
        r2 = place(t, make_runner('r2'), 4, 1)
        groups = t.get_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)


class TestApplyAspiration(unittest.TestCase):
    def test_simple_slipstream(self):
        """1 case vide entre 2 coureurs isolés -> l'arrière avance de 1."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        front = place(t, make_runner('front'), 7, 0)
        movements = t.apply_aspiration()
        self.assertEqual(len(movements), 1)
        self.assertEqual(rear.x, 6)
        self.assertEqual(front.x, 7)
        assert_consistent(self, t)

    def test_no_slipstream_with_two_empty_squares(self):
        """2 cases vides entre les groupes -> aucune aspiration."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 4, 0)
        front = place(t, make_runner('front'), 7, 0)
        movements = t.apply_aspiration()
        self.assertEqual(movements, [])
        self.assertEqual(rear.x, 4)
        self.assertEqual(front.x, 7)
        assert_consistent(self, t)

    def test_no_slipstream_single_group(self):
        """Coureurs adjacents = un seul groupe, rien à faire."""
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 5, 0)
        r2 = place(t, make_runner('r2'), 6, 0)
        movements = t.apply_aspiration()
        self.assertEqual(movements, [])
        self.assertEqual((r1.x, r2.x), (5, 6))
        assert_consistent(self, t)

    def test_two_lanes_group_moves_together(self):
        """Groupe arrière à 2 coureurs (files A+B) : les deux avancent."""
        t = make_track(20)
        ra = place(t, make_runner('ra'), 3, 0)
        rb = place(t, make_runner('rb'), 3, 1)
        front = place(t, make_runner('front'), 5, 0)
        movements = t.apply_aspiration()
        self.assertEqual(len(movements), 2)
        self.assertEqual((ra.x, rb.x), (4, 4))
        self.assertEqual(front.x, 5)
        assert_consistent(self, t)

    def test_group_over_two_squares(self):
        """Groupe arrière étalé sur 2 cases : chacun avance de 1, l'ordre est préservé."""
        t = make_track(20)
        r_back = place(t, make_runner('r_back'), 2, 0)
        r_front = place(t, make_runner('r_front'), 3, 1)
        ahead = place(t, make_runner('ahead'), 5, 0)
        movements = t.apply_aspiration()
        self.assertEqual(len(movements), 2)
        self.assertEqual((r_back.x, r_front.x), (3, 4))
        self.assertEqual(ahead.x, 5)
        assert_consistent(self, t)

    def test_cascade_slipstream(self):
        """Cascade : A[1] B[3] C[5] -> A avance, puis le groupe fusionné avance."""
        t = make_track(20)
        a = place(t, make_runner('a'), 1, 0)
        b = place(t, make_runner('b'), 3, 0)
        c = place(t, make_runner('c'), 5, 0)
        movements = t.apply_aspiration()
        # 1er mouvement : a 1->2 ; puis groupes {2,3} et {5} -> b et a avancent encore
        self.assertGreaterEqual(len(movements), 3)
        self.assertEqual((a.x, b.x, c.x), (3, 4, 5))
        assert_consistent(self, t)

    def test_leading_group_does_not_move(self):
        """Seul le groupe ARRIÈRE bouque ; le groupe devant reste immobile."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 8, 1)
        front_a = place(t, make_runner('fa'), 10, 0)
        front_b = place(t, make_runner('fb'), 10, 1)
        t.apply_aspiration()
        self.assertEqual(rear.x, 9)
        self.assertEqual((front_a.x, front_b.x), (10, 10))
        assert_consistent(self, t)

    def test_gap_square_partially_occupied_is_one_group(self):
        """Si la case intermédiaire contient un coureur, les groupes sont fusionnés."""
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 4, 0)
        r2 = place(t, make_runner('r2'), 5, 1)
        r3 = place(t, make_runner('r3'), 6, 0)
        groups = t.get_groups()
        self.assertEqual(len(groups), 1)  # pas de case vide entre eux
        movements = t.apply_aspiration()
        self.assertEqual(movements, [])
        assert_consistent(self, t)

    def test_aspiration_is_idempotent(self):
        """Un 2e appel ne doit rien déplacer (état stable)."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        front = place(t, make_runner('front'), 7, 0)
        t.apply_aspiration()
        movements = t.apply_aspiration()
        self.assertEqual(movements, [])
        self.assertEqual(rear.x, 6)
        assert_consistent(self, t)

    def test_runner_at_finish_never_moves(self):
        """Le coureur sur la dernière case ne bouge pas ; les autres aspirent en cascade."""
        t = make_track(10)  # cases 0..9
        rear = place(t, make_runner('rear'), 5, 0)
        mid = place(t, make_runner('mid'), 7, 0)
        winner = place(t, make_runner('winner'), 9, 0)
        t.apply_aspiration()
        # cascade : rear 5->6 ; mid 7->8 ; puis rear 6->7 (une case vide entre 7 et 8)
        self.assertEqual((rear.x, mid.x, winner.x), (7, 8, 9))
        assert_consistent(self, t)


class TestReapplyBug(unittest.TestCase):
    def test_reapplying_movements_corrupts_state(self):
        """Régression : l'UI réappliquait les mouvements déjà appliqués par
        apply_aspiration(), ce qui dupliquait les coureurs sur la piste.
        apply_aspiration() applique DÉJÀ les mouvements : les rejouer est un bug."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        front = place(t, make_runner('front'), 7, 0)
        movements = t.apply_aspiration()  # état final déjà appliqué : rear à 6

        # Simule l'ancien _apply_next_aspiration_step de main.py
        runner, old_x, new_x = movements[0]
        old_cell = t.get_cell(old_x, runner.y)
        if old_cell:
            old_cell.remove_runner(runner.y)
        runner.x = new_x
        new_cell = t.get_cell(new_x, runner.y)
        if new_cell and new_cell.is_empty(runner.y):
            new_cell.set_runner(runner, runner.y)
        else:
            runner.x = old_x
            if old_cell:
                old_cell.set_runner(runner, runner.y)

        # Le coureur se retrouve référencé à la fois à 6 (par apply_aspiration)
        # et repositionné à 5 : duplication détectée par assert_consistent.
        with self.assertRaises(AssertionError):
            assert_consistent(self, t)


if __name__ == '__main__':
    unittest.main(verbosity=2)
