"""Tests des règles de montagnes (montées/descentes) - rulebook officiel.

Montée (bords rouges) :
- Un coureur qui part de, entre dans ou traverse une montée ne peut jamais
  avancer de plus de 5 cases (carte supérieure jouable mais plafonnée).
- La 6e case ou plus ne peut jamais pénétrer la première case d'une montée :
  arrêt juste avant, sur la dernière file libre.
- Un coureur sur une montée ne donne NI ne reçoit l'aspiration.

Descente (bords bleus) :
- Un coureur qui PART d'une descente avance d'au minimum 5 cases.
- L'aspiration s'y applique normalement.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, TileType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game  # noqa: E402


def make_track(tile_types):
    track = Track()
    for t in tile_types:
        track.add_tile(t)
    return track


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


# Piste de test : cases 0-1 START, 2-9 STRAIGHT, 10-13 UPHILL, 14-19 STRAIGHT
MOUNTAIN_TRACK = ([TileType.START] + [TileType.STRAIGHT] * 4
                  + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 3)
# Piste de descente : cases 0-1 START, 2-7 DOWNHILL, 8-19 STRAIGHT
DOWNHILL_TRACK = ([TileType.START] + [TileType.DOWNHILL] * 3 + [TileType.STRAIGHT] * 6)


class TestAscentMovement(unittest.TestCase):
    def setUp(self):
        self.track = make_track(MOUNTAIN_TRACK)

    def test_ascent_caps_movement_at_5(self):
        """Carte 8 dont le trajet touche la montée (cases 10-13) -> 5 cases."""
        r = place(self.track, make_runner('r'), 6, 0)
        self.track.move_runner(r, 8)   # cible 14 : traverse la montée
        self.assertEqual(r.x, 11)      # 6 + 5, plafonné

    def test_rider_starting_on_ascent_is_capped(self):
        """Partir D'UNE montée plafonne aussi à 5 (départ compris)."""
        r = place(self.track, make_runner('r'), 10, 0)
        self.track.move_runner(r, 7)
        self.assertEqual(r.x, 15)

    def test_no_cap_when_ascent_not_on_path(self):
        """La montée n'est pas sur le trajet -> déplacement normal."""
        r = place(self.track, make_runner('r'), 0, 0)
        self.track.move_runner(r, 6)   # s'arrête case 6, avant la montée
        self.assertEqual(r.x, 6)

    def test_sixth_move_cannot_enter_ascent(self):
        """La 6e case ne peut pas pénétrer la montée : arrêt juste avant."""
        r = place(self.track, make_runner('r'), 4, 0)
        self.track.move_runner(r, 8)   # la case 10 (montée) serait la 6e
        self.assertEqual(r.x, 9)       # 4 + 5 : dernière case avant la montée

    def test_card_below_5_crossing_ascent_is_unchanged(self):
        r = place(self.track, make_runner('r'), 8, 0)
        self.track.move_runner(r, 3)   # traverse la fin de montée, carte 3
        self.assertEqual(r.x, 11)


class TestDescentMovement(unittest.TestCase):
    def setUp(self):
        self.track = make_track(DOWNHILL_TRACK)

    def test_descent_gives_minimum_5(self):
        """Partir d'une descente : carte 2 vaut au minimum 5."""
        r = place(self.track, make_runner('r'), 2, 0)
        self.track.move_runner(r, 2)
        self.assertEqual(r.x, 7)

    def test_descent_does_not_cap_high_cards(self):
        r = place(self.track, make_runner('r'), 2, 0)
        self.track.move_runner(r, 7)
        self.assertEqual(r.x, 9)

    def test_descent_only_from_descent_start(self):
        """Le minimum 5 ne s'applique qu'en PARTANT d'une descente."""
        r = place(self.track, make_runner('r'), 8, 0)  # droite, hors descente
        self.track.move_runner(r, 2)
        self.assertEqual(r.x, 10)

    def test_descent_then_ascent_caps_back_to_5(self):
        """Descente (min 5) puis montée sur le trajet -> plafonné à 5."""
        track = make_track([TileType.START] + [TileType.DOWNHILL] * 2
                           + [TileType.STRAIGHT] * 2 + [TileType.UPHILL] * 2
                           + [TileType.STRAIGHT] * 4)
        r = place(track, make_runner('r'), 2, 0)   # descente (cases 2-5)
        track.move_runner(r, 2)                    # min 5 -> cible 7, mais montée 10-13
        self.assertEqual(r.x, 7)                   # 5 cases, pas de montée touchée


class TestAscentSlipstream(unittest.TestCase):
    def test_rider_on_ascent_cannot_receive(self):
        """Un coureur SUR une montée ne reçoit pas l'aspiration."""
        track = make_track(MOUNTAIN_TRACK)
        rear = place(track, make_runner('rear'), 10, 0)  # sur la montée
        place(track, make_runner('front'), 12, 0)       # sur la montée aussi
        # placer un coureur devant avec exactement une case vide
        place(track, make_runner('ahead'), 14, 0)
        steps = run_aspiration(track)
        # le pack arrière (10,12) est entièrement en montée : aucun mouvement
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertNotIn('rear', moved_ids)

    def test_rider_on_ascent_cannot_give(self):
        """Le donneur (le plus en arrière du pack de devant) est en montée :
        le pack derrière n'aspire pas."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        # montée = cases 8-11
        place(track, make_runner('rear'), 5, 0)
        place(track, make_runner('giver'), 8, 0)    # première case de montée
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertNotIn('rear', moved_ids)
        self.assertNotIn('giver', moved_ids)

    def test_descent_slipstream_is_normal(self):
        """L'exemple du rulebook : en descente, l'aspiration s'applique
        normalement."""
        track = make_track(DOWNHILL_TRACK)
        rear = place(track, make_runner('rear'), 2, 0)   # descente
        place(track, make_runner('front'), 4, 0)          # descente
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertIn('rear', moved_ids)

    def test_ascent_gap_square_does_not_block(self):
        """Ce sont les COUREURS sur la montée qui bloquent, pas la case vide
        intermédiaire située en montée."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 2
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 5)
        # montée = cases 6-9 ; le coureur arrière en 3 (plaine), case vide 4
        # (plaine), donneur en 5 (plaine) : aspiration normale malgré la
        # montée plus loin
        rear = place(track, make_runner('rear'), 3, 0)
        place(track, make_runner('giver'), 5, 0)
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertIn('rear', moved_ids)
        self.assertEqual(rear.x, 4)


    def test_pack_splits_on_ascent_during_slipstream(self):
        """Exemple officiel (page Dized "Ascents") : dans un pack qui aspire,
        le coureur hors montée en tête glisse et FUSIONNE avec le pack de
        devant, tandis que le coéquipier en montée est laissé sur place
        ("left behind, even though he is in the same pack") — ceux derrière
        lui sont bloqués."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] + [TileType.STRAIGHT] * 2)
        # cases : 0-1 START, 2-7 STRAIGHT, 8-9 UPHILL, 10-13 STRAIGHT
        sprinteur = place(track, make_runner('sprinteur'), 10, 0)  # plaine, tête du pack
        rouleur = place(track, make_runner('rouleur'), 9, 0)       # MONTÉE (8-9)
        place(track, make_runner('giver'), 12, 0)                  # plaine, gap en 11
        steps = run_aspiration(track)
        moved_ids = {m[0].id for step in steps for m in step}
        self.assertEqual(sprinteur.x, 11)   # parti fusionner avec le giver
        self.assertEqual(rouleur.x, 9)       # laissé sur place, en montée
        self.assertIn('sprinteur', moved_ids)
        self.assertNotIn('rouleur', moved_ids)

    def test_ascent_rider_blocks_packmates_behind(self):
        """Un coureur en montée au MILIEU d'un pack bloque ceux derrière lui :
        seul le segment de tête (hors montée) glisse."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 2
                           + [TileType.UPHILL] + [TileType.STRAIGHT] * 3)
        # cases : 0-1 START, 2-5 STRAIGHT, 6-7 UPHILL, 8-13 STRAIGHT
        front = place(track, make_runner('front'), 8, 0)    # plaine, tête
        frozen = place(track, make_runner('frozen'), 7, 0)  # MONTÉE (6-7)
        rear = place(track, make_runner('rear'), 6, 0)      # MONTÉE (6-7)
        place(track, make_runner('giver'), 10, 0)           # gap en 9
        run_aspiration(track)
        self.assertEqual(front.x, 9)   # glisse
        self.assertEqual(frozen.x, 7)  # reste
        self.assertEqual(rear.x, 6)    # bloqué derrière


    def test_card_reaching_ascent_at_7th_square_stops_before(self):
        """Règle officielle ("si un coureur se déplace d'au moins 5 cases
        avant d'entrer dans la montée, il stoppe son mouvement sur la
        dernière file libre avant la montée") : un 7 à 7 cases de la montée
        entrerait à la 7e case -> arrêt JUSTE AVANT la montée (6 cases de
        plaine), pas à 5 cases."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        # cases 0-1 START, 2-7 STRAIGHT, 8-9 UPHILL
        r = place(track, make_runner('r'), 1, 0)   # montée à 7 cases (case 8)
        track.move_runner(r, 7)
        self.assertEqual(r.x, 7)  # 1 + 6 : dernière case libre avant la montée

    def test_card_reaching_ascent_at_8th_square_stops_before(self):
        """Un 8 dont la montée est à 8 cases : arrêt à 7 cases de plaine,
        juste devant la montée."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 4
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        # cases 0-1 START, 2-9 STRAIGHT, 10-11 UPHILL
        r = place(track, make_runner('r'), 2, 0)   # montée à 8 cases (case 10)
        track.move_runner(r, 8)
        self.assertEqual(r.x, 9)  # 2 + 7 : juste avant la montée

    def test_6th_move_into_ascent_stops_at_5(self):
        """Cas frontière : depuis la case 4, la montée (cases 8-9) est à
        4 cases -> entrée dans les 5 premières -> plafonné à 5 (la montée
        est traversée)."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        # cases 0-1 START, 2-7 STRAIGHT, 8-9 UPHILL
        r = place(track, make_runner('r'), 4, 0)   # montée à 4 cases (d=4)
        track.move_runner(r, 8)
        self.assertEqual(r.x, 9)  # 4 + 5 : traverse la montée, plafonné

    def test_card_stopping_before_ascent_is_not_capped(self):
        """Un 6 depuis la même position ne touche pas la montée (cible 7,
        plaine) : PAS de plafond, le coureur s'arrête juste devant."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        r = place(track, make_runner('r'), 1, 0)
        track.move_runner(r, 6)
        self.assertEqual(r.x, 7)  # 1 + 6 : trajet hors montée, pas de plafond

    def test_climbing_from_the_foot_of_the_ascent(self):
        """Au pied de la montée (case adjacente), un 5 traverse et sort de
        la montée : entrer dans la montée dans les 5 premières cases est
        parfaitement légal."""
        track = make_track([TileType.START] + [TileType.STRAIGHT] * 3
                           + [TileType.UPHILL] * 2 + [TileType.STRAIGHT] * 4)
        r = place(track, make_runner('r'), 7, 0)   # juste avant la montée (8-9)
        track.move_runner(r, 5)
        self.assertEqual(r.x, 12)  # traverse la montée, 5 cases au total


class TestCircuitStage(unittest.TestCase):
    def test_circuit_contains_mountains(self):
        from game.track import TileType
        game = Game(stage="circuit", player_count=2)
        tiles = [t.type for t in game.track.tiles]
        self.assertIn(TileType.UPHILL, tiles)
        self.assertIn(TileType.DOWNHILL, tiles)
        self.assertIn(TileType.SHARP_TURN, tiles)
        self.assertEqual(game.track.length, 60)


if __name__ == '__main__':
    unittest.main(verbosity=2)
