"""Tests headless de l'aspiration et de la fatigue (règles officielles Flamme Rouge).

Règles officielles (rulebook, End Phase) :
- "Pack" = un ou plusieurs coureurs sans case vide (2 files) entre eux.
- Slipstream : si exactement UNE case vide sépare deux packs, le pack
  arrière avance d'une case et fusionne. Le pack fusionné est revérifié
  immédiatement (un coureur peut aspirer plusieurs fois par tour).
- Chaque coureur garde sa file lors de l'aspiration.
- Fatigue : chaque coureur dont la CASE devant (2 files) est vide reçoit
  une carte Fatigue. Une simple file libre ne suffit pas.

Lancé :  python -m unittest tests.test_aspiration -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, TileType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game  # noqa: E402


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


def run_aspiration(track):
    """Calcule puis applique toutes les étapes, comme le ferait l'UI."""
    steps = track.compute_slipstream_steps()
    for step in steps:
        track.apply_slipstream_step(step)
    return steps


def assert_consistent(testcase, track):
    """Chaque coureur doit être référencé par exactement une case, x/y cohérents."""
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
    def test_adjacent_squares_same_pack(self):
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 2, 0)
        r2 = place(t, make_runner('r2'), 3, 1)
        r3 = place(t, make_runner('r3'), 5, 0)
        groups = t.get_groups()
        self.assertEqual(len(groups), 2)
        self.assertEqual([r.id for r in groups[0]], ['r1', 'r2'])
        self.assertEqual([r.id for r in groups[1]], ['r3'])

    def test_same_square_same_pack(self):
        t = make_track(20)
        place(t, make_runner('r1'), 4, 0)
        place(t, make_runner('r2'), 4, 1)
        groups = t.get_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)


class TestSlipstream(unittest.TestCase):
    def test_simple_slipstream(self):
        """1 case vide entre 2 coureurs -> l'arrière avance de 1, même file."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        front = place(t, make_runner('front'), 7, 0)
        steps = run_aspiration(t)
        self.assertEqual(len(steps), 1)
        self.assertEqual((rear.x, rear.y), (6, 0))
        self.assertEqual((front.x, front.y), (7, 0))
        assert_consistent(self, t)

    def test_no_slipstream_with_two_empty_squares(self):
        t = make_track(20)
        rear = place(t, make_runner('rear'), 4, 0)
        front = place(t, make_runner('front'), 7, 0)
        steps = run_aspiration(t)
        self.assertEqual(steps, [])
        self.assertEqual((rear.x, front.x), (4, 7))
        assert_consistent(self, t)

    def test_single_pack_no_move(self):
        t = make_track(20)
        r1 = place(t, make_runner('r1'), 5, 0)
        r2 = place(t, make_runner('r2'), 6, 0)
        self.assertEqual(run_aspiration(t), [])
        self.assertEqual((r1.x, r2.x), (5, 6))
        assert_consistent(self, t)

    def test_lanes_are_preserved(self):
        """Règle officielle : le pack "glisse", chaque coureur garde sa file."""
        t = make_track(20)
        ra = place(t, make_runner('ra'), 3, 0)
        rb = place(t, make_runner('rb'), 3, 1)
        place(t, make_runner('front'), 5, 0)
        steps = run_aspiration(t)
        self.assertEqual(len(steps), 1)
        self.assertEqual((ra.x, ra.y), (4, 0))
        self.assertEqual((rb.x, rb.y), (4, 1))
        assert_consistent(self, t)

    def test_pack_over_two_squares_keeps_lanes(self):
        t = make_track(20)
        r_back = place(t, make_runner('r_back'), 2, 0)
        r_front = place(t, make_runner('r_front'), 3, 1)
        place(t, make_runner('ahead'), 5, 0)
        steps = run_aspiration(t)
        self.assertEqual(len(steps), 1)
        self.assertEqual((r_back.x, r_back.y), (3, 0))
        self.assertEqual((r_front.x, r_front.y), (4, 1))
        assert_consistent(self, t)

    def test_rulebook_example(self):
        """Exemple officiel du rulebook : Pack1 trop loin ne bouge pas ;
        Pack2 aspire (fusion A), puis le pack fusionné aspire encore
        (fusion B) -> les coureurs du Pack2 bougent de 2, ceux du Pack3 de 1."""
        t = make_track(20)
        p1a = place(t, make_runner('p1a'), 0, 0)
        p1b = place(t, make_runner('p1b'), 0, 1)
        p2a = place(t, make_runner('p2a'), 3, 0)
        p2b = place(t, make_runner('p2b'), 3, 1)
        p3a = place(t, make_runner('p3a'), 5, 0)
        p3b = place(t, make_runner('p3b'), 5, 1)
        p4a = place(t, make_runner('p4a'), 7, 0)
        p4b = place(t, make_runner('p4b'), 7, 1)
        steps = run_aspiration(t)
        # 2 étapes : Pack2 (+fusion), puis pack fusionné 2+3 (+fusion avec Pack4)
        self.assertEqual(len(steps), 2)
        self.assertEqual(len(steps[0]), 2)   # Pack2 : 2 coureurs
        self.assertEqual(len(steps[1]), 4)   # Pack fusionné : 4 coureurs
        self.assertEqual((p1a.x, p1b.x), (0, 0))       # Pack1 ne bouge pas
        self.assertEqual((p2a.x, p2b.x), (5, 5))       # Pack2 : +2
        self.assertEqual((p3a.x, p3b.x), (6, 6))       # Pack3 : +1
        self.assertEqual((p4a.x, p4b.x), (7, 7))       # Pack4 : immobile
        assert_consistent(self, t)

    def test_leading_pack_never_moves(self):
        t = make_track(20)
        rear = place(t, make_runner('rear'), 8, 1)
        front_a = place(t, make_runner('fa'), 10, 0)
        front_b = place(t, make_runner('fb'), 10, 1)
        run_aspiration(t)
        self.assertEqual(rear.x, 9)
        self.assertEqual((front_a.x, front_b.x), (10, 10))
        assert_consistent(self, t)

    def test_gap_square_partially_occupied_is_one_pack(self):
        """Une case intermédiaire occupée fusionne les packs : pas d'aspiration."""
        t = make_track(20)
        place(t, make_runner('r1'), 4, 0)
        place(t, make_runner('r2'), 5, 1)
        place(t, make_runner('r3'), 6, 0)
        self.assertEqual(len(t.get_groups()), 1)
        self.assertEqual(run_aspiration(t), [])
        assert_consistent(self, t)

    def test_slipstream_is_idempotent(self):
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        front = place(t, make_runner('front'), 7, 0)
        run_aspiration(t)
        self.assertEqual(t.compute_slipstream_steps(), [])
        self.assertEqual(rear.x, 6)
        assert_consistent(self, t)

    def test_runner_at_finish_never_moves(self):
        """Le coureur sur la dernière case ne bouge pas ; les autres aspirent en cascade."""
        t = make_track(10)  # cases 0..9
        rear = place(t, make_runner('rear'), 5, 0)
        mid = place(t, make_runner('mid'), 7, 0)
        winner = place(t, make_runner('winner'), 9, 0)
        run_aspiration(t)
        # cascade officielle : Pack{rear} fusionne avec mid (rear 5->6),
        # puis le pack fusionné avance (rear 6->7, mid 7->8)
        self.assertEqual((rear.x, mid.x, winner.x), (7, 8, 9))
        assert_consistent(self, t)

    def test_steps_not_applied_until_explicit(self):
        """compute_slipstream_steps() ne modifie PAS le plateau."""
        t = make_track(20)
        rear = place(t, make_runner('rear'), 5, 0)
        place(t, make_runner('front'), 7, 0)
        steps = t.compute_slipstream_steps()
        self.assertEqual(len(steps), 1)
        self.assertEqual(rear.x, 5)  # rien n'a bougé
        t.apply_slipstream_step(steps[0])
        self.assertEqual(rear.x, 6)
        assert_consistent(self, t)


class TestFatigue(unittest.TestCase):
    def test_empty_square_ahead_causes_fatigue(self):
        """Case devant vide (2 files) -> fatigue."""
        t = make_track(20)
        r = place(t, make_runner('r'), 5, 0)
        self.assertTrue(t.is_square_empty(6))

    def test_empty_lane_only_is_not_fatigue(self):
        """Règle officielle : une simple FILE libre devant ne fatigue PAS
        (le pack roule au milieu de la route)."""
        t = make_track(20)
        r = place(t, make_runner('r'), 5, 0)
        other = place(t, make_runner('other'), 6, 1)  # file B occupée devant lui
        self.assertFalse(t.is_square_empty(6))

    def test_two_leaders_both_get_fatigue(self):
        """Deux coureurs côte à côte en tête d'un pack, case devant vide :
        les DEUX reçoivent une carte Fatigue (pas seulement un leader)."""
        game = Game(stage="test", player_count=2)
        # Vider la piste puis replacer : sprinteur_0 et roller_0 côte à côte,
        # tous les autres loin derrière.
        track = game.track
        for x, y, r in track.get_all_runners():
            track.get_cell(x, y).remove_runner(y)
        r1 = game.players[0].sprinter
        r2 = game.players[0].roller
        place(track, r1, 10, 0)
        place(track, r2, 10, 1)
        before = len(r1.discard_pile) + len(r2.discard_pile)
        game._assign_fatigue_cards()
        self.assertEqual(len(r1.discard_pile) + len(r2.discard_pile), before + 2)
        # un coureur abrité derrière ne reçoit rien
        r3 = game.players[1].sprinter
        place(track, r3, 9, 0)
        r3.discard_pile.clear()
        game._assign_fatigue_cards()
        self.assertEqual(len(r3.discard_pile), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
