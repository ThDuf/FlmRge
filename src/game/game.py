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
        if runner_type == RunnerType.SPRINTER:
            values = [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 9, 9, 9]
        else:
            values = [2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 7, 7, 8, 9]

        while len(values) < 45:
            values.extend(values[:10])
        values = values[:45]

        random.shuffle(values)
        return [Card(value, CardType.ENERGY) for value in values]

    def _generate_fatigue_deck(self) -> List[Card]:
        """Génère un deck Fatigue (toutes les cartes valent 2)."""
        return [Card(2, CardType.FATIGUE) for _ in range(10)]

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

    def _place_runner_at_start(self, runner: Runner) -> None:
        """Place un coureur à la ligne de départ.
        
        Règle : Priorité à la file A (lane 0) pour tous les coureurs.
        """
        # Priorité à la file A (lane 0) selon les règles
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
        
        Règle : Les coureurs se déplacent dans l'ordre inverse de leur position
        (du plus proche de l'arrivée au plus loin).
        """
        if self.current_phase != Phase.ENERGY:
            return

        self.current_phase = Phase.MOVEMENT
        print("\n--- PHASE DE MOUVEMENT ---")

        # Récupérer tous les coureurs triés par position (du plus proche au plus loin de l'arrivée)
        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        all_runners.sort(key=lambda r: r.x, reverse=True)

        print(f"Ordre de déplacement (du plus proche au plus loin) : {[r.id for r in all_runners]}")

        # Déplacer les coureurs un par un
        for runner in all_runners:
            if runner.discard_pile:
                card = runner.discard_pile[-1]
                print(f"  {runner.id} (pos {runner.x}) joue carte {card.value}")
                old_x = runner.x
                self.track.move_runner(runner, card.value)
                print(f"    -> Déplacé à {runner.x} (déplacement de {card.value} cases)")

        print("--- Fin de la phase de mouvement ---\n")

    def resolve_aspiration_phase(self) -> List:
        """
        Résout la phase d'aspiration selon les règles officielles.
        
        Règle : "Si exactement une case vide sépare deux groupes, 
        le groupe derrière avance d'une case."
        
        Retourne la liste des mouvements effectués.
        """
        if self.current_phase != Phase.MOVEMENT:
            return []

        self.current_phase = Phase.ASPIRATION
        print("\n--- PHASE D'ASPIRATION ---")

        # Afficher les groupes avant aspiration
        groups = self.track.get_groups()
        print(f"Groupes avant aspiration : {len(groups)} groupes")
        for i, group in enumerate(groups):
            positions = [r.x for r in group]
            print(f"  Groupe {i}: coureurs à positions {positions}")

        # Appliquer l'aspiration
        movements = self.track.apply_aspiration()

        # Afficher les groupes après aspiration
        groups = self.track.get_groups()
        print(f"Groupes après aspiration : {len(groups)} groupes")
        for i, group in enumerate(groups):
            positions = [r.x for r in group]
            print(f"  Groupe {i}: coureurs à positions {positions}")

        print(f"--- Fin de la phase d'aspiration ({len(movements)} mouvements) ---\n")
        return movements

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
            print(f"\n🏆 VICTOIRE : {self.winner.color} a gagné !\n")
        else:
            # 3. Préparer le prochain tour
            print("Préparation du prochain tour...")
            self._cleanup_hands()
            self.start_turn()

        print("--- Fin de la phase terminale ---\n")

    def _assign_fatigue_cards(self) -> None:
        """
        Attribue les cartes Fatigue selon les règles officielles.
        
        Règle : Seuls les premiers coureurs de chaque groupe reçoivent une carte Fatigue
        si la case devant eux est vide.
        """
        # Obtenir tous les coureurs triés par position
        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        
        # Trouver les groupes
        groups = self.track.get_groups()
        print(f"  Groupes pour la fatigue: {len(groups)} groupes")
        
        # Pour chaque groupe, seul le premier coureur (celui le plus en avant) peut être fatigué
        for group in groups:
            if not group:
                continue
            
            # Le premier du groupe est celui avec la position x la plus élevée
            leader = max(group, key=lambda r: (r.x, r.y))
            print(f"  Premier du groupe: {leader.id} à position {leader.x}, file {leader.y}")
            
            # Vérifier si la case devant le leader est vide
            if self.track.is_cell_empty(leader.x + 1, leader.y):
                if leader.fatigue_deck:
                    fatigue_card = leader.fatigue_deck.pop()
                    leader.discard_pile.append(fatigue_card)
                    print(f"  {leader.id} (premier du groupe) est fatigué -> reçoit une carte Fatigue (valeur 2)")
                else:
                    print(f"  {leader.id} devrait recevoir une fatigue mais n'a plus de cartes Fatigue")
            else:
                print(f"  {leader.id} (premier du groupe) n'est pas fatigué (case devant occupée)")

    def _cleanup_hands(self) -> None:
        """Nettoie les mains des coureurs pour le prochain tour."""
        for player in self.players:
            for runner in player.get_runners():
                runner.reset_hand()
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
