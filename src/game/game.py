import random
from typing import List, Optional, Dict
from enum import Enum, auto
from .player import Player
from .runner import Runner, RunnerType
from .card import Card, CardType
from .track import Track, TileType


class Phase(Enum):
    ENERGY = auto()    # Phase d'Énergie
    MOVEMENT = auto()  # Phase de Mouvement
    ASPIRATION = auto()  # Phase d'Aspiration
    TERMINAL = auto()  # Phase Terminale


class Game:
    """Moteur principal du jeu Flamme Rouge."""

    def __init__(self, stage: str = "Avenue Corso Paseo", player_count: int = 2):
        self.stage = stage
        self.players: List[Player] = []
        self.track = self._build_track(stage)
        self.current_phase: Phase = Phase.ENERGY
        self.turn_count: int = 0
        self.game_over: bool = False
        self.winner: Optional[Player] = None
        self.cards_played_this_turn = 0
        self.total_cards_to_play = 0
        self.cards_played_per_runner = {}

        # Initialiser les joueurs
        self._initialize_players(player_count)
        
        # Initialiser le compteur de cartes par coureur
        for player in self.players:
            for runner in player.get_runners():
                self.cards_played_per_runner[runner.id] = 0

        # Démarrer le premier tour
        self.start_turn()

    def _initialize_players(self, count: int) -> None:
        """Initialise les joueurs et leurs coureurs."""
        colors = ["red", "blue", "green", "yellow"][:count]
        for i, color in enumerate(colors):
            sprinter = Runner(
                id=f"sprinter_{i}",
                type=RunnerType.SPRINTER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.SPRINTER),
            )
            roller = Runner(
                id=f"roller_{i}",
                type=RunnerType.ROLLER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.ROLLER),
            )
            player = Player(id=f"player_{i}", color=color, sprinter=sprinter, roller=roller)
            self.players.append(player)

        # Placement au départ en round-robin pour l'équité : tous les
        # sprinteurs d'abord (à la première file libre), puis tous les
        # rouleurs. Les équipes démarrent ainsi sur des cases équivalentes.
        for player in self.players:
            self._place_runner_at_start(player.sprinter)
        for player in self.players:
            self._place_runner_at_start(player.roller)

    def _generate_energy_deck(self, runner_type: RunnerType) -> List[Card]:
        """Génère un deck Énergie de 15 cartes pour un coureur.
        
        Règles officielles :
        - Sprinteur : 15 cartes (2,2,3,3,4,4,5,5,6,6,6,7,7,7,8)
        - Rouleur : 15 cartes (2,2,2,3,3,3,4,4,4,5,5,5,6,6,7)
        """
        if runner_type == RunnerType.SPRINTER:
            # Deck officiel Sprinteur : 15 cartes
            values = [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 6, 7, 7, 7, 8]
            runner_str = "S"
        else:
            # Deck officiel Rouleur : 15 cartes
            values = [2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 7]
            runner_str = "R"

        random.shuffle(values)
        return [Card(value, CardType.ENERGY, runner_str) for value in values]

    def _build_track(self, stage: str) -> Track:
        """Construit la piste selon l'étape choisie."""
        track = Track()

        if stage == "Avenue Corso Paseo":
            track.add_tile(TileType.START)
            for _ in range(10):
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.FINISH)
        elif stage == "test":
            track.add_tile(TileType.START)
            for _ in range(13):
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.FINISH)
        elif stage == "circuit":
            # Circuit "organique" avec montées et descentes :
            # rangées de 16 cases (14 droites + un virage à 180° = 2 cases),
            # rendues comme de VRAIS virages par l'UI (cases contiguës).
            # 3 rangées pleines + rangée finale : 30 tuiles = 60 cases.
            track.add_tile(TileType.START)
            for _ in range(4):          # rangée 1
                track.add_tile(TileType.STRAIGHT)
            for _ in range(2):          # montée (cases 10 à 13)
                track.add_tile(TileType.UPHILL)
            track.add_tile(TileType.SHARP_TURN)
            for _ in range(2):          # rangée 2
                track.add_tile(TileType.STRAIGHT)
            for _ in range(3):          # descente (cases 18 à 23)
                track.add_tile(TileType.DOWNHILL)
            for _ in range(2):
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.SHARP_TURN)
            for _ in range(7):          # rangée 3
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.SHARP_TURN)
            for _ in range(5):          # rangée finale (pas de virage avant l'arrivée)
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.FINISH)

        return track

    def _place_runner_at_start(self, runner: Runner) -> None:
        """Place un coureur au départ dans la première file libre.

        Règle officielle : les coureurs sont placés derrière la ligne de
        départ dans n'importe quelle file libre. On remplit ici la
        première file libre (A puis B) à partir de la case 0.

        IMPORTANT : ne jamais laisser un coureur hors piste — un coureur
        non placé devient un « fantôme » dont le premier mouvement retirerait
        un autre coureur de sa case.
        """
        for x in range(self.track.length):
            for lane in (0, 1):
                cell = self.track.get_cell(x, lane)
                if cell and cell.is_empty(lane):
                    cell.set_runner(runner, lane)
                    return
        raise RuntimeError(f"Placement impossible : {runner.id} (zone de départ pleine)")

    def start_turn(self) -> None:
        """Démarre un nouveau tour."""
        self.turn_count += 1
        self.current_phase = Phase.ENERGY
        self.cards_played_this_turn = 0
        self.total_cards_to_play = 0

        for player in self.players:
            player.draw_cards_for_all(4)
            for runner in player.get_runners():
                if runner.hand:
                    self.cards_played_per_runner[runner.id] = 0
                    self.total_cards_to_play += 1
                else:
                    # Cas limite : plus aucune carte nulle part (deck et
                    # défausse vides). Le coureur est marqué comme ayant
                    # déjà joué (il n'avance pas ce tour), sinon la partie
                    # se bloquerait sans jamais être "prête".
                    self.cards_played_per_runner[runner.id] = 1

    def play_card(self, player: Player, runner: Runner, card: Card) -> bool:
        """Joue une carte pour un coureur."""
        if self.current_phase != Phase.ENERGY:
            return False
        if card not in runner.hand:
            return False
        if self.cards_played_per_runner[runner.id] >= 1:
            print(f"[ATTENTION] {runner.id} a deja joue sa carte ce tour !")
            return False

        runner.play_card(card)
        self.cards_played_per_runner[runner.id] = 1
        self.cards_played_this_turn += 1
        return True

    def all_players_ready(self) -> bool:
        """Vérifie si chaque joueur a joué 2 cartes (1 par coureur)."""
        return self.cards_played_this_turn >= self.total_cards_to_play

    def resolve_movement_phase(self) -> List:
        """
        Calcule l'ordre des mouvements de la phase de mouvement SANS les
        appliquer.

        Règle officielle : on déplace d'abord le coureur le plus en
        avant ; à égalité de position, la file A (file de droite,
        double ligne) est considérée en tête et bouge en premier.

        Retourne la liste [(runner, valeur_de_carte), ...], à appliquer
        un par un via apply_movement_step(). La destination de chaque
        coureur n'est calculée qu'au moment de SON déplacement, pour
        tenir compte des coureurs déplacés avant lui (arrêts derrière
        une case pleine, etc.).
        """
        if self.current_phase != Phase.ENERGY:
            return []

        self.current_phase = Phase.MOVEMENT
        print("\n--- PHASE DE MOUVEMENT ---")

        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        all_runners.sort(key=lambda r: (-r.x, r.y))

        moves = [(runner, runner.played_card.value)
                 for runner in all_runners if runner.played_card is not None]

        print(f"Ordre de déplacement (du plus proche au plus loin) : "
              f"{[r.id for r, _v in moves]}")
        print(f"--- Fin du calcul du mouvement ({len(moves)} coureurs) ---\n")
        return moves

    def apply_movement_step(self, move) -> None:
        """Applique UN mouvement de coureur (pour le pas-à-pas UI)."""
        runner, value = move
        print(f"  {runner.id} (pos {runner.x}) joue carte {value}")
        self.track.move_runner(runner, value)
        print(f"    -> Déplacé à {runner.x}, file {runner.y}")

    def apply_movement_steps(self, moves: List) -> None:
        """Applique tous les mouvements (usage headless)."""
        for move in moves:
            self.apply_movement_step(move)

    def resolve_aspiration_phase(self) -> List:
        """
        Calcule les mouvements d'aspiration SANS les appliquer.

        Règle officielle : "Si exactement une case vide sépare deux packs,
        le pack arrière avance d'une case pour fusionner avec celui de
        devant. Puis on revérifie le pack fusionné (un coureur peut aspirer
        plusieurs fois dans le même tour)."

        Retourne la liste des étapes (une étape = les mouvements d'un pack),
        à appliquer via Game.apply_slipstream_step() ou
        Game.apply_aspiration_steps().
        """
        if self.current_phase != Phase.MOVEMENT:
            return []

        self.current_phase = Phase.ASPIRATION
        print("\n--- PHASE D'ASPIRATION ---")

        groups = self.track.get_groups()
        print(f"Packs avant aspiration : {len(groups)} packs")
        for i, group in enumerate(groups):
            positions = [r.x for r in group]
            print(f"  Pack {i}: coureurs à positions {positions}")

        steps = self.track.compute_slipstream_steps()

        for i, step in enumerate(steps):
            desc = ", ".join(f"{r.id} {fx},{fl}->{tx},{tl}" for r, fx, fl, tx, tl in step)
            print(f"  Etape {i + 1}: {desc}")

        print(f"--- Fin du calcul d'aspiration ({len(steps)} étapes) ---\n")
        return steps

    def apply_slipstream_step(self, step) -> None:
        """Applique UNE étape d'aspiration sur le plateau (pour le pas-à-pas UI)."""
        self.track.apply_slipstream_step(step)

    def apply_aspiration_steps(self, steps: List) -> None:
        """Applique toutes les étapes d'aspiration (usage headless)."""
        for step in steps:
            self.track.apply_slipstream_step(step)

    def _assign_fatigue_cards(self) -> None:
        """
        Attribue les cartes Fatigue selon les règles officielles.

        Règle : "Un coureur est fatigué si la CASE devant lui est vide"
        (les 2 files vides). Une simple file libre devant lui ne suffit
        PAS — dans une vraie course, le pack roule au milieu de la route.
        Chaque coureur dans cette situation reçoit une carte Fatigue
        (valeur 2), recyclée dans son deck.
        """
        for player in self.players:
            for runner in player.get_runners():
                if self.track.is_square_empty(runner.x + 1):
                    fatigue_card = Card(2, CardType.FATIGUE,
                                        "S" if runner.type == RunnerType.SPRINTER else "R")
                    runner.discard_pile.append(fatigue_card)
                    print(f"  {runner.id} est fatigué (case devant vide) -> carte Fatigue (valeur 2)")

    def _cleanup_hands(self) -> None:
        """Nettoie les mains des coureurs pour le prochain tour.

        Règles officielles : les cartes non jouées sont recyclées, la
        carte jouée est RETIRÉE DU JEU (le deck s'épuise au fil de la
        course). Le remélange des cartes recyclées se fait à la pioche
        quand le deck est vide (cf. Runner.draw_cards).
        """
        for player in self.players:
            for runner in player.get_runners():
                runner.reset_hand()

    def _check_win_condition(self) -> bool:
        """Vérifie si un coureur a franchi la ligne d'arrivée.

        Règle officielle : si plusieurs coureurs franchissent la ligne dans
        le même tour, le plus loin devant gagne ; à égalité, la file A
        (file de droite) est considérée en tête.
        """
        finish_x = self.track.length - 1
        best = None
        for player in self.players:
            for runner in player.get_runners():
                if runner.x >= finish_x:
                    key = (runner.x, -runner.y)  # plus loin devant, puis file A
                    if best is None or key > best[0]:
                        best = (key, player, runner)
        if best is not None:
            self.winner = best[1]
            return True
        return False

    def get_current_phase_name(self) -> str:
        """Retourne le nom de la phase actuelle."""
        return self.current_phase.name

    def get_state(self) -> Dict:
        """Retourne l'état actuel du jeu."""
        return {
            "turn": self.turn_count,
            "phase": self.current_phase.name,
            "players": [
                {
                    "id": player.id,
                    "color": player.color,
                    "sprinter": {
                        "x": player.sprinter.x,
                        "y": player.sprinter.y,
                        "hand": [card.value for card in player.sprinter.hand],
                        "discard": [card.value for card in player.sprinter.discard_pile],
                    },
                    "roller": {
                        "x": player.roller.x,
                        "y": player.roller.y,
                        "hand": [card.value for card in player.roller.hand],
                        "discard": [card.value for card in player.roller.discard_pile],
                    },
                }
                for player in self.players
            ],
            "track_length": self.track.length,
            "game_over": self.game_over,
            "winner": self.winner.id if self.winner else None,
        }
