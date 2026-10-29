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
        self.cards_played_this_turn = 0  # Compteur de cartes jouées ce tour
        self.total_cards_to_play = 0     # Total de cartes à jouer (2 par joueur)
        self.cards_played_per_runner = {}  # {runner_id: nombre de cartes jouées}

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
                fatigue_deck=self._generate_fatigue_deck(),
            )
            roller = Runner(
                id=f"roller_{i}",
                type=RunnerType.ROLLER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.ROLLER),
                fatigue_deck=self._generate_fatigue_deck(),
            )
            player = Player(id=f"player_{i}", color=color, sprinter=sprinter, roller=roller)
            self.players.append(player)

            # Placer les coureurs au départ
            self._place_runner_at_start(sprinter)
            self._place_runner_at_start(roller)

    def _generate_energy_deck(self, runner_type: RunnerType) -> List[Card]:
        """Génère un deck Énergie pour un coureur."""
        # Distribution des cartes selon le type (simplifiée)
        # Sprinteur : plus de cartes à haute valeur (6-9)
        # Rouleur : plus de cartes à faible valeur (2-5)
        if runner_type == RunnerType.SPRINTER:
            values = [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 9, 9, 9]
        else:  # Rouleur
            values = [2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 7, 7, 8, 9]

        # Dupliquer pour avoir ~45 cartes (comme dans le jeu original)
        while len(values) < 45:
            values.extend(values[:10])
        values = values[:45]

        random.shuffle(values)
        return [Card(value, CardType.ENERGY) for value in values]

    def _generate_fatigue_deck(self) -> List[Card]:
        """Génère un deck Fatigue (toutes les cartes valent 2)."""
        return [Card(2, CardType.FATIGUE) for _ in range(10)]  # 10 cartes Fatigue

    def _build_track(self, stage: str) -> Track:
        """Construit la piste selon l'étape choisie."""
        track = Track()

        # Exemple pour "Avenue Corso Paseo" (setup: abcdefghijklmnopqrstu)
        # On va simplifier avec une piste droite pour commencer
        if stage == "Avenue Corso Paseo":
            # Départ
            track.add_tile(TileType.START)
            # Ligne droite (20 cases = 10 tuiles)
            for _ in range(10):
                track.add_tile(TileType.STRAIGHT)
            # Arrivée
            track.add_tile(TileType.FINISH)
        elif stage == "test":
            # Piste de test courte (5 tuiles = 10 cases)
            track.add_tile(TileType.START)
            for _ in range(3):
                track.add_tile(TileType.STRAIGHT)
            track.add_tile(TileType.FINISH)

        return track

    def _place_runner_at_start(self, runner: Runner) -> None:
        """Place un coureur à la ligne de départ."""
        # Trouver la première case après le départ
        start_cell = self.track.get_cell(0, 0)
        if start_cell and start_cell.is_empty(0):
            start_cell.set_runner(runner, 0)
        else:
            start_cell = self.track.get_cell(0, 1)
            if start_cell:
                start_cell.set_runner(runner, 1)

    def start_turn(self) -> None:
        """Démarre un nouveau tour."""
        self.turn_count += 1
        self.current_phase = Phase.ENERGY
        self.cards_played_this_turn = 0  # Réinitialiser le compteur
        self.total_cards_to_play = len(self.players) * 2  # 2 cartes par joueur (1 par coureur)

        # Réinitialiser le compteur de cartes par coureur
        for player in self.players:
            for runner in player.get_runners():
                self.cards_played_per_runner[runner.id] = 0
            player.draw_cards_for_all(4)  # Chaque coureur pioche 4 cartes

    def play_card(self, player: Player, runner: Runner, card: Card) -> bool:
        """
        Joue une carte pour un coureur.
        Retourne True si la carte a été jouée avec succès.
        """
        if self.current_phase != Phase.ENERGY:
            return False

        if card not in runner.hand:
            return False

        # VÉRIFICATION: Ce coureur n'a pas déjà joué sa carte ce tour
        if self.cards_played_per_runner[runner.id] >= 1:
            print(f"⚠️ {runner.id} a déjà joué sa carte ce tour !")
            return False

        runner.play_card(card)
        self.cards_played_per_runner[runner.id] = 1  # Marquer comme ayant joué
        self.cards_played_this_turn += 1  # Incrémenter le compteur
        return True

    def all_players_ready(self) -> bool:
        """Vérifie si tous les joueurs ont joué leurs 2 cartes (1 par coureur)."""
        return self.cards_played_this_turn >= self.total_cards_to_play

    def resolve_movement_phase(self) -> None:
        """Résout la phase de mouvement."""
        if self.current_phase != Phase.ENERGY:
            return

        self.current_phase = Phase.MOVEMENT

        # Récupérer tous les coureurs triés par position (du plus loin au plus proche)
        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        all_runners.sort(key=lambda r: r.x, reverse=True)  # Du + loin au + proche

        # Révéler les cartes et déplacer les coureurs
        for runner in all_runners:
            if runner.discard_pile:
                card = runner.discard_pile[-1]  # Dernière carte jouée
                self.track.move_runner(runner, card.value)

        # Passer à la phase terminale
        self.resolve_terminal_phase()

    def resolve_terminal_phase(self) -> None:
        """Résout la phase terminale."""
        if self.current_phase != Phase.MOVEMENT:
            return

        self.current_phase = Phase.TERMINAL

        # 1. Retirer les cartes jouées (déjà fait via discard_pile)
        # 2. Appliquer l'aspiration
        self.track.apply_aspiration()

        # 3. Attribuer les cartes Fatigue
        self._assign_fatigue_cards()

        # 4. Vérifier la condition de victoire
        if self._check_win_condition():
            self.game_over = True
        else:
            # Préparer le prochain tour
            self._cleanup_hands()
            self.start_turn()

    def _assign_fatigue_cards(self) -> None:
        """Attribue les cartes Fatigue aux coureurs fatigués."""
        for player in self.players:
            for runner in player.get_runners():
                if runner.is_tired(self.track):
                    # Pioche une carte Fatigue
                    if runner.fatigue_deck:
                        fatigue_card = runner.fatigue_deck.pop()
                        runner.discard_pile.append(fatigue_card)

    def _cleanup_hands(self) -> None:
        """Nettoie les mains des coureurs pour le prochain tour."""
        for player in self.players:
            for runner in player.get_runners():
                runner.reset_hand()
                # Re-mélanger le deck si nécessaire
                if not runner.energy_deck and runner.discard_pile:
                    runner.reshuffle_deck()

    def _check_win_condition(self) -> bool:
        """Vérifie si un coureur a franchi la ligne d'arrivée."""
        finish_x = self.track.length - 1
        for player in self.players:
            for runner in player.get_runners():
                if runner.x >= finish_x:
                    self.winner = player
                    return True
        return False

    def get_current_player(self) -> Player:
        """Retourne le joueur actuel."""
        return self.players[self.current_player_index]

    def get_current_phase_name(self) -> str:
        """Retourne le nom de la phase actuelle."""
        return self.current_phase.name

    def get_state(self) -> Dict:
        """Retourne l'état actuel du jeu (pour l'UI)."""
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
