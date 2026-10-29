import pygame
import sys
from typing import Optional, List
from game.game import Game, Phase
from game.runner import Runner
from game.card import Card, CardType

# Initialiser Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
CELL_SIZE = 60  # Taille d'une case en pixels
LANE_HEIGHT = CELL_SIZE // 2  # Hauteur d'une file
MARGIN = 50  # Marge autour de la piste

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# Couleurs des joueurs
PLAYER_COLORS = {
    "red": RED,
    "blue": BLUE,
    "green": GREEN,
    "yellow": YELLOW,
}


class FlammeRougeGame:
    """Classe principale pour l'interface Pygame."""

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flamme Rouge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 30)

        # Initialiser le jeu
        self.game = Game(stage="test", player_count=2)
        self.selected_runner: Optional[Runner] = None
        self.selected_card: Optional[Card] = None

        # État de l'UI
        self.show_hands = True  # Afficher les mains des coureurs

    def run(self):
        """Boucle principale du jeu."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Recommencer la partie
                        self.game = Game(stage="test", player_count=2)
                    elif event.key == pygame.K_h:
                        # Basculer l'affichage des mains
                        self.show_hands = not self.show_hands
                    elif event.key == pygame.K_SPACE:
                        # Passer à la phase suivante (pour tester)
                        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
                            self.game.resolve_movement_phase()
                        elif self.game.current_phase == Phase.MOVEMENT:
                            self.game.resolve_terminal_phase()

            # Mettre à jour l'affichage
            self.screen.fill(WHITE)
            self._draw_track()
            self._draw_runners()
            self._draw_ui()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def _handle_click(self, pos: tuple) -> None:
        """Gère les clics sur les cartes."""
        x, y = pos
        if not self.show_hands or self.game.current_phase != Phase.ENERGY:
            return

        # Bloquer les clics si toutes les cartes sont déjà jouées
        if self.game.all_players_ready():
            return

        hand_y_sprinter = SCREEN_HEIGHT - 120
        hand_y_roller = SCREEN_HEIGHT - 60

        for player_idx, player in enumerate(self.game.players):
            base_x = MARGIN + player_idx * 250

            # Clique sur une carte du sprinter
            for card_idx, card in enumerate(player.sprinter.hand):
                card_rect = pygame.Rect(
                    base_x + card_idx * 40,
                    hand_y_sprinter,
                    40, 60
                )
                if card_rect.collidepoint(x, y):
                    self.game.play_card(player, player.sprinter, card)
                    print(f"✅ Carte {card.value} jouée pour {player.color} Sprinteur")
                    if self.game.all_players_ready():
                        print("🚀 Toutes les cartes jouées ! Lancement de la phase de mouvement...")
                        self.game.resolve_movement_phase()
                    return

            # Clique sur une carte du rouleur
            for card_idx, card in enumerate(player.roller.hand):
                card_rect = pygame.Rect(
                    base_x + card_idx * 40,
                    hand_y_roller,
                    40, 60
                )
                if card_rect.collidepoint(x, y):
                    self.game.play_card(player, player.roller, card)
                    print(f"✅ Carte {card.value} jouée pour {player.color} Rouleur")
                    if self.game.all_players_ready():
                        print("🚀 Toutes les cartes jouées ! Lancement de la phase de mouvement...")
                        self.game.resolve_movement_phase()
                    return

    def _draw_track(self) -> None:
        """Dessine la piste."""
        # Dessiner le fond de la piste
        track_height = LANE_HEIGHT * 2 + 10
        track_y = (SCREEN_HEIGHT - track_height) // 2 - 50  # Déplacé vers le haut
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            (MARGIN, track_y, self.game.track.length * CELL_SIZE, track_height),
            border_radius=5,
        )

        # Dessiner les cases
        for x in range(self.game.track.length):
            cell_x = MARGIN + x * CELL_SIZE
            # File du haut (gauche)
            pygame.draw.rect(
                self.screen,
                WHITE,
                (cell_x, track_y, CELL_SIZE, LANE_HEIGHT),
                width=1,
            )
            # File du bas (droite)
            pygame.draw.rect(
                self.screen,
                WHITE,
                (cell_x, track_y + LANE_HEIGHT, CELL_SIZE, LANE_HEIGHT),
                width=1,
            )

            # Dessiner la ligne de départ et d'arrivée
            if x == 0:
                pygame.draw.rect(
                    self.screen,
                    GREEN,
                    (cell_x, track_y, CELL_SIZE, track_height),
                    width=3,
                )
            elif x == self.game.track.length - 1:
                pygame.draw.rect(
                    self.screen,
                    RED,
                    (cell_x, track_y, CELL_SIZE, track_height),
                    width=3,
                )

            # Numéro des cases (pour debug)
            if x % 2 == 0:
                text = self.font.render(str(x), True, BLACK)
                self.screen.blit(text, (cell_x + 5, track_y + 5))

    def _draw_runners(self) -> None:
        """Dessine les coureurs sur la piste."""
        track_y = (SCREEN_HEIGHT - (LANE_HEIGHT * 2 + 10)) // 2 - 50

        for player in self.game.players:
            for runner in player.get_runners():
                cell_x = MARGIN + runner.x * CELL_SIZE
                cell_y = track_y + runner.y * LANE_HEIGHT

                # Dessiner le coureur (cercle coloré)
                color = PLAYER_COLORS.get(player.color, BLACK)
                pygame.draw.circle(
                    self.screen,
                    color,
                    (cell_x + CELL_SIZE // 2, cell_y + LANE_HEIGHT // 2),
                    CELL_SIZE // 3,
                )

                # Écrire le type (S/R) et l'ID
                type_text = "S" if runner.type.name == "SPRINTER" else "R"
                text = self.font.render(f"{type_text}{runner.id[-1]}", True, WHITE)
                text_rect = text.get_rect(center=(cell_x + CELL_SIZE // 2, cell_y + LANE_HEIGHT // 2))
                self.screen.blit(text, text_rect)

                # Dessiner la dernière carte jouée (si phase de mouvement)
                if self.game.current_phase == Phase.MOVEMENT and runner.discard_pile:
                    last_card = runner.discard_pile[-1]
                    card_text = self.font.render(str(last_card.value), True, BLACK)
                    self.screen.blit(
                        card_text,
                        (cell_x + CELL_SIZE // 2 - 10, cell_y + LANE_HEIGHT // 2 - 20),
                    )

    def _draw_ui(self) -> None:
        """Dessine l'interface utilisateur (infos, mains, etc.)."""
        # Afficher la phase actuelle
        phase_text = self.big_font.render(
            f"Phase: {self.game.get_current_phase_name()} | Tour: {self.game.turn_count}",
            True,
            BLACK,
        )
        self.screen.blit(phase_text, (MARGIN, 10))

        # Nombre de cartes jouées/à jouer
        cards_text = self.big_font.render(
            f"Cartes jouées: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}",
            True,
            BLACK,
        )
        self.screen.blit(cards_text, (MARGIN, 50))

        # Afficher les mains des coureurs (si activé)
        if self.show_hands and self.game.current_phase == Phase.ENERGY:
            hand_y_sprinter = SCREEN_HEIGHT - 120
            hand_y_roller = SCREEN_HEIGHT - 60

            for player_idx, player in enumerate(self.game.players):
                base_x = MARGIN + player_idx * 250
                color = PLAYER_COLORS.get(player.color, BLACK)

                # Dessiner un fond pour le sprinter
                pygame.draw.rect(
                    self.screen,
                    color,
                    (base_x - 10, hand_y_sprinter - 10, 200, 70),
                    width=2,
                    border_radius=5
                )
                sprinter_text = self.font.render(
                    f"{player.color} Sprinteur:",
                    True,
                    color,
                )
                self.screen.blit(sprinter_text, (base_x, hand_y_sprinter - 30))

                # Dessiner les cartes du sprinter
                for card_idx, card in enumerate(player.sprinter.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_sprinter,
                        40,
                        60
                    )
                    pygame.draw.rect(self.screen, WHITE, card_rect, width=2)
                    card_text = self.font.render(str(card.value), True, BLACK)
                    card_text_rect = card_text.get_rect(center=card_rect.center)
                    self.screen.blit(card_text, card_text_rect)

                # Dessiner un fond pour le rouleur
                pygame.draw.rect(
                    self.screen,
                    color,
                    (base_x - 10, hand_y_roller - 10, 200, 70),
                    width=2,
                    border_radius=5
                )
                roller_text = self.font.render(
                    f"{player.color} Rouleur:",
                    True,
                    color,
                )
                self.screen.blit(roller_text, (base_x, hand_y_roller - 30))

                # Dessiner les cartes du rouleur
                for card_idx, card in enumerate(player.roller.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_roller,
                        40,
                        60
                    )
                    pygame.draw.rect(self.screen, WHITE, card_rect, width=2)
                    card_text = self.font.render(str(card.value), True, BLACK)
                    card_text_rect = card_text.get_rect(center=card_rect.center)
                    self.screen.blit(card_text, card_text_rect)

        # Afficher le gagnant si la partie est terminée
        if self.game.game_over:
            winner_text = self.big_font.render(
                f"Gagnant: {self.game.winner.color} ! (Appuyez sur R pour recommencer)",
                True,
                PLAYER_COLORS.get(self.game.winner.color, BLACK),
            )
            text_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(winner_text, text_rect)

        # Instructions
        if self.game.current_phase == Phase.ENERGY:
            instructions = [
                f"Jouez 1 carte par coureur ({self.game.total_cards_to_play} cartes au total)",
                "Appuyez sur H pour masquer/afficher les mains",
                "Appuyez sur R pour recommencer",
            ]
        else:
            instructions = [
                f"Phase: {self.game.get_current_phase_name()}",
                "Appuyez sur ESPACE pour passer à la phase suivante (debug)",
                "Appuyez sur R pour recommencer",
            ]
        for i, text in enumerate(instructions):
            text_surface = self.font.render(text, True, GRAY)
            self.screen.blit(text_surface, (MARGIN, SCREEN_HEIGHT - 60 + i * 25))


if __name__ == "__main__":
    game = FlammeRougeGame()
    game.run()
