from dataclasses import dataclass
from enum import Enum, auto


class CardType(Enum):
    ENERGY = auto()
    FATIGUE = auto()


@dataclass
class Card:
    """Représente une carte Énergie ou Fatigue."""
    value: int
    type: CardType

    def __repr__(self):
        return f"Card(value={self.value}, type={self.type.name})"
