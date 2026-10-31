"""Vérification par invariants des règles montée/descente sur parties aléatoires.

Pour chaque mouvement :
- si le trajet (départ compris, d'après la carte) touche une montée :
  le déplacement effectif ne doit PAS dépasser 5 cases
- si le coureur PART d'une descente : déplacement effectif = max(carte, 5),
  sauf si bloqué par des cases pleines (toutes les cases entre l'arrêt
  et la cible doivent alors être pleines)
- sinon : déplacement effectif = valeur de la carte, sauf blocage
"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game
from game.track import TileType

random.seed(42)
game = Game(stage="circuit", player_count=2)
track = game.track

def check_blocking(start, stop, target_x):
    """Le coureur s'est arrêté à `stop` au lieu de `target_x` : toutes les
    cases entre stop+1 et target_x doivent être pleines (2 files)."""
    for c in range(stop + 1, target_x + 1):
        cell = track.get_cell(c, 0)
        assert cell is not None and cell.is_full(), (
            f"arrêt injustifié à {stop} au lieu de {target_x} (case {c} non pleine)")

checked = 0
for turn in range(10):
    for player in game.players:
        for runner in player.get_runners():
            card = random.choice(runner.hand)
            assert game.play_card(player, runner, card)
    planned = game.resolve_movement_phase()
    before = {r.id: (r.x, r.y) for p in game.players for r in p.get_runners()}
    cards = {r.id: v for r, v in planned}
    game.apply_movement_steps(planned)
    after = {r.id: (r.x, r.y) for p in game.players for r in p.get_runners()}

    for rid, card_v in cards.items():
        start = before[rid][0]
        eff = after[rid][0] - start
        target_unc = min(start + card_v, track.length - 1)
        touches_ascent = any(track.tile_type_at(c) == TileType.UPHILL
                             for c in range(start, target_unc + 1))
        on_descent = track.tile_type_at(start) == TileType.DOWNHILL

        if touches_ascent:
            assert eff <= 5, f"T{turn} {rid}: {eff} cases (>5) avec montée sur le trajet"
            expected = min(card_v, 5)
            if eff < expected:
                check_blocking(start, after[rid][0], min(start + expected, track.length - 1))
        elif on_descent:
            expected = max(card_v, 5)
            target = min(start + expected, track.length - 1)
            assert eff <= expected, f"T{turn} {rid}: {eff} > {expected} (descente)"
            if eff < expected:
                check_blocking(start, after[rid][0], target)
        else:
            target = min(start + card_v, track.length - 1)
            if eff < card_v:
                check_blocking(start, after[rid][0], target)
        checked += 1

    # aspiration : appliquer puis vérifier qu'aucun coureur sur une montée n'a bougé
    steps = game.resolve_aspiration_phase()
    on_ascent_before = {rid: track.tile_type_at(pos[0]) == TileType.UPHILL
                        for rid, pos in before.items()}
    for step in steps:
        for runner, fx, fl, tx, tl in step:
            assert track.tile_type_at(fx) != TileType.UPHILL, (
                f"T{turn} {runner.id} a reçu de l'aspiration en partant d'une montée")
    game.apply_aspiration_steps(steps)
    game._assign_fatigue_cards()
    if game._check_win_condition():
        break
    game._cleanup_hands()
    game.start_turn()

print(f"{checked} mouvements vérifiés : invariants montée/descente OK")
