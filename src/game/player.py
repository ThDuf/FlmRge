from dataclasses import dataclass, field
from typing import List, Optional
from .runner import Runner, RunnerType
from .card import Card


@dataclass
class Player:
    """Représente un joueur avec 2 coureurs."""
    id: str
    color: str
    sprinter: Runner
    roller: Runner
    ai: Optional[str] = None          # None, "peloton" ou "muscle" (équipe factice)
    controller: Optional[int] = None  # index du joueur humain qui la contrôle (None = IA)
    ai_deck: list = field(default_factory=list)     # deck partagé de l'équipe Peloton
    ai_discard: list = field(default_factory=list)  # défausse de l'équipe Peloton

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
