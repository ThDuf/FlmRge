from dataclasses import dataclass
from typing import List
from .runner import Runner, RunnerType
from .card import Card


@dataclass
class Player:
    """Représente un joueur avec 2 coureurs."""
    id: str
    color: str
    sprinter: Runner
    roller: Runner

    def __post_init__(self):
        """Initialise les coureurs avec la couleur du joueur."""
        self.sprinter.color = self.color
        self.roller.color = self.color

    def get_runners(self) -> List[Runner]:
        """Retourne les 2 coureurs du joueur."""
        return [self.sprinter, self.roller]

    def draw_cards_for_all(self, count: int) -> None:
        """Pioche `count` cartes pour chaque coureur."""
        self.sprinter.draw_cards(count)
        self.roller.draw_cards(count)

    def play_card_for_runner(self, runner: Runner, card: Card) -> None:
        """Joue une carte pour un coureur spécifique."""
        runner.play_card(card)
