"""Simulation complète de parties headless (vérification bout-en-bout).

Suit le flux officiel : énergie -> mouvement -> aspiration (appliquée)
-> fatigue -> fin de tour. Vérifie la cohérence du plateau à chaque phase
et l'épuisement progressif des decks (cartes jouées retirées du jeu).
"""
import os, sys, random
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game

def consistency(game):
    seen = set()
    for x, y, r in game.track.get_all_runners():
        assert r.id not in seen, f"{r.id} dupliqué"
        seen.add(r.id)
        assert (r.x, r.y) == (x, y), f"{r.id} désynchronisé"

def deck_sizes(game):
    return [len(r.energy_deck) + len(r.discard_pile) + len(r.hand) + (1 if r.played_card else 0)
            for p in game.players for r in p.get_runners()]

def play_game(seed):
    random.seed(seed)
    game = Game(stage="test", player_count=2)
    initial = deck_sizes(game)
    for turn in range(60):
        assert game.current_phase.name == "ENERGY"
        for player in game.players:
            for runner in player.get_runners():
                card = random.choice(runner.hand)
                assert game.play_card(player, runner, card)
        assert game.all_players_ready()
        game.resolve_movement_phase()
        consistency(game)
        steps = game.resolve_aspiration_phase()
        game.apply_aspiration_steps(steps)
        consistency(game)
        game._assign_fatigue_cards()
        consistency(game)
        if game._check_win_condition():
            game.game_over = True
            return game.turn_count, game.winner.color, len(steps), deck_sizes(game), initial
        game._cleanup_hands()
        game.start_turn()
    raise AssertionError("partie sans fin après 60 tours")

for seed in range(20):
    turns, color, asp, final_decks, initial = play_game(seed)
    depleted = [i - f for i, f in zip(initial, final_decks)]
    print(f"seed {seed:2d}: victoire {color} en {turns} tours "
          f"({asp} étapes d'aspiration au dernier tour, decks -{depleted[0]}/-{depleted[1]} cartes)")
print("20 parties simulées OK")
