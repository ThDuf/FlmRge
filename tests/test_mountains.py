"""Tests des règles de montagnes (montées/descentes) - rulebook officiel.

Montée (bords rouges) :
- entrée dans les 5 premières cases (ou départ en montée) : plafonné à 5
- entrée à la 6e case ou plus : arrêt sur la dernière file libre AVANT la montée
- un coureur en montée ne donne ni ne reçoit l'aspiration (mais les autres
  membres du pack hors montée glissent quand même - exemple Dized)

Descente (bords bleus) : partir d'une descente = minimum 5 cases.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, TileType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game  # noqa: E402


def make_track(spec):
    """spec : liste de types, ou de tuples (type, cases)."""
    track = Track()
    for item in spec:
        t, cells = item if isinstance(item, tuple) else (item, None)
        track.add_tile(t, cells=cells)
    return track


def first_cell_of(track, ttype):
    """Première case d'une tuile du type donné."""
    return next(t.x for t in track.tiles if t.type == ttype)


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y=0):
    cell = track.get_cell(x, y)
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


def run_aspiration(track):
    steps = track.compute_slipstream_steps()
    for step in steps:
        track.apply_slipstream_step(step)
    return steps


# Piste avec une montée de 2 cases (comme une vraie tuile virage retournée)
# cases : START 0-1, STRAIGHT 2-19, UPHILL 20-21, STRAIGHT 22-39
MOUNTAIN_TRACK = ([TileType.START] + [TileType.STRAIGHT] * 3
                  + [(TileType.UPHILL, 2)] + [TileType.STRAIGHT] * 3)
# Piste avec une descente de 6 cases (tuile droite)
# cases : START 0-1, DOWNHILL 2-7, STRAIGHT 8-31
DOWNHILL_TRACK = ([TileType.START] + [(TileType.DOWNHILL, 6)] + [TileType.STRAIGHT] * 4)


class TestAscentMovement(unittest.TestCase):
    def setUp(self):
        self.track = make_track(MOUNTAIN_TRACK)
        self.up = first_cell_of(self.track, TileType.UPHILL)  # 20

    def test_ascent_caps_movement_at_5(self):
        """Carte 8 dont le trajet touche la montée (entrée en 4e case) -> 5."""
        r = place(self.track, make_runner('r'), self.up - 4, 0)
        self.track.move_runner(r, 8)
        self.assertEqual(r.x, self.up + 1)  # up-4 + 5

    def test_rider_starting_on_ascent_is_capped(self):
        r = place(self.track, make_runner('r'), self.up, 0)
        self.track.move_runner(r, 7)
        self.assertEqual(r.x, self.up + 5)

    def test_no_cap_when_ascent_not_on_path(self):
        r = place(self.track, make_runner('r'), 0, 0)
        self.track.move_runner(r, 6)   # cible 6, avant la montée
        self.assertEqual(r.x, 6)

    def test_sixth_move_cannot_enter_ascent(self):
        """La montée est à 6 cases, carte 8 : arrêt à 5 cases (up-1)."""
        r = place(self.track, make_runner('r'), self.up - 6, 0)
        self.track.move_runner(r, 8)
        self.assertEqual(r.x, self.up - 1)

    def test_card_7_at_7_cases_stops_before_ascent(self):
        """Règle FR : 'se déplace d'au moins 5 cases avant d'entrer dans la
        montée -> stoppe sur la dernière file libre avant la montée'.
        Carte 7 à 7 cases de la montée -> 6 cases, arrêt juste avant."""
        r = place(self.track, make_runner('r'), self.up - 7, 0)
        self.track.move_runner(r, 7)
        self.assertEqual(r.x, self.up - 1)

    def test_card_8_at_8_cases_stops_before_ascent(self):
        r = place(self.track, make_runner('r'), self.up - 8, 0)
        self.track.move_runner(r, 8)
        self.assertEqual(r.x, self.up - 1)

    def test_card_below_5_crossing_ascent_is_unchanged(self):
        r = place(self.track, make_runner('r'), self.up - 2, 0)
        self.track.move_runner(r, 3)   # carte 3, traverse la montée
        self.assertEqual(r.x, self.up + 1)

    def test_climbing_from_the_foot_of_the_ascent(self):
        """Au pied de la montée (case adjacente), un 5 traverse et sort."""
        r = place(self.track, make_runner('r'), self.up - 1, 0)
        self.track.move_runner(r, 5)
        self.assertEqual(r.x, self.up + 4)


class TestDescentMovement(unittest.TestCase):
    def setUp(self):
        self.track = make_track(DOWNHILL_TRACK)
        self.down = first_cell_of(self.track, TileType.DOWNHILL)  # 2

    def test_descent_gives_minimum_5(self):
        r = place(self.track, make_runner('r'), self.down, 0)
        self.track.move_runner(r, 2)
        self.assertEqual(r.x, self.down + 5)

    def test_descent_does_not_cap_high_cards(self):
        r = place(self.track, make_runner('r'), self.down, 0)
        self.track.move_runner(r, 7)
        self.assertEqual(r.x, self.down + 7)

    def test_descent_only_from_descent_start(self):
        """Le minimum 5 ne s'applique qu'en PARTANT d'une descente."""
        r = place(self.track, make_runner('r'), self.down + 6, 0)  # plaine
        self.track.move_runner(r, 2)
        self.assertEqual(r.x, self.down + 8)

    def test_descent_then_ascent_caps_back_to_5(self):
        track = make_track([TileType.START, (TileType.DOWNHILL, 6),
                            TileType.STRAIGHT, (TileType.UPHILL, 2),
                            TileType.STRAIGHT, TileType.STRAIGHT])
        # cases : 0-1 START, 2-7 DOWN, 8-13 STRAIGHT, 14-15 UP, 16-27 STRAIGHT
        r = place(track, make_runner('r'), 2, 0)
        track.move_runner(r, 2)   # min 5 -> cible 7, montée à 14 non touchée
        self.assertEqual(r.x, 7)


class TestAscentSlipstream(unittest.TestCase):
    def test_rider_on_ascent_cannot_receive(self):
        """Un coureur SUR une montée ne reçoit pas l'aspiration."""
        track = make_track(MOUNTAIN_TRACK)
        up = first_cell_of(track, TileType.UPHILL)
        rear = place(track, make_runner('rear'), up, 0)
        place(track, make_runner('ahead'), up + 2, 0)  # 1 case vide entre les deux
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertNotIn('rear', moved_ids)

    def test_rider_on_ascent_cannot_give(self):
        """Le donneur (le plus en arrière du pack de devant) est en montée."""
        track = make_track(MOUNTAIN_TRACK)
        up = first_cell_of(track, TileType.UPHILL)
        place(track, make_runner('rear'), up - 2, 0)   # plaine
        place(track, make_runner('giver'), up, 0)      # 1re case de montée
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertNotIn('rear', moved_ids)
        self.assertNotIn('giver', moved_ids)

    def test_pack_splits_on_ascent_during_slipstream(self):
        """Exemple officiel Dized : le sprinteur hors montée en tête glisse
        et fusionne, le rouleur en montée reste ('left behind')."""
        track = make_track(MOUNTAIN_TRACK)
        up = first_cell_of(track, TileType.UPHILL)  # 20-21
        rouleur = place(track, make_runner('rouleur'), up + 1, 0)      # MONTÉE (2e case)
        sprinteur = place(track, make_runner('sprinteur'), up + 2, 0)  # plaine, tête du pack
        place(track, make_runner('giver'), up + 4, 0)                  # plaine, gap en up+3
        run_aspiration(track)
        self.assertEqual(sprinteur.x, up + 3)  # parti fusionner avec le giver
        self.assertEqual(rouleur.x, up + 1)    # laissé sur place

    def test_ascent_rider_blocks_packmates_behind(self):
        """Un coureur en montée au milieu d'un pack bloque ceux derrière lui."""
        track = make_track([TileType.START, TileType.STRAIGHT,
                            (TileType.UPHILL, 2), TileType.STRAIGHT, TileType.STRAIGHT])
        # cases : 0-1 START, 2-7 STRAIGHT, 8-9 UPHILL, 10-21 STRAIGHT
        front = place(track, make_runner('front'), 10, 0)    # plaine, tête
        frozen = place(track, make_runner('frozen'), 9, 0)   # MONTÉE
        rear = place(track, make_runner('rear'), 8, 0)       # MONTÉE
        place(track, make_runner('giver'), 12, 0)            # gap en 11
        run_aspiration(track)
        self.assertEqual(front.x, 11)
        self.assertEqual(frozen.x, 9)
        self.assertEqual(rear.x, 8)

    def test_descent_slipstream_is_normal(self):
        """Exemple du rulebook : en descente, l'aspiration s'applique normalement."""
        track = make_track(DOWNHILL_TRACK)
        down = first_cell_of(track, TileType.DOWNHILL)
        rear = place(track, make_runner('rear'), down, 0)
        place(track, make_runner('front'), down + 2, 0)
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertIn('rear', moved_ids)


class TestCircuitStage(unittest.TestCase):
    def test_circuit_contains_mountains(self):
        game = Game(stage="circuit", player_count=2)
        tiles = [t.type for t in game.track.tiles]
        self.assertIn(TileType.UPHILL, tiles)
        self.assertIn(TileType.DOWNHILL, tiles)
        self.assertIn(TileType.SHARP_TURN, tiles)
        self.assertEqual(game.track.length, 93)  # circuit perso : 19 tuiles


if __name__ == '__main__':
    unittest.main(verbosity=2)
