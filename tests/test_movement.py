"""Tests du mouvement et des decks selon les règles officielles Flamme Rouge.

Règles officielles (rulebook, Movement Phase) :
- On déplace d'abord le coureur le plus en avant ; à égalité, la file A
  (file de droite, double ligne) est en tête et bouge en premier.
- Un coureur TRAVERSE les autres coureurs ; il ne peut juste pas finir
  son mouvement sur une case entièrement occupée.
- Si la case d'arrivée est pleine : il s'arrête derrière, sur la première
  case offrant une file libre.
- Case d'arrivée vide -> placé dans la file A (droite).

Decks (règles officielles) :
- Les cartes jouées sont RETIRÉES DU JEU (le deck s'épuise).
- Les cartes non jouées sont recyclées ; le remélange se fait à la pioche.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, TileType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.card import Card, CardType  # noqa: E402
from game.game import Game, Phase  # noqa: E402


def make_track(min_cells):
    track = Track()
    while track.length < min_cells:
        track.add_tile(TileType.STRAIGHT)
    return track


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y):
    cell = track.get_cell(x, y)
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


class TestMovement(unittest.TestCase):
    def test_exact_move_on_empty_track(self):
        t = make_track(20)
        r = place(t, make_runner('r'), 2, 1)
        t.move_runner(r, 4)
        # case vide -> placé en file A (droite)
        self.assertEqual((r.x, r.y), (6, 0))

    def test_rider_moves_through_other_riders(self):
        """Un coureur TRAVERSE les coureurs : seule sa case d'arrivée compte."""
        t = make_track(20)
        r = place(t, make_runner('r'), 0, 0)
        place(t, make_runner('blocker_a'), 2, 0)
        place(t, make_runner('blocker_b'), 2, 1)  # case 2 pleine
        t.move_runner(r, 5)
        self.assertEqual((r.x, r.y), (5, 0))

    def test_blocked_landing_stops_behind(self):
        """Case d'arrivée pleine -> arrêt derrière, première case avec file libre."""
        t = make_track(20)
        r = place(t, make_runner('r'), 0, 0)
        place(t, make_runner('blocker_a'), 5, 0)
        place(t, make_runner('blocker_b'), 5, 1)  # case 5 pleine
        place(t, make_runner('half'), 4, 0)        # case 4 : file A occupée
        t.move_runner(r, 5)
        self.assertEqual((r.x, r.y), (4, 1))  # s'arrête sur la file B de la case 4

    def test_fully_blocked_rider_stays(self):
        """Toutes les cases devant pleines -> le coureur reste sur place."""
        t = make_track(20)
        r = place(t, make_runner('r'), 0, 0)
        for x in (1, 2):
            place(t, make_runner(f'ba_{x}'), x, 0)
            place(t, make_runner(f'bb_{x}'), x, 1)
        t.move_runner(r, 2)
        self.assertEqual((r.x, r.y), (0, 0))

    def test_move_capped_at_finish(self):
        t = make_track(8)  # cases 0..7
        r = place(t, make_runner('r'), 5, 0)
        t.move_runner(r, 5)
        self.assertEqual(r.x, 7)

    def test_frontmost_moves_first_lane_a_tiebreak(self):
        """À égalité de position, la file A (droite) est en tête et bouge en premier.
        Vérifié via la place finale : le coureur de la file A doit garder la file A."""
        game = Game(stage="test", player_count=2)
        track = game.track
        # Vider la piste
        for x, y, r in list(track.get_all_runners()):
            track.get_cell(x, y).remove_runner(y)
        ra = game.players[0].sprinter   # file A, même case
        rb = game.players[0].roller     # file B, même case
        place(track, ra, 3, 0)
        place(track, rb, 3, 1)
        ra.played_card = Card(3, CardType.ENERGY, "S")
        rb.played_card = Card(3, CardType.ENERGY, "R")
        game.current_phase = Phase.ENERGY
        game.apply_movement_steps(game.resolve_movement_phase())
        # Les deux arrivent sur la case 6 (vide au départ) :
        # le premier arrivé prend la file A, l'autre la file B.
        # La file A (ra) ayant bougé en premier, il doit être en file A.
        self.assertEqual((ra.x, ra.y), (6, 0))
        self.assertEqual((rb.x, rb.y), (6, 1))


class TestDecks(unittest.TestCase):
    def _total_cards(self, runner):
        return (len(runner.energy_deck) + len(runner.discard_pile)
                + len(runner.hand) + (1 if runner.played_card else 0))

    def test_played_card_removed_from_game(self):
        """Règle officielle : les cartes jouées quittent le jeu (deck s'épuisant)."""
        game = Game(stage="test", player_count=2)
        runner = game.players[0].sprinter
        self.assertEqual(self._total_cards(runner), 15)
        card = runner.hand[0]
        game.play_card(game.players[0], runner, card)
        self.assertIs(runner.played_card, card)
        self.assertEqual(self._total_cards(runner), 15)  # toujours dans le jeu
        game._cleanup_hands()
        self.assertEqual(self._total_cards(runner), 14)  # carte jouée retirée du jeu

    def test_unplayed_cards_are_recycled(self):
        game = Game(stage="test", player_count=2)
        runner = game.players[0].sprinter
        game.play_card(game.players[0], runner, runner.hand[0])
        game._cleanup_hands()
        # 4 piochées, 1 jouée (retirée), 3 recyclées
        self.assertEqual(len(runner.discard_pile), 3)
        self.assertEqual(len(runner.hand), 0)

    def test_draw_reshuffles_recycled_when_deck_empty(self):
        game = Game(stage="test", player_count=2)
        runner = game.players[0].sprinter
        runner.energy_deck = [Card(2, CardType.ENERGY, "S"), Card(3, CardType.ENERGY, "S")]
        runner.discard_pile = [Card(v, CardType.ENERGY, "S") for v in (4, 5, 6)]
        runner.hand = []
        drawn = runner.draw_cards(4)
        self.assertEqual(len(drawn), 4)
        self.assertEqual(len(runner.hand), 4)

    def test_draw_all_when_not_enough_cards(self):
        game = Game(stage="test", player_count=2)
        runner = game.players[0].sprinter
        runner.energy_deck = [Card(2, CardType.ENERGY, "S")]
        runner.discard_pile = []
        runner.hand = []
        drawn = runner.draw_cards(4)
        self.assertEqual(len(drawn), 1)


class TestStartPlacement(unittest.TestCase):
    """Régression : les coureurs des joueurs > 0 n'étaient PAS placés sur la
    piste (set_runner échouait silencieusement sur une case déjà occupée),
    devenant des « fantômes » dont le premier mouvement retirait un autre
    coureur de sa case."""

    def test_every_runner_is_on_the_track(self):
        for count in (2, 3, 4):
            game = Game(stage="test", player_count=count)
            expected = {r.id for p in game.players for r in p.get_runners()}
            on_track = {r.id for _x, _y, r in game.track.get_all_runners()}
            self.assertEqual(on_track, expected, msg=f"{count} joueurs")

    def test_placement_is_fair_between_teams(self):
        """Round-robin : les équipes démarrent sur des cases équivalentes."""
        game = Game(stage="test", player_count=2)
        p0, p1 = game.players
        self.assertEqual(p0.sprinter.x, p1.sprinter.x)
        self.assertEqual(p0.roller.x, p1.roller.x)

    def test_four_player_full_turn_consistency(self):
        """Un tour complet à 4 joueurs ne doit corrompre aucun état."""
        game = Game(stage="test", player_count=4)
        for player in game.players:
            for runner in player.get_runners():
                self.assertTrue(game.play_card(player, runner, runner.hand[0]))
        self.assertTrue(game.all_players_ready())
        game.apply_movement_steps(game.resolve_movement_phase())
        game.apply_aspiration_steps(game.resolve_aspiration_phase())
        game._assign_fatigue_cards()
        seen = set()
        for x, y, r in game.track.get_all_runners():
            self.assertNotIn(r.id, seen, f"{r.id} dupliqué")
            seen.add(r.id)
            self.assertEqual((r.x, r.y), (x, y))


class TestNoCardsEdgeCase(unittest.TestCase):
    def test_rider_without_any_cards_is_skipped(self):
        """Cas limite : un coureur sans plus aucune carte ne doit pas bloquer
        la partie (marqué comme ayant joué, il n'avance pas)."""
        game = Game(stage="test", player_count=2)
        runner = game.players[0].sprinter
        runner.energy_deck.clear()
        runner.discard_pile.clear()
        runner.hand.clear()
        game.start_turn()
        self.assertEqual(game.cards_played_per_runner[runner.id], 1)
        self.assertEqual(game.cards_played_per_runner[game.players[0].roller.id], 0)
        self.assertEqual(game.total_cards_to_play, 3)
        self.assertFalse(game.all_players_ready())


if __name__ == '__main__':
    unittest.main(verbosity=2)
