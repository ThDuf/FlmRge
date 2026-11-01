"""Tests des règles de montagnes (montées/descentes) - rulebook officiel.

Montée (bord rouge) :
- entrée dans les 5 premières cases (ou départ en montée) : plafonné à 5
- entrée à la 6e case ou plus : arrêt sur la dernière file libre AVANT la montée
- un coureur en montée ne donne ni ne reçoit l'aspiration (mais les autres
  membres du pack hors montée glissent quand même - exemple Dized)

Descente (bord bleu) : partir d'une descente = minimum 5 cases.
"""
import os
import sys
import math
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, make_tile, CellGeographyType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game  # noqa: E402


def make_track(spec):
    """spec : liste de chaînes de cases (alphabet CELL_CHARS, ex. 'uu')."""
    track = Track()
    for chars in spec:
        track.add_tile(make_tile(chars))
    return track


def first_cell_of(track, geography):
    """Première case d'une géographie donnée (UPHILL / DOWNHILL)."""
    return next(c.x for t in track.tiles for c in t.cells if c.geography == geography)


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
MOUNTAIN_TRACK = ["sssssf"] + ["ffffff"] * 3 + ["uu"] + ["ffffff"] * 3
# Piste avec une descente de 6 cases (tuile droite)
DOWNHILL_TRACK = ["sssssf", "dddddd"] + ["ffffff"] * 4


class TestAscentMovement(unittest.TestCase):
    def setUp(self):
        self.track = make_track(MOUNTAIN_TRACK)
        self.up = first_cell_of(self.track, CellGeographyType.UPHILL)

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
        self.down = first_cell_of(self.track, CellGeographyType.DOWNHILL)

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
        track = make_track(["sssssf", "dddddd", "ffffff", "uu", "ffffff", "ffffff"])
        down = first_cell_of(track, CellGeographyType.DOWNHILL)
        r = place(track, make_runner('r'), down, 0)
        track.move_runner(r, 2)   # min 5 -> cible down+5, montée loin
        self.assertEqual(r.x, down + 5)


class TestAscentSlipstream(unittest.TestCase):
    def test_rider_on_ascent_cannot_receive(self):
        """Un coureur SUR une montée ne reçoit pas l'aspiration."""
        track = make_track(MOUNTAIN_TRACK)
        up = first_cell_of(track, CellGeographyType.UPHILL)
        rear = place(track, make_runner('rear'), up, 0)
        place(track, make_runner('ahead'), up + 2, 0)  # 1 case vide entre les deux
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertNotIn('rear', moved_ids)

    def test_rider_on_ascent_cannot_give(self):
        """Le donneur (le plus en arrière du pack de devant) est en montée."""
        track = make_track(MOUNTAIN_TRACK)
        up = first_cell_of(track, CellGeographyType.UPHILL)
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
        up = first_cell_of(track, CellGeographyType.UPHILL)
        rouleur = place(track, make_runner('rouleur'), up + 1, 0)      # MONTÉE (2e case)
        sprinteur = place(track, make_runner('sprinteur'), up + 2, 0)  # plaine, tête du pack
        place(track, make_runner('giver'), up + 4, 0)                  # plaine, gap en up+3
        run_aspiration(track)
        self.assertEqual(sprinteur.x, up + 3)  # parti fusionner avec le giver
        self.assertEqual(rouleur.x, up + 1)    # laissé sur place

    def test_ascent_rider_blocks_packmates_behind(self):
        """Un coureur en montée au milieu d'un pack bloque ceux derrière lui."""
        track = make_track(["sssssf", "ffffff", "uu", "ffffff", "ffffff"])
        up = first_cell_of(track, CellGeographyType.UPHILL)
        front = place(track, make_runner('front'), up + 2, 0)   # plaine, tête
        frozen = place(track, make_runner('frozen'), up + 1, 0)  # MONTÉE
        rear = place(track, make_runner('rear'), up, 0)          # MONTÉE
        place(track, make_runner('giver'), up + 4, 0)            # gap en up+3
        run_aspiration(track)
        self.assertEqual(front.x, up + 3)
        self.assertEqual(frozen.x, up + 1)
        self.assertEqual(rear.x, up)

    def test_descent_slipstream_is_normal(self):
        """Exemple du rulebook : en descente, l'aspiration s'applique normalement."""
        track = make_track(DOWNHILL_TRACK)
        down = first_cell_of(track, CellGeographyType.DOWNHILL)
        rear = place(track, make_runner('rear'), down, 0)
        place(track, make_runner('front'), down + 2, 0)
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertIn('rear', moved_ids)


class TestMountainStage(unittest.TestCase):
    def test_haut_montagne_contains_mountains(self):
        game = Game(stage="La Haut Montagne", player_count=2)
        turns = [t.turn for t in game.track.tiles]
        geographies = [c.geography for t in game.track.tiles for c in t.cells]
        self.assertIn(CellGeographyType.UPHILL, geographies)
        self.assertIn(CellGeographyType.DOWNHILL, geographies)
        self.assertTrue(any(t and abs(t[0]) >= math.pi / 2 for t in turns))
        self.assertEqual(game.track.length, 78)  # étape officielle : 21 tuiles


if __name__ == '__main__':
    unittest.main(verbosity=2)
