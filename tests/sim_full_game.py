"""Simulation complète de parties headless (vérification bout-en-bout)."""
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

def play_game(seed):
    random.seed(seed)
    game = Game(stage="test", player_count=2)
    for turn in range(60):
        assert game.current_phase.name == "ENERGY"
        for player in game.players:
            for runner in player.get_runners():
                card = random.choice(runner.hand)
                assert game.play_card(player, runner, card)
        assert game.all_players_ready()
        game.resolve_movement_phase()
        consistency(game)
        movements = game.resolve_aspiration_phase()
        consistency(game)
        game._assign_fatigue_cards()
        consistency(game)
        if game._check_win_condition():
            game.game_over = True
            return game.turn_count, game.winner.color, len(movements)
        game._cleanup_hands()
        game.start_turn()
    raise AssertionError("partie sans fin après 60 tours")

for seed in range(20):
    turns, color, asp = play_game(seed)
    print(f"seed {seed:2d}: victoire {color} en {turns} tours ({asp} aspirations au dernier tour)")
print("20 parties simulées OK")
