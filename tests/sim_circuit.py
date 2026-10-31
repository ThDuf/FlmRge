"""Simulation complete d'une partie sur le circuit long (stage 'circuit')."""
import os, sys, random
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game

def consistency(game):
    seen = set()
    for x, y, r in game.track.get_all_runners():
        assert r.id not in seen, f"{r.id} duplique"
        seen.add(r.id)
        assert (r.x, r.y) == (x, y), f"{r.id} desynchronise"

random.seed(7)
game = Game(stage="circuit", player_count=2)
print(f"Circuit : {game.track.length} cases, {len(game.track.tiles)} tuiles")
for turn in range(80):
    for player in game.players:
        for runner in player.get_runners():
            card = random.choice(runner.hand)
            assert game.play_card(player, runner, card)
    game.apply_movement_steps(game.resolve_movement_phase())
    game.apply_aspiration_steps(game.resolve_aspiration_phase())
    consistency(game)
    game._assign_fatigue_cards()
    if game._check_win_condition():
        print(f"Victoire : {game.winner.color} en {game.turn_count} tours")
        break
    game._cleanup_hands()
    game.start_turn()
else:
    raise AssertionError("partie sans fin apres 80 tours")
consistency(game)
decks = [len(r.energy_deck) + len(r.discard_pile) + len(r.hand)
         for p in game.players for r in p.get_runners()]
print(f"Cartes restantes par coureur en fin de partie : {decks}")
print("Partie complete sur circuit OK")
