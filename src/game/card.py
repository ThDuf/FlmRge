from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class CardType(Enum):
    ENERGY = auto()
    FATIGUE = auto()


@dataclass
class Card:
    """Représente une carte Énergie ou Fatigue."""
    value: int
    type: CardType
    runner_type: Optional[str] = None  # "S" pour Sprinteur, "R" pour Rouleur

    def __repr__(self):
        runner_info = f", runner={self.runner_type}" if self.runner_type else ""
        return f"Card(value={self.value}, type={self.type.name}{runner_info})"
