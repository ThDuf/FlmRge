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
INSTRUCTIONS_X = SCREEN_WIDTH - 350  # Position X des instructions

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
        
        # Scroll horizontal pour la piste avec la souris
        self.scroll_x = 0  # Position de défilement
        self.scroll_speed = 30  # Vitesse de défilement
        self.dragging = False  # Indique si on est en train de draguer
        self.last_mouse_pos = (0, 0)  # Dernière position de la souris
        
        # Carte sélectionnée affichée à côté des mains
        self.selected_cards_display = []  # Liste de (player_color, runner_type, card_value, x, y)
        
        # Phase d'aspiration
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_groups = []
        self.aspiration_movements = []  # Liste des (runner, old_x, new_x)

    def _calculate_max_scroll(self) -> int:
        """Calcule le scroll maximum possible."""
        track_width = self.game.track.length * CELL_SIZE
        visible_width = SCREEN_WIDTH - 2 * MARGIN
        return max(0, track_width - visible_width)

    def _initialize_aspiration(self):
        """Initialise l'affichage de l'aspiration."""
        self.showing_aspiration = True
        self.aspiration_step = 0
        self.aspiration_groups = self.game.track.get_groups()
        self.aspiration_movements = []
        
        # Trouver tous les mouvements d'aspiration possibles
        # On doit recalculer les groupes après chaque mouvement, donc on fait une simulation
        temp_track = self.game.track
        groups = temp_track.get_groups()
        
        for i in range(len(groups) - 1, 0, -1):
            group_behind = groups[i]
            group_ahead = groups[i - 1]
            
            x_ahead = min(runner.x for runner in group_ahead)
            x_behind = max(runner.x for runner in group_behind)
            
            # Vérifier s'il y a exactement 1 case vide entre les groupes
            if x_ahead - x_behind == 2:
                # Tous les coureurs du groupe derrière à la position x_behind peuvent avancer
                for runner in group_behind:
                    if runner.x == x_behind:
                        self.aspiration_movements.append((runner, runner.x, runner.x + 1))

    def _apply_next_aspiration_step(self) -> bool:
        """Applique une étape d'aspiration. Retourne True si terminé."""
        if not self.aspiration_movements:
            return True
        
        # Appliquer le premier mouvement
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
                # Si la case est occupée, remettre le coureur à l'ancienne position
                runner.x = old_x
                if old_cell:
                    old_cell.set_runner(runner, runner.y)
        
        self.aspiration_step += 1
        
        # Recalculer les groupes et mouvements restants
        self.aspiration_groups = self.game.track.get_groups()
        remaining_movements = []
        for i in range(len(self.aspiration_groups) - 1, 0, -1):
            group_behind = self.aspiration_groups[i]
            group_ahead = self.aspiration_groups[i - 1]
            
            x_ahead = min(runner.x for runner in group_ahead)
            x_behind = max(runner.x for runner in group_behind)
            
            if x_ahead - x_behind == 2:
                for runner in group_behind:
                    if runner.x == x_behind:
                        remaining_movements.append((runner, runner.x, runner.x + 1))
        
        self.aspiration_movements = remaining_movements
        return len(self.aspiration_movements) == 0

    def run(self):
        """Boucle principale du jeu."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic gauche
                        # Vérifier si on clique sur une carte (seulement en phase ENERGY)
                        if self.game.current_phase == Phase.ENERGY and self.show_hands:
                            self._handle_click(event.pos)
                        # Démarrer le drag pour le scroll (si on ne clique pas sur une carte)
                        self.dragging = True
                        self.last_mouse_pos = event.pos
                    elif event.button == 4:  # Molette vers le haut
                        self.scroll_x = max(0, self.scroll_x - self.scroll_speed)
                    elif event.button == 5:  # Molette vers le bas
                        self.scroll_x = min(self._calculate_max_scroll(), self.scroll_x + self.scroll_speed)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Relâcher le clic gauche
                        self.dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging and self.game.current_phase != Phase.ENERGY:
                        # Calculer le décalage
                        dx = event.pos[0] - self.last_mouse_pos[0]
                        self.scroll_x = max(0, min(self._calculate_max_scroll(), self.scroll_x - dx))
                        self.last_mouse_pos = event.pos

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Recommencer la partie
                        self.game = Game(stage="test", player_count=2)
                        self.scroll_x = 0
                        self.selected_cards_display = []
                        self.showing_aspiration = False
                        self.aspiration_step = 0
                    elif event.key == pygame.K_h:
                        # Basculer l'affichage des mains
                        self.show_hands = not self.show_hands
                    elif event.key == pygame.K_RETURN:
                        # Passer à la phase suivante avec ENTRÉE
                        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
                            self.game.resolve_movement_phase()
                            self.selected_cards_display = []
                        elif self.game.current_phase == Phase.MOVEMENT:
                            # Initialiser l'aspiration avec les mouvements
                            self.aspiration_movements = self.game.resolve_aspiration_phase()
                            self._initialize_aspiration()
                            self.showing_aspiration = True
                            if not self.aspiration_movements:
                                # Pas d'aspiration possible, passer directement à la phase terminale
                                self.showing_aspiration = False
                                self.game.current_phase = Phase.TERMINAL
                                self.game._assign_fatigue_cards()
                                if not self.game._check_win_condition():
                                    self.game._cleanup_hands()
                                    self.game.start_turn()
                                    self.selected_cards_display = []
                                else:
                                    self.game.game_over = True
                        elif self.showing_aspiration:
                            if self._apply_next_aspiration_step():
                                # Aspiration terminée
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
                        # Scroll à gauche
                        self.scroll_x = max(0, self.scroll_x - self.scroll_speed)
                    elif event.key == pygame.K_RIGHT:
                        # Scroll à droite
                        self.scroll_x = min(self._calculate_max_scroll(), self.scroll_x + self.scroll_speed)

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

            # Sprinteur - vérifier qu'il n'a pas déjà joué
            if self.game.cards_played_per_runner[player.sprinter.id] < 1:
                for card_idx, card in enumerate(player.sprinter.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_sprinter,
                        40, 60
                    )
                    if card_rect.collidepoint(x, y):
                        if self.game.play_card(player, player.sprinter, card):
                            print(f"✅ {player.color} Sprinteur: carte {card.value} jouée")
                            # Enregistrer la carte sélectionnée pour l'affichage
                            self.selected_cards_display.append((
                                player.color,
                                "Sprinteur",
                                card.value,
                                base_x + card_idx * 40 + 40,
                                hand_y_sprinter
                            ))
                            if self.game.all_players_ready():
                                print("⏳ Toutes les cartes jouées ! Appuyez sur ENTRÉE pour lancer la phase de mouvement...")
                        return  # Sortir après avoir joué une carte

            # Rouleur - vérifier qu'il n'a pas déjà joué
            if self.game.cards_played_per_runner[player.roller.id] < 1:
                for card_idx, card in enumerate(player.roller.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_roller,
                        40, 60
                    )
                    if card_rect.collidepoint(x, y):
                        if self.game.play_card(player, player.roller, card):
                            print(f"✅ {player.color} Rouleur: carte {card.value} jouée")
                            # Enregistrer la carte sélectionnée pour l'affichage
                            self.selected_cards_display.append((
                                player.color,
                                "Rouleur",
                                card.value,
                                base_x + card_idx * 40 + 40,
                                hand_y_roller
                            ))
                            if self.game.all_players_ready():
                                print("⏳ Toutes les cartes jouées ! Appuyez sur ENTRÉE pour lancer la phase de mouvement...")
                        return  # Sortir après avoir joué une carte
            
            # Si on arrive ici, ce joueur a déjà joué toutes ses cartes, on passe au suivant
            continue

    def _draw_track(self) -> None:
        """Dessine la piste avec scroll."""
        # Dessiner le fond de la piste
        track_height = LANE_HEIGHT * 2 + 10
        track_y = (SCREEN_HEIGHT - track_height) // 2 - 30  # Déplacé vers le haut pour plus d'espace
        
        # Calculer la position visible de la piste
        visible_start = self.scroll_x // CELL_SIZE
        visible_end = min(self.game.track.length, (self.scroll_x + SCREEN_WIDTH - MARGIN) // CELL_SIZE)
        
        # Dessiner le fond de la piste (visible)
        visible_width = (visible_end - visible_start) * CELL_SIZE
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            (MARGIN - self.scroll_x % CELL_SIZE, track_y, visible_width + CELL_SIZE, track_height),
            border_radius=5,
        )

        # Dessiner les cases visibles
        for x in range(visible_start, visible_end):
            cell_x = MARGIN + x * CELL_SIZE - self.scroll_x
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
            if x % 5 == 0:
                text = self.font.render(str(x), True, BLACK)
                self.screen.blit(text, (cell_x + 5, track_y + 5))

    def _draw_runners(self) -> None:
        """Dessine les coureurs sur la piste."""
        track_y = (SCREEN_HEIGHT - (LANE_HEIGHT * 2 + 10)) // 2 - 30

        for player in self.game.players:
            for runner in player.get_runners():
                # Calculer la position visible avec scroll
                cell_x = MARGIN + runner.x * CELL_SIZE - self.scroll_x
                cell_y = track_y + runner.y * LANE_HEIGHT
                
                # Ne dessiner que si le coureur est visible
                if cell_x + CELL_SIZE < MARGIN or cell_x > SCREEN_WIDTH - MARGIN:
                    continue

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

                # Dessiner la dernière carte jouée (si phase de mouvement ou terminale)
                if self.game.current_phase in [Phase.MOVEMENT, Phase.TERMINAL] and runner.discard_pile:
                    last_card = runner.discard_pile[-1]
                    card_text = self.font.render(str(last_card.value), True, BLACK)
                    self.screen.blit(
                        card_text,
                        (cell_x + CELL_SIZE // 2 - 10, cell_y + LANE_HEIGHT // 2 - 20),
                    )
                
                # Dessiner l'indicateur d'aspiration (flèche orange)
                if self.showing_aspiration and (runner, runner.x - 1, runner.x) in self.aspiration_movements:
                    pygame.draw.line(
                        self.screen,
                        ORANGE,
                        (cell_x + CELL_SIZE // 2 - 10, cell_y + LANE_HEIGHT // 2),
                        (cell_x + CELL_SIZE // 2 + 10, cell_y + LANE_HEIGHT // 2),
                        3
                    )

    def _draw_ui(self) -> None:
        """Dessine l'interface utilisateur."""
        # ===== PHASE ACTUELLE (en haut à gauche) =====
        phase_text = self.big_font.render(
            f"Phase: {self.game.get_current_phase_name()}",
            True,
            BLACK,
        )
        self.screen.blit(phase_text, (MARGIN, 10))

        # ===== TOUR ACTUEL (en haut à gauche) =====
        turn_text = self.big_font.render(
            f"Tour: {self.game.turn_count}",
            True,
            BLACK,
        )
        self.screen.blit(turn_text, (MARGIN, 50))

        # ===== PHASE D'ASPIRATION (si active) =====
        if self.showing_aspiration:
            aspiration_text = self.big_font.render(
                f"🌪️ Aspiration: Étape {self.aspiration_step}/{len(self.aspiration_movements)}",
                True,
                ORANGE,
            )
            self.screen.blit(aspiration_text, (MARGIN, 90))

        # ===== NOMBRE DE CARTES JOUÉES (si phase ENERGY) =====
        if self.game.current_phase == Phase.ENERGY:
            cards_text = self.big_font.render(
                f"Cartes: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}",
                True,
                BLACK,
            )
            self.screen.blit(cards_text, (MARGIN, 90))

        # ===== INSTRUCTIONS (en haut à droite) =====
        instructions_y = 10
        if self.game.current_phase == Phase.ENERGY:
            if self.game.all_players_ready():
                instructions = [
                    "⏳ Appuyez sur ENTRÉE",
                    "    pour lancer",
                    "    la phase de mouvement",
                ]
            else:
                instructions = [
                    f"Jouez 1 carte par",
                    f"    coureur ({self.game.total_cards_to_play} total)",
                ]
        elif self.game.current_phase == Phase.MOVEMENT:
            instructions = [
                "⏳ Appuyez sur ENTRÉE",
                "    pour lancer",
                "    l'aspiration",
            ]
        elif self.showing_aspiration:
            instructions = [
                "⏳ Appuyez sur ENTRÉE",
                "    pour continuer",
                "    l'aspiration",
            ]
        elif self.game.current_phase == Phase.TERMINAL:
            instructions = [
                "⏳ Appuyez sur ENTRÉE",
                "    pour un nouveau",
                "    tour",
            ]
        else:
            instructions = [
                f"Phase: {self.game.get_current_phase_name()}",
            ]
        
        for i, text in enumerate(instructions):
            text_surface = self.font.render(text, True, BLACK)
            self.screen.blit(text_surface, (INSTRUCTIONS_X, instructions_y + i * 25))

        # ===== CONTRÔLES (en haut à droite, sous les instructions) =====
        controls_y = instructions_y + len(instructions) * 25 + 10
        controls = [
            "Molette/flèches: scroller",
            "H: masquer mains",
            "R: recommencer",
        ]
        for i, text in enumerate(controls):
            text_surface = self.font.render(text, True, GRAY)
            self.screen.blit(text_surface, (INSTRUCTIONS_X, controls_y + i * 25))

        # ===== CARTES SÉLECTIONNÉES (à côté des mains) =====
        for (color, runner_type, card_value, x, y) in self.selected_cards_display:
            card_text = self.font.render(f"→{card_value}", True, PLAYER_COLORS.get(color, BLACK))
            self.screen.blit(card_text, (x + 10, y))

        # ===== MAINS DES COUREURS (en bas) =====
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
                sprinter_status = "✅" if self.game.cards_played_per_runner[player.sprinter.id] >= 1 else "❌"
                sprinter_text = self.font.render(
                    f"{player.color} Sprinteur {sprinter_status}:",
                    True,
                    color,
                )
                self.screen.blit(sprinter_text, (base_x, hand_y_sprinter - 30))

                # Dessiner les cartes du sprinter (grisées si déjà joué)
                for card_idx, card in enumerate(player.sprinter.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_sprinter,
                        40,
                        60
                    )
                    card_color = GRAY if self.game.cards_played_per_runner[player.sprinter.id] >= 1 else WHITE
                    pygame.draw.rect(self.screen, card_color, card_rect, width=2)
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
                roller_status = "✅" if self.game.cards_played_per_runner[player.roller.id] >= 1 else "❌"
                roller_text = self.font.render(
                    f"{player.color} Rouleur {roller_status}:",
                    True,
                    color,
                )
                self.screen.blit(roller_text, (base_x, hand_y_roller - 30))

                # Dessiner les cartes du rouleur (grisées si déjà joué)
                for card_idx, card in enumerate(player.roller.hand):
                    card_rect = pygame.Rect(
                        base_x + card_idx * 40,
                        hand_y_roller,
                        40,
                        60
                    )
                    card_color = GRAY if self.game.cards_played_per_runner[player.roller.id] >= 1 else WHITE
                    pygame.draw.rect(self.screen, card_color, card_rect, width=2)
                    card_text = self.font.render(str(card.value), True, BLACK)
                    card_text_rect = card_text.get_rect(center=card_rect.center)
                    self.screen.blit(card_text, card_text_rect)

        # ===== GAGNANT (si partie terminée) =====
        if self.game.game_over:
            winner_text = self.big_font.render(
                f"Gagnant: {self.game.winner.color} !",
                True,
                PLAYER_COLORS.get(self.game.winner.color, BLACK),
            )
            text_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(winner_text, text_rect)
            
            restart_text = self.font.render(
                "Appuyez sur R pour recommencer",
                True,
                BLACK,
            )
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
            self.screen.blit(restart_text, restart_rect)


if __name__ == "__main__":
    game = FlammeRougeGame()
    game.run()
