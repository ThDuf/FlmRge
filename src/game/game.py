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
        self.current_player_index: int = 0
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
                fatigue_deck=[],  # Les decks Fatigue sont gérés séparément
            )
            roller = Runner(
                id=f"roller_{i}",
                type=RunnerType.ROLLER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.ROLLER),
                fatigue_deck=[],  # Les decks Fatigue sont gérés séparément
            )
            player = Player(id=f"player_{i}", color=color, sprinter=sprinter, roller=roller)
            self.players.append(player)

            # Placer les coureurs au départ
            # Sprinter sur file A (lane 0), Rouleur sur file B (lane 1)
            self._place_runner_at_start(sprinter, lane=0)
            self._place_runner_at_start(roller, lane=1)

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

    def _generate_fatigue_deck(self, runner_type: RunnerType) -> List[Card]:
        """Génère un deck Fatigue de 10 cartes pour un coureur.
        
        Règles officielles : 10 cartes Fatigue par type (toutes valent 2)
        """
        runner_str = "S" if runner_type == RunnerType.SPRINTER else "R"
        return [Card(2, CardType.FATIGUE, runner_str) for _ in range(10)]

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

        return track

    def _place_runner_at_start(self, runner: Runner, lane: int = 0) -> None:
        """Place un coureur à la ligne de départ.
        
        Args:
            runner: Le coureur à placer
            lane: 0 pour file A (sprinter), 1 pour file B (roller)
        """
        start_cell = self.track.get_cell(0, lane)
        if start_cell:
            start_cell.set_runner(runner, lane)

    def start_turn(self) -> None:
        """Démarre un nouveau tour."""
        self.turn_count += 1
        self.current_phase = Phase.ENERGY
        self.cards_played_this_turn = 0
        self.total_cards_to_play = len(self.players) * 2

        for player in self.players:
            for runner in player.get_runners():
                self.cards_played_per_runner[runner.id] = 0
            player.draw_cards_for_all(4)

    def play_card(self, player: Player, runner: Runner, card: Card) -> bool:
        """Joue une carte pour un coureur."""
        if self.current_phase != Phase.ENERGY:
            return False
        if card not in runner.hand:
            return False
        if self.cards_played_per_runner[runner.id] >= 1:
            print(f"⚠️ {runner.id} a déjà joué sa carte ce tour !")
            return False

        runner.play_card(card)
        self.cards_played_per_runner[runner.id] = 1
        self.cards_played_this_turn += 1
        return True

    def all_players_ready(self) -> bool:
        """Vérifie si chaque joueur a joué 2 cartes (1 par coureur)."""
        return self.cards_played_this_turn >= self.total_cards_to_play

    def resolve_movement_phase(self) -> None:
        """
        Résout la phase de mouvement selon les règles officielles.

        Règle : on déplace d'abord le coureur le plus en avant ; à égalité
        de position, la file A (file de droite, double ligne) est
        considérée en tête et bouge en premier.
        """
        if self.current_phase != Phase.ENERGY:
            return

        self.current_phase = Phase.MOVEMENT
        print("\n--- PHASE DE MOUVEMENT ---")

        # Récupérer tous les coureurs triés du plus proche au plus loin de l'arrivée
        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        all_runners.sort(key=lambda r: (-r.x, r.y))

        print(f"Ordre de déplacement (du plus proche au plus loin) : {[r.id for r in all_runners]}")

        # Déplacer les coureurs un par un
        for runner in all_runners:
            if runner.played_card is not None:
                card = runner.played_card
                print(f"  {runner.id} (pos {runner.x}) joue carte {card.value}")
                self.track.move_runner(runner, card.value)
                print(f"    -> Déplacé à {runner.x}, file {runner.y}")

        print("--- Fin de la phase de mouvement ---\n")

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

    def resolve_terminal_phase(self) -> None:
        """
        Résout la phase terminale selon les règles officielles.
        
        1. Retirer les cartes jouées (déjà fait)
        2. Appliquer la fatigue
        3. Vérifier la victoire
        """
        if self.current_phase != Phase.ASPIRATION:
            return

        print("\n--- PHASE TERMINALE ---")

        # 1. Attribuer les cartes Fatigue
        print("Vérification de la fatigue...")
        self._assign_fatigue_cards()

        # 2. Vérifier la condition de victoire
        if self._check_win_condition():
            self.game_over = True
            print(f"\nVICTOIRE : {self.winner.color} a gagné !\n")
        else:
            # 3. Préparer le prochain tour
            print("Préparation du prochain tour...")
            self._cleanup_hands()
            self.start_turn()

        print("--- Fin de la phase terminale ---\n")

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

    def get_current_player(self) -> Player:
        """Retourne le joueur actuel."""
        return self.players[self.current_player_index]

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
