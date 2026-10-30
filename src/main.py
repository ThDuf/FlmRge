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
MIN_WIDTH = 900    # taille minimale de la fenêtre
MIN_HEIGHT = 600
CELL_SIZE = 60
LANE_HEIGHT = CELL_SIZE // 2
MARGIN = 50
CARD_W = 54        # taille des cartes en main
CARD_H = 68
CARD_GAP = 8       # espace entre cartes
PANEL_PAD = 12     # padding des panneaux de joueur
PANEL_HEADER = 32  # hauteur de l'en-tête des panneaux (nom + progression)

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
        self.width, self.height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Flamme Rouge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 30)
        self.card_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 15)

        self.game = Game(stage="test", player_count=2)
        self.show_hands = True
        self.show_decks = False  # Afficher les decks à droite
        self.scroll_x = 0
        self.scroll_speed = 30
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_total = 0
        self.aspiration_movements = []

    def _calculate_max_scroll(self) -> int:
        track_width = self.game.track.length * CELL_SIZE
        visible_width = self.width - 2 * MARGIN
        return max(0, track_width - visible_width)

    def _hands_height(self) -> int:
        """Hauteur réservée en bas pour les panneaux de sélection des cartes."""
        return PANEL_HEADER + 2 * CARD_H + 26

    def _track_top(self) -> int:
        """Position Y du haut de la piste (stable quel que soit la phase)."""
        track_height = LANE_HEIGHT * 2 + 10
        return max(120, (self.height - self._hands_height() - track_height) // 2)

    def _hand_layout(self):
        """Géométrie des panneaux de mains : un panneau par joueur, adapté à la fenêtre.

        Panneau compact : en-tête d'une ligne (nom du joueur + progression x/2),
        puis 2 lignes (Sprinteur / Rouleur) avec le libellé à GAUCHE et les
        cartes à droite du libellé.
        Retourne [(player, panel_rect, [(runner, label, [card_rects]), ...]), ...].
        Utilisé à la fois pour le dessin et pour la détection des clics,
        afin de garantir que les zones cliquables correspondent à l'affichage.
        """
        n = max(1, len(self.game.players))
        panel_w = min(520, max(260, (self.width - 2 * MARGIN) // n))
        panel_h = self._hands_height()
        top = self.height - panel_h - 6
        total_w = panel_w * n
        start_x = max(MARGIN // 2, (self.width - total_w) // 2)

        label_w = 104  # zone réservée au libellé ("Sprinteur" / "Rouleur")
        layout = []
        for idx, player in enumerate(self.game.players):
            panel = pygame.Rect(start_x + idx * panel_w, top, panel_w - 10, panel_h)
            avail = panel.w - label_w - 2 * PANEL_PAD
            card_w = max(32, min(CARD_W, (avail - 3 * CARD_GAP) // 4))
            rows = []
            for row, (runner, label) in enumerate(
                    [(player.sprinter, "Sprinteur"), (player.roller, "Rouleur")]):
                row_y = panel.y + PANEL_HEADER + 8 + row * (CARD_H + 10)
                cards_x = panel.x + label_w + PANEL_PAD
                rects = [pygame.Rect(cards_x + i * (card_w + CARD_GAP), row_y, card_w, CARD_H)
                         for i in range(len(runner.hand))]
                rows.append((runner, label, rects))
            layout.append((player, panel, rows))
        return layout

    def _initialize_aspiration(self):
        """Prépare l'affichage pas-à-pas de l'aspiration.

        Les étapes ont été CALCULÉES (mais pas appliquées) par
        Game.resolve_aspiration_phase(). Chaque appui sur ENTRÉE applique
        une étape sur le plateau : les coureurs bougent réellement un
        pack à la fois.
        """
        self.showing_aspiration = True
        self.aspiration_step = 0
        self.aspiration_total = len(self.aspiration_movements)

    def _next_aspiration_step(self) -> bool:
        """Applique une étape d'aspiration sur le plateau.

        Retourne True si toutes les étapes ont été appliquées.
        """
        if not self.aspiration_movements:
            return True
        step = self.aspiration_movements.pop(0)
        self.game.apply_slipstream_step(step)
        self.aspiration_step += 1
        return len(self.aspiration_movements) == 0

    def _finish_aspiration_phase(self):
        """Passe en phase terminale : fatigue, victoire éventuelle, nouveau tour."""
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_movements = []
        self.game.current_phase = Phase.TERMINAL
        self.game._assign_fatigue_cards()
        if not self.game._check_win_condition():
            self.game._cleanup_hands()
            self.game.start_turn()
        else:
            self.game.game_over = True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE:
                    # Fenêtre redimensionnable (taille minimale pour rester lisible)
                    self.width = max(MIN_WIDTH, event.w)
                    self.height = max(MIN_HEIGHT, event.h)
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    self.scroll_x = min(self.scroll_x, self._calculate_max_scroll())

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
                        self.showing_aspiration = False
                        self.aspiration_step = 0
                        self.aspiration_total = 0
                        self.aspiration_movements = []
                    elif event.key == pygame.K_h:
                        self.show_hands = not self.show_hands
                    elif event.key == pygame.K_d:
                        self.show_decks = not self.show_decks
                    elif event.key == pygame.K_RETURN:
                        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
                            self.game.resolve_movement_phase()
                        elif self.game.current_phase == Phase.MOVEMENT:
                            # Le moteur CALCULE toutes les étapes d'aspiration
                            # sans les appliquer : l'UI les applique pas-à-pas.
                            self.aspiration_movements = self.game.resolve_aspiration_phase()
                            if not self.aspiration_movements:
                                print("DEBUG: Aucune aspiration possible, passage en phase terminale")
                                self._finish_aspiration_phase()
                            else:
                                print(f"DEBUG: {len(self.aspiration_movements)} étapes d'aspiration à appliquer")
                                self._initialize_aspiration()
                        elif self.showing_aspiration:
                            # Applique réellement UNE étape (un pack) sur le plateau
                            if self._next_aspiration_step():
                                self._finish_aspiration_phase()
                        elif self.game.current_phase == Phase.TERMINAL:
                            if not self.game.game_over:
                                self.game._cleanup_hands()
                                self.game.start_turn()
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
        """Gère un clic : jouer une carte via les zones du layout des mains."""
        if not self.show_hands or self.game.current_phase != Phase.ENERGY:
            return
        if self.game.all_players_ready():
            return

        for player, panel, rows in self._hand_layout():
            for runner, label, rects in rows:
                if self.game.cards_played_per_runner[runner.id] >= 1:
                    continue  # ce coureur a déjà joué sa carte
                for card, rect in zip(runner.hand, rects):
                    if rect.collidepoint(pos):
                        if self.game.play_card(player, runner, card):
                            print(f"[OK] {player.color} {label}: carte {card.value} jouee")
                            if self.game.all_players_ready():
                                print("Appuyez sur ENTREE pour lancer la phase de mouvement...")
                        return

    def _draw_track(self):
        track_height = LANE_HEIGHT * 2 + 10
        track_y = self._track_top()
        visible_start = self.scroll_x // CELL_SIZE
        visible_end = min(self.game.track.length, (self.scroll_x + self.width - MARGIN) // CELL_SIZE)
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
        track_y = self._track_top()

        for player in self.game.players:
            for runner in player.get_runners():
                cell_x = MARGIN + runner.x * CELL_SIZE - self.scroll_x
                cell_y = track_y + runner.y * LANE_HEIGHT

                if cell_x + CELL_SIZE < MARGIN or cell_x > self.width - MARGIN:
                    continue

                color = PLAYER_COLORS.get(player.color, BLACK)
                center = (cell_x + CELL_SIZE // 2, cell_y + LANE_HEIGHT // 2)
                pygame.draw.circle(self.screen, color, center, CELL_SIZE // 3)

                # Type du coureur au-dessus du centre, carte jouée en dessous :
                # 2 textes petits, sans chevauchement dans le cercle
                type_text = "S" if runner.type.name == "SPRINTER" else "R"
                type_surf = self.small_font.render(f"{type_text}{runner.id[-1]}", True, WHITE)
                self.screen.blit(type_surf, type_surf.get_rect(center=(center[0], center[1] - 9)))

                if self.game.current_phase in [Phase.MOVEMENT, Phase.TERMINAL, Phase.ASPIRATION] and runner.played_card:
                    val_surf = self.small_font.render(str(runner.played_card.value), True, WHITE)
                    self.screen.blit(val_surf, val_surf.get_rect(center=(center[0], center[1] + 9)))

    def _draw_ui(self):
        # Barre d'infos en haut à gauche (espacée pour éviter tout chevauchement)
        phase_text = self.big_font.render(f"Phase: {self.game.get_current_phase_name()}", True, BLACK)
        self.screen.blit(phase_text, (MARGIN, 8))

        turn_text = self.big_font.render(f"Tour: {self.game.turn_count}", True, BLACK)
        self.screen.blit(turn_text, (MARGIN, 50))

        # Phase d'aspiration (pas-à-pas appliqué sur le plateau)
        if self.showing_aspiration:
            aspiration_text = self.big_font.render(
                f"Aspiration: {self.aspiration_step}/{self.aspiration_total} packs", True, ORANGE)
            self.screen.blit(aspiration_text, (MARGIN, 94))
            if self.aspiration_movements:
                step = self.aspiration_movements[0]
                desc = ", ".join(f"{r.id}:{fx}->{tx}" for r, fx, _fl, tx, _tl in step)
                next_text = self.font.render(f"Pack: {desc}", True, ORANGE)
                self.screen.blit(next_text, (MARGIN, 138))

        # Cartes jouées ce tour
        if self.game.current_phase == Phase.ENERGY:
            cards_text = self.big_font.render(
                f"Cartes: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}", True, BLACK)
            self.screen.blit(cards_text, (MARGIN, 94))

        # Instructions (haut à droite)
        instructions_y = 10
        instructions_x = self.width - 350
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
            self.screen.blit(text_surface, (instructions_x, instructions_y + i * 25))

        # Contrôles
        controls_y = instructions_y + len(instructions) * 25 + 10
        controls = ["Molette/fl\u00e8ches: scroller", "H: masquer mains", "D: afficher decks", "R: recommencer"]
        for i, text in enumerate(controls):
            text_surface = self.font.render(text, True, GRAY)
            self.screen.blit(text_surface, (instructions_x, controls_y + i * 25))

        # Mains des coureurs
        if self.show_hands and self.game.current_phase == Phase.ENERGY:
            self._draw_hands()

        # Affichage des decks
        if self.show_decks:
            self._draw_decks()

        # Écran de fin de partie (affiché quelle que soit la phase)
        if self.game.game_over and self.game.winner:
            winner_text = self.big_font.render(
                f"Gagnant: {self.game.winner.color} !", True,
                PLAYER_COLORS.get(self.game.winner.color, BLACK))
            text_rect = winner_text.get_rect(center=(self.width // 2, self.height // 2 - 50))
            self.screen.blit(winner_text, text_rect)
            restart_text = self.font.render("Appuyez sur R pour recommencer", True, BLACK)
            restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 10))
            self.screen.blit(restart_text, restart_rect)

    def _draw_hands(self):
        """Panneaux de sélection des cartes (phase d'énergie).

        Panneau compact par joueur : en-tête avec nom + progression x/2,
        libellés à gauche des cartes, surbrillance au survol, cartes grisées
        une fois jouées.
        """
        mouse = pygame.mouse.get_pos()
        for player, panel, rows in self._hand_layout():
            color = PLAYER_COLORS.get(player.color, BLACK)

            # Panneau du joueur
            pygame.draw.rect(self.screen, (248, 248, 245), panel, border_radius=8)
            pygame.draw.rect(self.screen, color, panel, width=2, border_radius=8)

            # En-tête : nom du joueur à gauche, progression à droite
            name = self.font.render(player.color.capitalize(), True, color)
            self.screen.blit(name, (panel.x + PANEL_PAD, panel.y + 6))
            played_count = sum(1 for r in (player.sprinter, player.roller)
                               if self.game.cards_played_per_runner[r.id] >= 1)
            prog = self.font.render(f"{played_count}/2", True,
                                    GREEN if played_count == 2 else GRAY)
            self.screen.blit(prog, (panel.right - PANEL_PAD - prog.get_width(), panel.y + 6))
            pygame.draw.line(self.screen, color,
                            (panel.x + 6, panel.y + PANEL_HEADER),
                            (panel.right - 6, panel.y + PANEL_HEADER), 1)

            for runner, label, rects in rows:
                played = self.game.cards_played_per_runner[runner.id] >= 1
                label_surf = self.font.render(label, True, GRAY if played else BLACK)
                self.screen.blit(label_surf, (panel.x + PANEL_PAD,
                                             rects[0].y + CARD_H // 2 - 10))

                for card, rect in zip(runner.hand, rects):
                    hovered = (not played) and rect.collidepoint(mouse)
                    if played:
                        fill = (225, 225, 225)
                    elif hovered:
                        fill = (255, 244, 200)
                    else:
                        fill = WHITE
                    pygame.draw.rect(self.screen, fill, rect, border_radius=6)
                    border_color = color if (hovered or played) else BLACK
                    pygame.draw.rect(self.screen, border_color, rect,
                                     width=3 if hovered else 2, border_radius=6)
                    value_text = str(card.value) + ("F" if card.type == CardType.FATIGUE else "")
                    val_surf = self.card_font.render(value_text, True, GRAY if played else BLACK)
                    self.screen.blit(val_surf, val_surf.get_rect(center=rect.center))

    def _format_cards_count(self, cards: List[Card]) -> str:
        """Formate une liste de cartes en affichant le nombre de cartes par valeur."""
        from game.card import CardType
        counts = {}
        for card in cards:
            if card.type == CardType.FATIGUE:
                key = "2F"
            else:
                key = str(card.value)
            counts[key] = counts.get(key, 0) + 1
        if not counts:
            return "-"
        sorted_keys = sorted(counts.keys(), key=lambda k: (0 if k == "2F" else int(k), k))
        return ",".join(f"{k}x{counts[k]}" for k in sorted_keys)

    def _format_hand(self, cards: List[Card]) -> str:
        """Formate la main en affichant les valeurs des cartes."""
        from game.card import CardType
        values = []
        for card in cards:
            if card.type == CardType.FATIGUE:
                values.append("2F")
            else:
                values.append(str(card.value))
        return ", ".join(values) if values else "-"

    def _draw_decks(self):
        """Affiche les decks à droite, sous les instructions/contrôles."""
        small_font = pygame.font.SysFont("Arial", 14)
        tiny_font = pygame.font.SysFont("Arial", 12)
        deck_x = self.width - 300
        deck_y = 205  # sous les instructions/contrôles (qui finissent vers y=195)
        hands_top = self.height - self._hands_height() - 6

        for player_idx, player in enumerate(self.game.players):
            block_y = deck_y + player_idx * 110
            if block_y + 140 > hands_top:
                break  # plus de place : ne pas dessiner sur les panneaux de mains
            color = PLAYER_COLORS.get(player.color, BLACK)
            title = small_font.render(f"{player.color}:", True, color)
            self.screen.blit(title, (deck_x, block_y))
            
            sprinter_energy_count = self._format_cards_count(player.sprinter.energy_deck)
            sprinter_hand = self._format_hand(player.sprinter.hand)
            sprinter_discard_count = self._format_cards_count(player.sprinter.discard_pile)

            sprinter_text1 = tiny_font.render(
                f"S: Deck[{len(player.sprinter.energy_deck)}:{sprinter_energy_count}]",
                True, BLACK
            )
            self.screen.blit(sprinter_text1, (deck_x + 30, block_y + 20))
            sprinter_text2 = tiny_font.render(f"   Hand:[{sprinter_hand}]", True, BLACK)
            self.screen.blit(sprinter_text2, (deck_x + 30, block_y + 40))
            sprinter_text3 = tiny_font.render(
                f"   Discard[{len(player.sprinter.discard_pile)}:{sprinter_discard_count}]",
                True, BLACK
            )
            self.screen.blit(sprinter_text3, (deck_x + 30, block_y + 60))

            roller_energy_count = self._format_cards_count(player.roller.energy_deck)
            roller_hand = self._format_hand(player.roller.hand)
            roller_discard_count = self._format_cards_count(player.roller.discard_pile)

            roller_text1 = tiny_font.render(
                f"R: Deck[{len(player.roller.energy_deck)}:{roller_energy_count}]",
                True, BLACK
            )
            self.screen.blit(roller_text1, (deck_x + 30, block_y + 80))
            roller_text2 = tiny_font.render(f"   Hand:[{roller_hand}]", True, BLACK)
            self.screen.blit(roller_text2, (deck_x + 30, block_y + 100))
            roller_text3 = tiny_font.render(
                f"   Discard[{len(player.roller.discard_pile)}:{roller_discard_count}]",
                True, BLACK
            )
            self.screen.blit(roller_text3, (deck_x + 30, block_y + 120))
            
            if player_idx < len(self.game.players) - 1:
                pygame.draw.line(self.screen, GRAY, (deck_x, block_y + 140),
                               (deck_x + 280, block_y + 140), 1)


if __name__ == "__main__":
    game = FlammeRougeGame()
    game.run()
