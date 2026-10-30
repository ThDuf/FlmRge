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
CELL_SIZE = 60
LANE_HEIGHT = CELL_SIZE // 2
MARGIN = 50
INSTRUCTIONS_X = SCREEN_WIDTH - 350
DECKS_X = SCREEN_WIDTH - 300  # Position pour afficher les decks

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

PLAYER_COLORS = {
    "red": RED,
    "blue": BLUE,
    "green": GREEN,
    "yellow": YELLOW,
}


class FlammeRougeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flamme Rouge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 30)

        self.game = Game(stage="test", player_count=2)
        self.selected_runner = None
        self.selected_card = None
        self.show_hands = True
        self.show_decks = False  # Afficher les decks à droite
        self.scroll_x = 0
        self.scroll_speed = 30
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.selected_cards_display = []
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_movements = []

    def _calculate_max_scroll(self) -> int:
        track_width = self.game.track.length * CELL_SIZE
        visible_width = SCREEN_WIDTH - 2 * MARGIN
        return max(0, track_width - visible_width)

    def _initialize_aspiration(self):
        """Initialise l'affichage de l'aspiration."""
        self.showing_aspiration = True
        self.aspiration_step = 0
        self.aspiration_movements = []
        
        # L'aspiration a déjà été calculée dans resolve_aspiration_phase
        # On inverse juste l'ordre pour l'affichage
        self.aspiration_movements = self.aspiration_movements[::-1]
        print(f"DEBUG: _initialize_aspiration avec {len(self.aspiration_movements)} mouvements")

    def _apply_next_aspiration_step(self) -> bool:
        """Applique une étape d'aspiration. Retourne True si terminé."""
        if not self.aspiration_movements:
            return True
        
        runner, old_x, new_x = self.aspiration_movements.pop(0)
        
        # Retirer le coureur de sa position actuelle
        old_cell = self.game.track.get_cell(old_x, runner.y)
        if old_cell:
            old_cell.remove_runner(runner.y)
        
        # Déplacer le coureur
        runner.x = new_x
        
        # Placer le coureur à sa nouvelle position
        new_cell = self.game.track.get_cell(new_x, runner.y)
        if new_cell:
            if new_cell.is_empty(runner.y):
                new_cell.set_runner(runner, runner.y)
            else:
                # Si la case est occupée, remettre le coureur
                runner.x = old_x
                if old_cell:
                    old_cell.set_runner(runner, runner.y)
        
        return len(self.aspiration_movements) == 0

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.game.current_phase == Phase.ENERGY and self.show_hands:
                            self._handle_click(event.pos)
                        self.dragging = True
                        self.last_mouse_pos = event.pos
                    elif event.button == 4:
                        self.scroll_x = max(0, self.scroll_x - self.scroll_speed)
                    elif event.button == 5:
                        self.scroll_x = min(self._calculate_max_scroll(), self.scroll_x + self.scroll_speed)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging and self.game.current_phase != Phase.ENERGY:
                        dx = event.pos[0] - self.last_mouse_pos[0]
                        self.scroll_x = max(0, min(self._calculate_max_scroll(), self.scroll_x - dx))
                        self.last_mouse_pos = event.pos

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.game = Game(stage="test", player_count=2)
                        self.scroll_x = 0
                        self.selected_cards_display = []
                        self.showing_aspiration = False
                    elif event.key == pygame.K_h:
                        self.show_hands = not self.show_hands
                    elif event.key == pygame.K_d:
                        self.show_decks = not self.show_decks
                    elif event.key == pygame.K_RETURN:
                        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
                            self.game.resolve_movement_phase()
                            self.selected_cards_display = []
                        elif self.game.current_phase == Phase.MOVEMENT:
                            self.aspiration_movements = self.game.resolve_aspiration_phase()
                            self._initialize_aspiration()
                            if not self.aspiration_movements:
                                print("DEBUG: Aucune aspiration possible, passage en phase terminale")
                                self.game.current_phase = Phase.TERMINAL
                                self.game._assign_fatigue_cards()
                                if not self.game._check_win_condition():
                                    self.game._cleanup_hands()
                                    self.game.start_turn()
                                    self.selected_cards_display = []
                                else:
                                    self.game.game_over = True
                            else:
                                print(f"DEBUG: {len(self.aspiration_movements)} mouvements d'aspiration à appliquer")
                        elif self.showing_aspiration:
                            if self._apply_next_aspiration_step():
                                self.showing_aspiration = False
                                self.game.current_phase = Phase.TERMINAL
                                self.game._assign_fatigue_cards()
                                if not self.game._check_win_condition():
                                    self.game._cleanup_hands()
                                    self.game.start_turn()
                                    self.selected_cards_display = []
                                else:
                                    self.game.game_over = True
                        elif self.game.current_phase == Phase.TERMINAL:
                            self.game._cleanup_hands()
                            self.game.start_turn()
                            self.selected_cards_display = []
                    elif event.key == pygame.K_LEFT:
                        self.scroll_x = max(0, self.scroll_x - self.scroll_speed)
                    elif event.key == pygame.K_RIGHT:
                        self.scroll_x = min(self._calculate_max_scroll(), self.scroll_x + self.scroll_speed)

            self.screen.fill(WHITE)
            self._draw_track()
            self._draw_runners()
            self._draw_ui()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def _handle_click(self, pos):
        x, y = pos
        if not self.show_hands or self.game.current_phase != Phase.ENERGY:
            return
        if self.game.all_players_ready():
            return

        hand_y_sprinter = SCREEN_HEIGHT - 120
        hand_y_roller = SCREEN_HEIGHT - 60

        for player_idx, player in enumerate(self.game.players):
            base_x = MARGIN + player_idx * 300  # Plus d'espace entre joueurs (300 au lieu de 250)

            if self.game.cards_played_per_runner[player.sprinter.id] < 1:
                for card_idx, card in enumerate(player.sprinter.hand):
                    card_rect = pygame.Rect(base_x + card_idx * 45, hand_y_sprinter, 40, 60)  # 45px d'espacement
                    if card_rect.collidepoint(x, y):
                        if self.game.play_card(player, player.sprinter, card):
                            print(f"\u2705 {player.color} Sprinteur: carte {card.value} jou\u00e9e")
                            self.selected_cards_display.append((player.color, "Sprinteur", card.value, base_x + card_idx * 45 + 45, hand_y_sprinter))
                            if self.game.all_players_ready():
                                print("\u23f3 Appuyez sur ENTR\u00c9E pour lancer la phase de mouvement...")
                        return

            if self.game.cards_played_per_runner[player.roller.id] < 1:
                for card_idx, card in enumerate(player.roller.hand):
                    card_rect = pygame.Rect(base_x + card_idx * 45, hand_y_roller, 40, 60)  # 45px d'espacement
                    if card_rect.collidepoint(x, y):
                        if self.game.play_card(player, player.roller, card):
                            print(f"\u2705 {player.color} Rouleur: carte {card.value} jou\u00e9e")
                            self.selected_cards_display.append((player.color, "Rouleur", card.value, base_x + card_idx * 45 + 45, hand_y_roller))
                            if self.game.all_players_ready():
                                print("\u23f3 Appuyez sur ENTR\u00c9E pour lancer la phase de mouvement...")
                        return

    def _draw_track(self):
        track_height = LANE_HEIGHT * 2 + 10
        track_y = (SCREEN_HEIGHT - track_height) // 2 - 30
        visible_start = self.scroll_x // CELL_SIZE
        visible_end = min(self.game.track.length, (self.scroll_x + SCREEN_WIDTH - MARGIN) // CELL_SIZE)
        visible_width = (visible_end - visible_start) * CELL_SIZE
        
        pygame.draw.rect(self.screen, LIGHT_GRAY, (MARGIN - self.scroll_x % CELL_SIZE, track_y, visible_width + CELL_SIZE, track_height), border_radius=5)

        for x in range(visible_start, visible_end):
            cell_x = MARGIN + x * CELL_SIZE - self.scroll_x
            pygame.draw.rect(self.screen, WHITE, (cell_x, track_y, CELL_SIZE, LANE_HEIGHT), width=1)
            pygame.draw.rect(self.screen, WHITE, (cell_x, track_y + LANE_HEIGHT, CELL_SIZE, LANE_HEIGHT), width=1)

            # Afficher les noms des files
            if x == 0:
                lane_a_text = self.font.render("A", True, BLACK)
                self.screen.blit(lane_a_text, (cell_x - 25, track_y + LANE_HEIGHT // 2 - 10))
                lane_b_text = self.font.render("B", True, BLACK)
                self.screen.blit(lane_b_text, (cell_x - 25, track_y + LANE_HEIGHT + LANE_HEIGHT // 2 - 10))

            if x == 0:
                pygame.draw.rect(self.screen, GREEN, (cell_x, track_y, CELL_SIZE, track_height), width=3)
            elif x == self.game.track.length - 1:
                pygame.draw.rect(self.screen, RED, (cell_x, track_y, CELL_SIZE, track_height), width=3)

            if x % 5 == 0:
                text = self.font.render(str(x), True, BLACK)
                self.screen.blit(text, (cell_x + 5, track_y + 5))

    def _draw_runners(self):
        track_y = (SCREEN_HEIGHT - (LANE_HEIGHT * 2 + 10)) // 2 - 30

        for player in self.game.players:
            for runner in player.get_runners():
                cell_x = MARGIN + runner.x * CELL_SIZE - self.scroll_x
                cell_y = track_y + runner.y * LANE_HEIGHT
                
                if cell_x + CELL_SIZE < MARGIN or cell_x > SCREEN_WIDTH - MARGIN:
                    continue

                color = PLAYER_COLORS.get(player.color, BLACK)
                pygame.draw.circle(self.screen, color, (cell_x + CELL_SIZE // 2, cell_y + LANE_HEIGHT // 2), CELL_SIZE // 3)

                type_text = "S" if runner.type.name == "SPRINTER" else "R"
                text = self.font.render(f"{type_text}{runner.id[-1]}", True, WHITE)
                text_rect = text.get_rect(center=(cell_x + CELL_SIZE // 2, cell_y + LANE_HEIGHT // 2))
                self.screen.blit(text, text_rect)

                if self.game.current_phase in [Phase.MOVEMENT, Phase.TERMINAL, Phase.ASPIRATION] and runner.discard_pile:
                    last_card = runner.discard_pile[-1]
                    card_text = self.font.render(str(last_card.value), True, BLACK)
                    self.screen.blit(card_text, (cell_x + CELL_SIZE // 2 - 10, cell_y + LANE_HEIGHT // 2 - 20))

    def _draw_ui(self):
        # Phase actuelle
        phase_text = self.big_font.render(f"Phase: {self.game.get_current_phase_name()}", True, BLACK)
        self.screen.blit(phase_text, (MARGIN, 10))

        # Tour actuel
        turn_text = self.big_font.render(f"Tour: {self.game.turn_count}", True, BLACK)
        self.screen.blit(turn_text, (MARGIN, 50))

        # Phase d'aspiration
        if self.showing_aspiration:
            aspiration_text = self.big_font.render(f"Aspiration: {self.aspiration_step}/{len(self.aspiration_movements)}", True, ORANGE)
            self.screen.blit(aspiration_text, (MARGIN, 90))

        # Cartes jouées
        if self.game.current_phase == Phase.ENERGY:
            cards_text = self.big_font.render(f"Cartes: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}", True, BLACK)
            self.screen.blit(cards_text, (MARGIN, 90))

        # Cartes sélectionnées
        for (color, runner_type, card_value, x, y) in self.selected_cards_display:
            card_text = self.font.render(f"\u2192{card_value}", True, PLAYER_COLORS.get(color, BLACK))
            self.screen.blit(card_text, (x + 10, y))

        # Instructions (haut à droite)
        instructions_y = 10
        if self.game.current_phase == Phase.ENERGY:
            if self.game.all_players_ready():
                instructions = ["\u23f3 Appuyez sur ENTR\u00c9E", "    pour lancer", "    la phase de mouvement"]
            else:
                instructions = [f"Jouez 1 carte par", f"    coureur ({self.game.total_cards_to_play} total)"]
        elif self.game.current_phase == Phase.MOVEMENT:
            instructions = ["\u23f3 Appuyez sur ENTR\u00c9E", "    pour lancer", "    l'aspiration"]
        elif self.showing_aspiration:
            instructions = ["\u23f3 Appuyez sur ENTR\u00c9E", "    pour continuer", "    l'aspiration"]
        elif self.game.current_phase == Phase.TERMINAL:
            instructions = ["\u23f3 Appuyez sur ENTR\u00c9E", "    pour un nouveau", "    tour"]
        else:
            instructions = [f"Phase: {self.game.get_current_phase_name()}"]
        
        for i, text in enumerate(instructions):
            text_surface = self.font.render(text, True, BLACK)
            self.screen.blit(text_surface, (INSTRUCTIONS_X, instructions_y + i * 25))

        # Contrôles
        controls_y = instructions_y + len(instructions) * 25 + 10
        controls = ["Molette/fl\u00e8ches: scroller", "H: masquer mains", "D: afficher decks", "R: recommencer"]
        for i, text in enumerate(controls):
            text_surface = self.font.render(text, True, GRAY)
            self.screen.blit(text_surface, (INSTRUCTIONS_X, controls_y + i * 25))

        # Mains des coureurs
        if self.show_hands and self.game.current_phase == Phase.ENERGY:
            hand_y_sprinter = SCREEN_HEIGHT - 120
            hand_y_roller = SCREEN_HEIGHT - 60

            for player_idx, player in enumerate(self.game.players):
                base_x = MARGIN + player_idx * 300  # Plus d'espace entre joueurs
                color = PLAYER_COLORS.get(player.color, BLACK)

                # Sprinteur
                pygame.draw.rect(self.screen, color, (base_x - 10, hand_y_sprinter - 10, 260, 70), width=2, border_radius=5)
                sprinter_status = "\u2705" if self.game.cards_played_per_runner[player.sprinter.id] >= 1 else "\u274c"
                sprinter_text = self.font.render(f"{player.color} Sprinteur {sprinter_status}:", True, color)
                self.screen.blit(sprinter_text, (base_x, hand_y_sprinter - 30))

                for card_idx, card in enumerate(player.sprinter.hand):
                    card_rect = pygame.Rect(base_x + card_idx * 45, hand_y_sprinter, 40, 60)  # 45px d'espacement
                    card_color = GRAY if self.game.cards_played_per_runner[player.sprinter.id] >= 1 else WHITE
                    pygame.draw.rect(self.screen, card_color, card_rect, width=2)
                    card_text = self.font.render(str(card.value), True, BLACK)
                    card_text_rect = card_text.get_rect(center=card_rect.center)
                    self.screen.blit(card_text, card_text_rect)

                # Rouleur (en dessous, avec plus d'espace)
                pygame.draw.rect(self.screen, color, (base_x - 10, hand_y_roller - 10, 260, 70), width=2, border_radius=5)
                roller_status = "\u2705" if self.game.cards_played_per_runner[player.roller.id] >= 1 else "\u274c"
                roller_text = self.font.render(f"{player.color} Rouleur {roller_status}:", True, color)
                self.screen.blit(roller_text, (base_x, hand_y_roller - 30))

                for card_idx, card in enumerate(player.roller.hand):
                    card_rect = pygame.Rect(base_x + card_idx * 45, hand_y_roller, 40, 60)  # 45px d'espacement
                    card_color = GRAY if self.game.cards_played_per_runner[player.roller.id] >= 1 else WHITE
                    pygame.draw.rect(self.screen, card_color, card_rect, width=2)
                    card_text = self.font.render(str(card.value), True, BLACK)
                    card_text_rect = card_text.get_rect(center=card_rect.center)
                    self.screen.blit(card_text, card_text_rect)

        # Affichage des decks (en bas à droite, format compact)
        if self.show_decks:
            small_font = pygame.font.SysFont("Arial", 16)
            deck_x = SCREEN_WIDTH - 250
            deck_y = SCREEN_HEIGHT - 200
            
            for player_idx, player in enumerate(self.game.players):
                color = PLAYER_COLORS.get(player.color, BLACK)
                
                # Titre joueur
                title = small_font.render(f"{player.color}:", True, color)
                self.screen.blit(title, (deck_x, deck_y + player_idx * 100))
                
                # Fonction pour compter les cartes par valeur
                def count_cards(deck, is_fatigue=False):
                    counts = {}
                    for card in deck:
                        if is_fatigue:
                            key = "2F"  # Cartes fatigue valent toujours 2
                        else:
                            key = str(card.value)
                        counts[key] = counts.get(key, 0) + 1
                    return counts
                
                # Sprinteur
                sprinter_energy_counts = count_cards(player.sprinter.energy_deck)
                sprinter_fatigue_counts = count_cards(player.sprinter.fatigue_deck, is_fatigue=True)
                
                sprinter_text = small_font.render(
                    f"S: {', '.join([f'{k}:{v}' for k, v in sorted(sprinter_energy_counts.items())])} | F:{sprinter_fatigue_counts.get('2F', 0)}",
                    True, BLACK
                )
                self.screen.blit(sprinter_text, (deck_x + 30, deck_y + 20 + player_idx * 100))
                
                # Rouleur
                roller_energy_counts = count_cards(player.roller.energy_deck)
                roller_fatigue_counts = count_cards(player.roller.fatigue_deck, is_fatigue=True)
                
                roller_text = small_font.render(
                    f"R: {', '.join([f'{k}:{v}' for k, v in sorted(roller_energy_counts.items())])} | F:{roller_fatigue_counts.get('2F', 0)}",
                    True, BLACK
                )
                self.screen.blit(roller_text, (deck_x + 30, deck_y + 40 + player_idx * 100))

        # Gagnant
        if self.game.game_over:
            winner_text = self.big_font.render(f"Gagnant: {self.game.winner.color} !", True, PLAYER_COLORS.get(self.game.winner.color, BLACK))
            text_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(winner_text, text_rect)
            restart_text = self.font.render("Appuyez sur R pour recommencer", True, BLACK)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
            self.screen.blit(restart_text, restart_rect)


if __name__ == "__main__":
    game = FlammeRougeGame()
    game.run()
