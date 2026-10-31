import pygame
import sys
import math
from bisect import bisect_right
from game.game import Game, Phase
from game.card import CardType
from game.track import TileType

# Initialiser Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
MIN_WIDTH = 900    # taille minimale de la fenêtre
MIN_HEIGHT = 600
CELLS_PER_ROW = 16  # cases par rangée du circuit (14 droites + virage 180° = 2)
CELL_MIN = 32       # taille de case (s'adapte à la largeur de la fenêtre)
CELL_MAX = 60
INFO_H = 170         # hauteur réservée en haut pour la barre d'infos

CARD_W = 44        # taille des cartes en main
CARD_H = 58
CARD_GAP = 6       # espace entre cartes
PANEL_PAD = 10     # padding des panneaux de joueur
PANEL_HEADER = 30  # hauteur de l'en-tête des panneaux (nom + progression)
PANEL_H = 170      # hauteur d'un panneau de joueur (colonne de gauche)
GREEN_CARD_FILL = (185, 230, 176)    # carte jouée (sélectionnée)
GREEN_CARD_BORDER = (46, 125, 50)

LIGHT_TURN_FILL = (255, 250, 205)    # virage léger
SHARP_TURN_FILL = (255, 224, 178)   # virage serré
UPHILL_FILL = (255, 205, 205)       # montée (bords rouges dans le jeu officiel)
DOWNHILL_FILL = (205, 225, 255)     # descente (bords bleus)
UPHILL_ARROW = (180, 60, 60)        # triangle marqueur montée
DOWNHILL_ARROW = (60, 90, 180)      # triangle marqueur descente

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

PLAYER_COLORS = {
    "red": RED,
    "blue": BLUE,
    "green": GREEN,
    "yellow": YELLOW,
}


class FlammeRougeGame:
    """Interface Pygame : colonne de cartes à gauche, circuit serpentin à droite.

    Le circuit complet est affiché sans scrolling : les cases déroulent
    en serpentin (rangées gauche->droite puis droite->gauche), ce qui
    permet de voir toute la course d'un coup d'œil.
    """

    def __init__(self):
        self.width, self.height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Flamme Rouge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 30)
        self.card_font = pygame.font.SysFont("Arial", 18)
        self.label_font = pygame.font.SysFont("Arial", 16)
        self.small_font = pygame.font.SysFont("Arial", 12)

        self.game = Game(stage="circuit", player_count=2)
        self.show_hands = True
        self.played_display_index = {}  # runner_id -> position d'origine de la carte jouée
        self.show_decks = False  # Panneau des cartes restantes (touche D)
        self.showing_movement = False
        self.movement_step = 0
        self.movement_total = 0
        self.movement_movements = []
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_total = 0
        self.aspiration_movements = []

    # ------------------------------------------------------------------
    # Géométrie : colonne de gauche / circuit serpentin à droite
    # ------------------------------------------------------------------

    def _left_w(self) -> int:
        """Largeur de la colonne de gauche (panneaux de cartes des joueurs)."""
        return min(340, max(280, self.width // 2))

    def _cells_per_row(self) -> int:
        """Nombre de cases par rangée du circuit (fixe, aligné sur le moteur)."""
        return CELLS_PER_ROW

    def _track_geometry(self) -> dict:
        """Géométrie du circuit organique (mise en cache).

        Le circuit serpente : rangées droites reliées par de VRAIS virages
        à 180° (demi-cercles). L'arc total vaut exactement
        track.length * cell : chaque case occupe `cell` pixels d'arc, et les
        2 dernières cases d'une rangée tombent sur le demi-cercle. Les cases
        sont donc contiguës le long du chemin : AUCUN saut.
        """
        key = (self.width, self.height, self.game.track.length)
        if getattr(self, "_geo_key", None) == key:
            return self._geo

        left_w = self._left_w()
        avail = self.width - left_w - 24
        # 14 cases droites + les bombés des virages + la largeur de route
        # doivent tenir de part et d'autre
        cell = max(CELL_MIN, min(CELL_MAX, int((avail - 80) / 14.7)))
        radius = 2 * cell / math.pi
        lane_w = max(16, min(26, cell // 2))
        half = lane_w
        # Le bord gauche de la route (bombé du virage - demi-largeur) reste
        # à 16px de la colonne de panneaux
        track_left = left_w + 16 + radius + half
        length = self.game.track.length

        rows = -(-length // CELLS_PER_ROW)  # ceil
        rows_h = (rows - 1) * 2 * radius + 2 * half
        top = INFO_H + max(0, (self.height - INFO_H - 30 - rows_h) // 2)

        # Construction du chemin : segments droits + demi-cercles
        points = []
        x, y, direction = track_left, top, 1
        remaining = length
        while remaining > 0:
            in_row = min(CELLS_PER_ROW, remaining)
            hairpin = remaining > CELLS_PER_ROW  # pas de virage sur la rangée finale
            straight = in_row - (2 if hairpin else 0)
            points.append((x, y))
            x += direction * straight * cell
            points.append((x, y))
            remaining -= straight
            if hairpin:
                cx, cy = x, y + radius
                for i in range(1, 25):
                    phi = math.pi * i / 24
                    points.append((cx + direction * radius * math.sin(phi),
                                   cy - radius * math.cos(phi)))
                y += 2 * radius
                remaining -= 2
                direction = -direction

        # Longueurs cumulées (abscisse curviligne)
        cum = [0.0]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))

        geo = {"cell": cell, "radius": radius, "lane_w": lane_w, "half": half,
               "points": points, "cum": cum, "total": cum[-1], "top": top}
        self._geo_key = key
        self._geo = geo
        return geo

    def _path_at(self, geo: dict, s: float):
        """Point (x, y) et tangente unitaire (tx, ty) à l'abscisse curviligne s."""
        cum = geo["cum"]
        points = geo["points"]
        s = max(0.0, min(s, geo["total"]))
        i = max(1, min(bisect_right(cum, s), len(points) - 1))
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        seg = cum[i] - cum[i - 1]
        t = 0.0 if seg == 0 else (s - cum[i - 1]) / seg
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        d = math.hypot(x1 - x0, y1 - y0)
        if d == 0:
            return x, y, 1.0, 0.0
        return x, y, (x1 - x0) / d, (y1 - y0) / d

    def _cell_anchor(self, x_cell: int):
        """Centre de la case x_cell sur le circuit : (x, y, tx, ty)."""
        geo = self._track_geometry()
        return self._path_at(geo, (x_cell + 0.5) * geo["cell"])

    # ------------------------------------------------------------------
    # Géométrie : panneaux de cartes (colonne de gauche)
    # ------------------------------------------------------------------

    def _panel_h(self) -> int:
        """Hauteur d'un panneau de joueur, réduite si beaucoup de joueurs."""
        n = max(1, len(self.game.players))
        return min(PANEL_H, (self.height - 16 - (n - 1) * 8) // n)

    def _row_items(self, runner):
        """Cartes affichées d'un coureur : [(carte, jouée), ...].

        La carte jouée ce tour ne disparait PAS du panneau : elle est
        réinsérée à sa position d'origine (mémorisée au clic), marquée
        « jouée » pour être affichée en vert et non cliquable.
        """
        items = [(card, False) for card in runner.hand]
        if runner.played_card is not None:
            idx = self.played_display_index.get(runner.id, 0)
            items.insert(min(idx, len(items)), (runner.played_card, True))
        return items

    def _hand_layout(self):
        """Géométrie des panneaux de mains, empilés en colonne à GAUCHE.

        Un panneau compact par joueur : en-tête (nom + progression x/2),
        2 lignes (Sprinteur / Rouleur) avec libellé à gauche et cartes
        (carte jouée incluse, en vert) à droite.
        Retourne [(player, panel_rect, [(runner, label, items, [card_rects]), ...]), ...].
        Utilisé à la fois pour le dessin et pour la détection des clics,
        afin de garantir que les zones cliquables correspondent à l'affichage.
        """
        panel_h = self._panel_h()
        panel_w = self._left_w() - 16
        card_h = max(36, (panel_h - PANEL_HEADER - 26) // 2)
        label_w = 88  # zone réservée au libellé ("Sprinteur" / "Rouleur")
        avail = panel_w - label_w - 2 * PANEL_PAD
        card_w = max(28, min(CARD_W, (avail - 3 * CARD_GAP) // 4))

        layout = []
        for idx, player in enumerate(self.game.players):
            panel = pygame.Rect(8, 8 + idx * (panel_h + 8), panel_w, panel_h)
            rows = []
            for row, (runner, label) in enumerate(
                    [(player.sprinter, "Sprinteur"), (player.roller, "Rouleur")]):
                row_y = panel.y + PANEL_HEADER + 8 + row * (card_h + 10)
                items = self._row_items(runner)
                cards_x = panel.x + label_w + PANEL_PAD
                rects = [pygame.Rect(cards_x + i * (card_w + CARD_GAP), row_y, card_w, card_h)
                         for i in range(len(items))]
                rows.append((runner, label, items, rects))
            layout.append((player, panel, rows))
        return layout

    # ------------------------------------------------------------------
    # Déroulé du tour (bouton ou ENTRÉE)
    # ------------------------------------------------------------------

    def _start_movement_phase(self):
        """Calcule les mouvements (sans les appliquer) et démarre le pas-à-pas."""
        self.movement_movements = self.game.resolve_movement_phase()
        self.movement_step = 0
        self.movement_total = len(self.movement_movements)
        self.showing_movement = bool(self.movement_movements)

    def _next_movement_step(self) -> bool:
        """Applique UN mouvement de coureur sur le plateau.

        Retourne True si tous les mouvements ont été appliqués.
        """
        if not self.movement_movements:
            return True
        move = self.movement_movements.pop(0)
        self.game.apply_movement_step(move)
        self.movement_step += 1
        return len(self.movement_movements) == 0

    def _button_rect(self) -> pygame.Rect:
        """Position du bouton d'action (sous la colonne de panneaux, à gauche)."""
        n = max(1, len(self.game.players))
        y = 8 + n * (self._panel_h() + 8) + 6
        return pygame.Rect(8, min(y, self.height - 58), self._left_w() - 16, 48)

    def _button_info(self):
        """(libellé, couleur) du bouton d'action, ou None s'il n'y en a pas.

        Le bouton est l'équivalent cliquable de la touche ENTRÉE :
        lancer le mouvement, puis avancer un coureur / un pack à la fois.
        """
        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
            return ("Lancer le mouvement", (25, 118, 210))
        if self.showing_movement:
            return (f"Mouvement suivant  {self.movement_step}/{self.movement_total}", (46, 125, 50))
        if self.game.current_phase == Phase.MOVEMENT:
            return ("Lancer l'aspiration", (25, 118, 210))
        if self.showing_aspiration:
            return (f"Aspiration suivante  {self.aspiration_step}/{self.aspiration_total}", (230, 126, 0))
        return None

    def _try_button_click(self, pos) -> bool:
        """Gère un clic sur le bouton d'action. Retourne True si consommé."""
        info = self._button_info()
        if info is None or not self._button_rect().collidepoint(pos):
            return False
        self._advance_step()
        return True

    def _advance_step(self):
        """Avance d'une étape (bouton ou ENTRÉE) selon l'état courant."""
        if self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
            self._start_movement_phase()
        elif self.showing_movement:
            if self._next_movement_step():
                self.showing_movement = False
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

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

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

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if not self._try_button_click(event.pos):
                            if self.game.current_phase == Phase.ENERGY and self.show_hands:
                                self._handle_click(event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.game = Game(stage="circuit", player_count=2)
                        self.showing_movement = False
                        self.movement_step = 0
                        self.movement_total = 0
                        self.movement_movements = []
                        self.showing_aspiration = False
                        self.aspiration_step = 0
                        self.aspiration_total = 0
                        self.aspiration_movements = []
                        self.played_display_index = {}
                    elif event.key == pygame.K_h:
                        self.show_hands = not self.show_hands
                    elif event.key == pygame.K_d:
                        self.show_decks = not self.show_decks
                    elif event.key == pygame.K_RETURN:
                        self._advance_step()

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
            for runner, label, items, rects in rows:
                if self.game.cards_played_per_runner[runner.id] >= 1:
                    continue  # ce coureur a déjà joué sa carte
                for card_idx, ((card, played), rect) in enumerate(zip(items, rects)):
                    if played:
                        continue  # carte déjà jouée (affichée en vert)
                    if rect.collidepoint(pos):
                        if self.game.play_card(player, runner, card):
                            # Mémoriser la position d'origine pour que la carte
                            # reste affichée là où elle a été cliquée (en vert)
                            self.played_display_index[runner.id] = card_idx
                            print(f"[OK] {player.color} {label}: carte {card.value} jouee")
                            if self.game.all_players_ready():
                                print("Appuyez sur ENTREE pour lancer la phase de mouvement...")
                        return

    # ------------------------------------------------------------------
    # Dessin : circuit serpentin
    # ------------------------------------------------------------------

    def _draw_track(self):
        """Dessine le circuit organique : un chemin continu sans saut.

        La route suit le chemin (rangées droites + demi-cercles), les cases
        sont quadrillées le long de l'arc, les virages sont teintés, la ligne
        médiane blanche sépare les files A (droite) et B (gauche).
        """
        geo = self._track_geometry()
        track = self.game.track
        cell = geo["cell"]
        half = geo["half"]

        # Échantillons du chemin (point + tangente) pour les bords de route
        pts = geo["points"]
        samples = []
        for i, (x, y) in enumerate(pts):
            x0, y0 = pts[max(0, i - 1)]
            x1, y1 = pts[min(len(pts) - 1, i + 1)]
            d = math.hypot(x1 - x0, y1 - y0)
            if d == 0:
                tx, ty = 1.0, 0.0
            else:
                tx, ty = (x1 - x0) / d, (y1 - y0) / d
            samples.append((x, y, tx, ty))

        # Route : polygone entre les bords gauche et droit du sens de marche
        left_edge = [(x + ty * half, y - tx * half) for x, y, tx, ty in samples]
        right_edge = [(x - ty * half, y + tx * half) for x, y, tx, ty in samples]
        road = right_edge + left_edge[::-1]
        pygame.draw.polygon(self.screen, LIGHT_GRAY, road)
        pygame.draw.polygon(self.screen, GRAY, road, width=2)

        # Teinte des cases spéciales (virages, montées, descentes) + marqueurs
        for x_cell in range(track.length):
            tile_type = track.tiles[x_cell // 2].type
            if tile_type == TileType.LIGHT_TURN:
                color = LIGHT_TURN_FILL
            elif tile_type == TileType.SHARP_TURN:
                color = SHARP_TURN_FILL
            elif tile_type == TileType.UPHILL:
                color = UPHILL_FILL
            elif tile_type == TileType.DOWNHILL:
                color = DOWNHILL_FILL
            else:
                continue
            sample = []
            for k in range(9):
                px, py, _tx, _ty = self._path_at(geo, x_cell * cell + cell * k / 8)
                sample.append((px, py))
            pygame.draw.lines(self.screen, color, False, sample, width=2 * half)

            # Marqueurs montée/descente : triangles à l'extérieur droit de la route
            if tile_type in (TileType.UPHILL, TileType.DOWNHILL):
                px, py, tx, ty = self._path_at(geo, (x_cell + 0.5) * cell)
                nx, ny = -ty, tx
                mx = px + nx * (half + 12)
                my = py + ny * (half + 12)
                forward = 1 if tile_type == TileType.UPHILL else -1
                pts = [(mx + tx * 7 * forward, my + ty * 7 * forward),
                       (mx + nx * 5, my + ny * 5),
                       (mx - nx * 5, my - ny * 5)]
                arrow_color = UPHILL_ARROW if tile_type == TileType.UPHILL else DOWNHILL_ARROW
                pygame.draw.polygon(self.screen, arrow_color, pts)

        # Ligne médiane (séparation des files) + quadrillage des cases
        pygame.draw.lines(self.screen, WHITE, False, pts, 3)
        for k in range(track.length + 1):
            px, py, tx, ty = self._path_at(geo, k * cell)
            nx, ny = -ty, tx
            pygame.draw.line(self.screen, WHITE,
                             (px + nx * half, py + ny * half),
                             (px - nx * half, py - ny * half), 1)

        # Départ (vert) et arrivée (rouge) : traits perpendiculaires à la route
        for s, color in ((0, GREEN), (geo["total"], RED)):
            px, py, tx, ty = self._path_at(geo, s)
            nx, ny = -ty, tx
            pygame.draw.line(self.screen, color,
                             (px + nx * half, py + ny * half),
                             (px - nx * half, py - ny * half), 5)

        # Numéros de case tous les 5, à l'extérieur de la route
        for x_cell in range(0, track.length, 5):
            px, py, tx, ty = self._path_at(geo, (x_cell + 0.5) * cell)
            nx, ny = -ty, tx
            num = self.small_font.render(str(x_cell), True, GRAY)
            self.screen.blit(num, num.get_rect(
                center=(px - nx * (half + 11), py - ny * (half + 11))))

        # Lettres des files au départ : A à droite du sens de marche, B à gauche
        px, py, tx, ty = self._path_at(geo, 1.5 * cell)
        nx, ny = -ty, tx
        lane_a = self.small_font.render("A", True, BLACK)
        self.screen.blit(lane_a, lane_a.get_rect(
            center=(px + nx * (half + 10), py + ny * (half + 10))))
        lane_b = self.small_font.render("B", True, BLACK)
        self.screen.blit(lane_b, lane_b.get_rect(
            center=(px - nx * (half + 10), py - ny * (half + 10))))

    def _draw_runners(self):
        geo = self._track_geometry()
        lane_off = geo["lane_w"] / 2
        radius = int(geo["lane_w"] * 0.55)

        for player in self.game.players:
            for runner in player.get_runners():
                px, py, tx, ty = self._cell_anchor(runner.x)
                nx, ny = -ty, tx
                sign = 1 if runner.y == 0 else -1  # file A = droite du sens de marche
                cx = px + nx * lane_off * sign
                cy = py + ny * lane_off * sign

                color = PLAYER_COLORS.get(player.color, BLACK)
                pygame.draw.circle(self.screen, color, (int(cx), int(cy)), radius)

                # Type du coureur au-dessus du centre, carte jouée en dessous
                type_text = "S" if runner.type.name == "SPRINTER" else "R"
                type_surf = self.small_font.render(f"{type_text}{runner.id[-1]}", True, WHITE)
                self.screen.blit(type_surf, type_surf.get_rect(center=(cx, cy - 7)))

                if self.game.current_phase in [Phase.MOVEMENT, Phase.TERMINAL, Phase.ASPIRATION] and runner.played_card:
                    val_surf = self.small_font.render(str(runner.played_card.value), True, WHITE)
                    self.screen.blit(val_surf, val_surf.get_rect(center=(cx, cy + 8)))

    # ------------------------------------------------------------------
    # Dessin : interface
    # ------------------------------------------------------------------

    def _draw_ui(self):
        info_x = self._left_w() + 16

        # Barre d'infos en haut de la zone circuit (espacée, sans chevauchement)
        phase_text = self.big_font.render(f"Phase: {self.game.get_current_phase_name()}", True, BLACK)
        self.screen.blit(phase_text, (info_x, 8))

        turn_text = self.big_font.render(f"Tour: {self.game.turn_count}", True, BLACK)
        self.screen.blit(turn_text, (info_x, 50))

        # Pas-à-pas du mouvement (un coureur à la fois)
        if self.showing_movement:
            movement_text = self.big_font.render(
                f"Mouvement: {self.movement_step}/{self.movement_total} coureurs", True, BLACK)
            self.screen.blit(movement_text, (info_x, 94))
            if self.movement_movements:
                runner, value = self.movement_movements[0]
                next_text = self.font.render(
                    f"Suivant: {runner.id} joue {value}", True, BLACK)
                self.screen.blit(next_text, (info_x, 138))

        # Phase d'aspiration (pas-à-pas appliqué sur le plateau)
        if self.showing_aspiration:
            aspiration_text = self.big_font.render(
                f"Aspiration: {self.aspiration_step}/{self.aspiration_total} packs", True, ORANGE)
            self.screen.blit(aspiration_text, (info_x, 94))
            if self.aspiration_movements:
                step = self.aspiration_movements[0]
                desc = ", ".join(f"{r.id}:{fx}->{tx}" for r, fx, _fl, tx, _tl in step)
                next_text = self.font.render(f"Pack: {desc}", True, ORANGE)
                self.screen.blit(next_text, (info_x, 138))

        # Cartes jouées ce tour
        if self.game.current_phase == Phase.ENERGY:
            cards_text = self.big_font.render(
                f"Cartes: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}", True, BLACK)
            self.screen.blit(cards_text, (info_x, 94))

        # Instructions (haut à droite)
        instructions_y = 10
        instructions_x = self.width - 350
        if self.game.current_phase == Phase.ENERGY:
            if self.game.all_players_ready():
                instructions = ["ENTR\u00c9E ou bouton", "    pour lancer", "    la phase de mouvement"]
            else:
                instructions = [f"Jouez 1 carte par", f"    coureur ({self.game.total_cards_to_play} total)"]
        elif self.showing_movement:
            instructions = ["Un coureur \u00e0 la fois :", "    ENTR\u00c9E ou bouton", "    pour le suivant"]
        elif self.game.current_phase == Phase.MOVEMENT:
            instructions = ["ENTR\u00c9E ou bouton", "    pour lancer", "    l'aspiration"]
        elif self.showing_aspiration:
            instructions = ["Un pack \u00e0 la fois :", "    ENTR\u00c9E ou bouton", "    pour continuer"]
        elif self.game.current_phase == Phase.TERMINAL:
            instructions = ["ENTR\u00c9E ou bouton", "    pour un nouveau", "    tour"]
        else:
            instructions = [f"Phase: {self.game.get_current_phase_name()}"]

        for i, text in enumerate(instructions):
            text_surface = self.font.render(text, True, BLACK)
            self.screen.blit(text_surface, (instructions_x, instructions_y + i * 25))

        # Contrôles
        controls_y = instructions_y + len(instructions) * 25 + 10
        controls = ["H: masquer mains", "D: afficher decks", "R: recommencer"]
        for i, text in enumerate(controls):
            text_surface = self.font.render(text, True, GRAY)
            self.screen.blit(text_surface, (instructions_x, controls_y + i * 25))

        # Bouton d'action (équivalent cliquable de ENTRÉE) :
        # lancer le mouvement, puis avancer coureur par coureur / pack par pack
        button_info = self._button_info()
        if button_info is not None:
            label, button_color = button_info
            rect = self._button_rect()
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            fill = tuple(min(255, c + 35) for c in button_color) if hovered else button_color
            pygame.draw.rect(self.screen, fill, rect, border_radius=10)
            pygame.draw.rect(self.screen, BLACK, rect, width=2, border_radius=10)
            button_text = self.font.render(label, True, WHITE)
            self.screen.blit(button_text, button_text.get_rect(center=rect.center))

        # Mains des coureurs : visibles dans toutes les phases (cartes jouées
        # en vert, progression x/2) ; cliquables uniquement en phase d'énergie
        if self.show_hands:
            self._draw_hands()

        # Affichage des cartes restantes
        if self.show_decks:
            self._draw_decks()

        # Légende des couleurs du circuit (bas de la zone circuit)
        legend_y = self.height - 26
        legend_x = self._left_w() + 20
        for swatch, label in ((GREEN, "D\u00e9part"), (RED, "Arriv\u00e9e"),
                              (SHARP_TURN_FILL, "Virage"), (UPHILL_FILL, "Mont\u00e9e"),
                              (DOWNHILL_FILL, "Descente"), (WHITE, "Files A|B")):
            pygame.draw.rect(self.screen, swatch, (legend_x, legend_y, 14, 14), border_radius=3)
            pygame.draw.rect(self.screen, BLACK, (legend_x, legend_y, 14, 14),
                             width=1, border_radius=3)
            text_surf = self.label_font.render(label, True, BLACK)
            self.screen.blit(text_surf, (legend_x + 18, legend_y - 2))
            legend_x += 18 + text_surf.get_width() + 14

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
        """Panneaux de cartes des joueurs, empilés en colonne à gauche.

        Panneau compact par joueur : en-tête avec nom + progression x/2,
        libellés à gauche des cartes, surbrillance au survol, carte jouée
        en vert, cartes restantes grisées. Les cartes ne sont cliquables
        qu'en phase d'énergie (cf. _handle_click).
        """
        mouse = pygame.mouse.get_pos()
        for player, panel, rows in self._hand_layout():
            color = PLAYER_COLORS.get(player.color, BLACK)

            # Panneau du joueur
            pygame.draw.rect(self.screen, (248, 248, 245), panel, border_radius=8)
            pygame.draw.rect(self.screen, color, panel, width=2, border_radius=8)

            # En-tête : nom du joueur à gauche, progression à droite
            name = self.label_font.render(player.color.capitalize(), True, color)
            self.screen.blit(name, (panel.x + PANEL_PAD, panel.y + 6))
            played_count = sum(1 for r in (player.sprinter, player.roller)
                               if self.game.cards_played_per_runner[r.id] >= 1)
            prog = self.label_font.render(f"{played_count}/2", True,
                                          GREEN if played_count == 2 else GRAY)
            self.screen.blit(prog, (panel.right - PANEL_PAD - prog.get_width(), panel.y + 6))
            pygame.draw.line(self.screen, color,
                             (panel.x + 6, panel.y + PANEL_HEADER),
                             (panel.right - 6, panel.y + PANEL_HEADER), 1)

            for runner, label, items, rects in rows:
                played = self.game.cards_played_per_runner[runner.id] >= 1
                label_surf = self.label_font.render(label, True, GRAY if played else BLACK)
                self.screen.blit(label_surf, (panel.x + PANEL_PAD,
                                             rects[0].y + rects[0].h // 2 - 8))

                can_play = not played and self.game.current_phase == Phase.ENERGY
                for (card, is_played), rect in zip(items, rects):
                    hovered = can_play and rect.collidepoint(mouse)
                    if is_played:
                        # Carte sélectionnée : reste visible, en vert
                        fill = GREEN_CARD_FILL
                        border = GREEN_CARD_BORDER
                        text_color = GREEN_CARD_BORDER
                        width = 3
                    elif played:
                        # Coureur ayant déjà joué : cartes restantes grisées
                        fill = (225, 225, 225)
                        border = color
                        text_color = GRAY
                        width = 2
                    elif hovered:
                        fill = (255, 244, 200)
                        border = color
                        text_color = BLACK
                        width = 3
                    else:
                        fill = WHITE
                        border = BLACK
                        text_color = BLACK
                        width = 2
                    pygame.draw.rect(self.screen, fill, rect, border_radius=6)
                    pygame.draw.rect(self.screen, border, rect, width=width, border_radius=6)
                    value_text = str(card.value) + ("F" if card.type == CardType.FATIGUE else "")
                    val_surf = self.card_font.render(value_text, True, text_color)
                    self.screen.blit(val_surf, val_surf.get_rect(center=rect.center))

    def _remaining_counts(self, runner) -> dict:
        """Nombre de cartes restantes dans le jeu, par valeur.

        Compte la pioche + la main + la défausse (recyclée) ; les cartes
        jouées sont retirées du jeu et ne comptent pas. Les cartes
        Fatigue sont regroupées sous la clé "2F".
        """
        counts = {}
        for zone in (runner.energy_deck, runner.hand, runner.discard_pile):
            for card in zone:
                key = "2F" if card.type == CardType.FATIGUE else str(card.value)
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _draw_decks(self):
        """Panneau de visualisation des cartes restantes (touche D).

        Pour chaque coureur : une rangée de mini-cartes (valeurs 2 à 8 +
        Fatigue en orange) affichant le nombre de cartes de cette valeur
        encore dans le jeu, les valeurs épuisées en gris, plus les
        effectifs Pioche/Main/Défausse. Empilé en bas à droite.
        """
        tiny_font = pygame.font.SysFont("Arial", 10)
        small_font = pygame.font.SysFont("Arial", 14)
        count_font = pygame.font.SysFont("Arial", 12)

        panel_w = 300
        block_h = 104
        n = len(self.game.players)
        deck_x = self.width - panel_w - 8

        for player_idx, player in enumerate(self.game.players):
            # Empilement depuis le bas de l'écran
            block_y = self.height - (n - player_idx) * (block_h + 6) - 8
            if block_y < INFO_H:
                break  # plus de place au-dessus de la barre d'infos
            color = PLAYER_COLORS.get(player.color, BLACK)

            panel = pygame.Rect(deck_x, block_y, panel_w, block_h)
            pygame.draw.rect(self.screen, (250, 250, 248), panel, border_radius=8)
            pygame.draw.rect(self.screen, color, panel, width=2, border_radius=8)
            name_surf = small_font.render(player.color.capitalize(), True, color)
            self.screen.blit(name_surf, (deck_x + 10, block_y + 4))

            for row, (runner, tag) in enumerate(
                    [(player.sprinter, "S"), (player.roller, "R")]):
                row_y = block_y + 26 + row * 38
                counts = self._remaining_counts(runner)
                total = sum(counts.values())
                tag_surf = small_font.render(f"{tag} ({total})", True, color)
                self.screen.blit(tag_surf, (deck_x + 8, row_y + 8))

                x = deck_x + 42
                for v in ("2", "3", "4", "5", "6", "7", "8", "2F"):
                    cnt = counts.get(v, 0)
                    if cnt == 0:
                        fill, border, txt = (238, 238, 238), (210, 210, 210), (185, 185, 185)
                    elif v == "2F":
                        fill, border, txt = (255, 224, 178), ORANGE, (180, 90, 0)
                    else:
                        fill, border, txt = WHITE, BLACK, BLACK
                    rect = pygame.Rect(x, row_y, 20, 30)
                    pygame.draw.rect(self.screen, fill, rect, border_radius=4)
                    pygame.draw.rect(self.screen, border, rect, width=1, border_radius=4)
                    val_surf = tiny_font.render(v, True, txt)
                    self.screen.blit(val_surf, val_surf.get_rect(center=(rect.centerx, row_y + 9)))
                    cnt_surf = count_font.render(str(cnt), True, txt)
                    self.screen.blit(cnt_surf, cnt_surf.get_rect(center=(rect.centerx, row_y + 22)))
                    x += 22

                zones = tiny_font.render(
                    f"P:{len(runner.energy_deck)} M:{len(runner.hand)} D:{len(runner.discard_pile)}",
                    True, GRAY)
                self.screen.blit(zones, (deck_x + 42 + 8 * 22 + 4, row_y + 10))


if __name__ == "__main__":
    game = FlammeRougeGame()
    game.run()
