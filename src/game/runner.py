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
    discard_pile: List[Card] = field(default_factory=list)  # cartes recyclées (non jouées + fatigue reçue)
    hand: List[Card] = field(default_factory=list)
    played_card: Optional[Card] = None  # carte jouée ce tour (retirée du jeu à la fin du tour)

    def draw_cards(self, count: int) -> List[Card]:
        """Pioche `count` cartes Énergie.

        Règles officielles : si le deck épuisé, mélanger les cartes
        recyclées et continuer à piocher jusqu'à avoir `count` cartes
        (ou épuisement total).
        """
        drawn = []
        while len(drawn) < count:
            if not self.energy_deck and self.discard_pile:
                self.reshuffle_deck()
            if not self.energy_deck:
                break
            drawn.append(self.energy_deck.pop(0))
        self.hand.extend(drawn)
        return drawn

    def play_card(self, card: Card) -> None:
        """Joue une carte (elle sera retirée du jeu à la fin du tour)."""
        if card in self.hand:
            self.hand.remove(card)
            self.played_card = card

    def reset_hand(self) -> None:
        """Recycle les cartes non jouées ; la carte jouée quitte le jeu."""
        self.discard_pile.extend(self.hand)
        self.hand = []
        self.played_card = None

    def reshuffle_deck(self) -> None:
        """Mélange la défausse pour reformer le deck Énergie."""
        import random
        self.energy_deck = self.discard_pile.copy()
        self.discard_pile = []
        random.shuffle(self.energy_deck)
