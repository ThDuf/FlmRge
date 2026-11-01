"""Vérification par invariants des règles montée/descente sur parties aléatoires.

Pour chaque mouvement :
- si le coureur PART d'une descente : déplacement effectif = max(carte, 5),
  sauf si bloqué par des cases pleines
- MONTÉE (règle officielle complète) :
  * entrée dans la montée dans les 5 premières cases (ou départ en
    montée) : déplacement plafonné à 5
  * entrée à la 6e case ou plus : arrêt sur la dernière file libre
    AVANT la montée (le déplacement peut atteindre d-1 cases de plaine)
- sinon : déplacement = valeur de la carte, sauf blocage
- aspiration : aucun coureur partant d'une montée ne bouge
"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game
from game.track import Terrain

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

def first_ascent_distance(start, card_v):
    """Distance d à la première case de montée sur le trajet de la carte
    (d=0 si départ en montée), ou None si le trajet n'en touche pas."""
    target = min(start + card_v, track.length - 1)
    for d, c in enumerate(range(start, target + 1)):
        if track.terrain_at(c) == Terrain.UPHILL:
            return d
    return None

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
        d = first_ascent_distance(start, card_v)
        on_descent = track.terrain_at(start) == Terrain.DOWNHILL

        # Déplacement attendu selon les règles (indépendant du plafond final)
        expected = max(card_v, 5) if on_descent else card_v
        if d is not None:
            if d <= 5:
                expected = min(expected, 5)      # entre dans les 5 premières cases
            else:
                expected = min(expected, d - 1)  # arrêt avant la montée

        assert eff <= expected, (
            f"T{turn} {rid}: {eff} cases > attendu {expected} (carte {card_v}, d={d})")
        if eff < expected:
            check_blocking(start, after[rid][0], min(start + expected, track.length - 1))
        checked += 1

    # aspiration : appliquer puis vérifier qu'aucun coureur sur une montée n'a bougé
    steps = game.resolve_aspiration_phase()
    for step in steps:
        for runner, fx, fl, tx, tl in step:
            assert track.terrain_at(fx) != Terrain.UPHILL, (
                f"T{turn} {runner.id} a reçu de l'aspiration en partant d'une montée")
    game.apply_aspiration_steps(steps)
    game._assign_fatigue_cards()
    if game._check_win_condition():
        break
    game._cleanup_hands()
    game.start_turn()

print(f"{checked} mouvements vérifiés : invariants montée/descente OK")
