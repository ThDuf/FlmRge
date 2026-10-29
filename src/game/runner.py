from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
from .card import Card, CardType


class RunnerType(Enum):
    SPRINTER = auto()  # Sprinteur (vitesse)
    ROLLER = auto()    # Rouleur (endurance)


@dataclass
class Runner:
    """Représente un coureur (Rouleur ou Sprinteur)."""
    id: str
    type: RunnerType
    x: int = 0          # Position en cases (0 = départ)
    y: int = 0          # File (0 = gauche, 1 = droite)
    color: str = "red"  # Couleur du joueur

    # Cartes
    energy_deck: List[Card] = field(default_factory=list)
    fatigue_deck: List[Card] = field(default_factory=list)
    discard_pile: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)

    def draw_cards(self, count: int) -> List[Card]:
        """Pioche `count` cartes Énergie."""
        drawn = self.energy_deck[:count]
        self.energy_deck = self.energy_deck[count:]
        self.hand.extend(drawn)
        return drawn

    def play_card(self, card: Card) -> None:
        """Joue une carte (la place dans la défausse)."""
        if card in self.hand:
            self.hand.remove(card)
            self.discard_pile.append(card)

    def is_tired(self, track: 'Track') -> bool:
        """Vérifie si le coureur est fatigué (case devant vide)."""
        from .track import Track
        return track.is_cell_empty(self.x + 1, self.y)

    def reset_hand(self) -> None:
        """Remet toutes les cartes de la main dans la défausse."""
        self.discard_pile.extend(self.hand)
        self.hand = []

    def reshuffle_deck(self) -> None:
        """Mélange la défausse pour reformer le deck Énergie."""
        import random
        self.energy_deck = self.discard_pile.copy()
        self.discard_pile = []
        random.shuffle(self.energy_deck)
