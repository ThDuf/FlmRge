import pygame
import sys
import math
from bisect import bisect_right
from game.game import Game, Phase
from game.card import CardType
from game.track import CellGeographyType, CellRunType

# Initialiser Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
MIN_WIDTH = 900    # taille minimale de la fenêtre
MIN_HEIGHT = 600
CELLS_PER_ROW = None  # (obsolète : le tracé suit désormais la séquence des tuiles)
CELL_MIN = 10       # plancher absolu de taille de case (le tracé tient toujours à l'écran)
CELL_MAX = 60
HEADER_H = 60       # bandeau de titre (toute la largeur)
PHASE_H = 44        # bandeau de phase (toute la largeur)
TOP_H = HEADER_H + PHASE_H + 8  # début de la zone de jeu sous les bandeaux
INFO_H = 100        # hauteur du bloc infos (compteur, action, prochain)

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

# Noms d'affichage des étapes
STAGE_NAMES = {
    "test": "Piste d'essai",
    "Avenue Corso Paseo": "Avenue Corso Paseo",
}


class FlammeRougeGame:
    """Interface Pygame : colonne de cartes à gauche, circuit serpentin à droite.

    Le circuit complet est affiché sans scrolling : les cases déroulent
    en serpentin (rangées gauche->droite puis droite->gauche), ce qui
    permet de voir toute la course d'un coup d'œil.
    """

    def __init__(self, stage: str = None):
        self.width, self.height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Flamme Rouge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 30)
        self.title_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.phase_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.card_font = pygame.font.SysFont("Arial", 18)
        self.label_font = pygame.font.SysFont("Arial", 16)
        self.small_font = pygame.font.SysFont("Arial", 12)

        self.stage = stage  # None -> menu de sélection d'étape affiché
        self.player_count = 2  # nombre de joueurs choisi au menu (2-4)
        self.game = Game(stage=stage, player_count=self.player_count) if stage else None
        self.menu_index = 0
        self.menu_step = "stage"  # "stage" -> "players"
        self._pending_stage = None
        self._preview_cache = {}  # nom d'étape -> polyligne de prévisualisation
        self._profile_cache = {}  # nom d'étape -> profil d'altitude
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
        self.last_action = None  # (texte, couleur) de la dernière action effectuée

    def _short_id(self, runner) -> str:
        """Identifiant court pour l'affichage : S0 / R1 (type + index)."""
        letter = "S" if runner.type.name == "SPRINTER" else "R"
        return f"{letter}{runner.id[-1]}"

    # ------------------------------------------------------------------
    # Géométrie : colonne de gauche / circuit serpentin à droite
    # ------------------------------------------------------------------

    def _left_w(self) -> int:
        """Largeur de la colonne de gauche (panneaux de cartes des joueurs)."""
        return min(340, max(280, self.width // 2))

    def _track_geometry(self) -> dict:
        """Géométrie du circuit (mise en cache), ajustée à la fenêtre.

        Le tracé suit la SÉQUENCE RÉELLE des tuiles (compute_track_path :
        chaque tuile avance de 2 cases, les virages courbent le cap de
        45°/90° selon leur direction), puis est mis à l'échelle et centré
        dans la zone de droite. Chaque case occupe exactement `cell` pixels
        d'arc : les cases restent contiguës, aucun saut.
        """
        key = (self.width, self.height, self.game.stage)
        if getattr(self, "_geo_key", None) == key:
            return self._geo

        from game.track import compute_track_path
        pts_units = compute_track_path(self.game.track, unit=1.0)

        left = self._left_w() + 12
        right = self.width - 12
        top = TOP_H + INFO_H + 6
        bottom = self.height - 34  # légende en bas
        avail_w = max(50.0, right - left)
        avail_h = max(50.0, bottom - top)

        xs = [p[0] for p in pts_units]
        ys = [p[1] for p in pts_units]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # marge de 30px de chaque côté pour la demi-largeur de la route
        scale = min((avail_w - 60) / max(bb_w, 1e-9), (avail_h - 60) / max(bb_h, 1e-9))
        cell = max(CELL_MIN, min(CELL_MAX, scale))
        ox = left + (avail_w - bb_w * cell) / 2 - min(xs) * cell
        oy = top + (avail_h - bb_h * cell) / 2 - min(ys) * cell

        points = [(ox + px * cell, oy + py * cell) for px, py in pts_units]

        # Longueurs cumulées (abscisse curviligne)
        cum = [0.0]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))

        lane_w = max(14, min(26, int(cell * 0.45)))
        geo = {"cell": cell, "lane_w": lane_w, "half": lane_w,
               "points": points, "cum": cum, "total": cum[-1]}
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
        return min(PANEL_H, (self.height - TOP_H - 16 - (n - 1) * 8) // n)

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
            panel = pygame.Rect(8, TOP_H + 8 + idx * (panel_h + 8), panel_w, panel_h)
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
        """Applique UN mouvement de coureur sur le plateau et l'affiche.

        Retourne True si tous les mouvements ont été appliqués.
        """
        if not self.movement_movements:
            return True
        move = self.movement_movements.pop(0)
        runner, value = move
        eff, reason = self.game.track.effective_steps(runner.x, value)
        from_x, from_y = runner.x, runner.y
        self.game.apply_movement_step(move)
        to_x, to_y = runner.x, runner.y

        # Bandeau : ce qui vient de se passer
        if to_x == from_x:
            desc = f"{self._short_id(runner)} joue {value} : bloqu\u00e9 (cases pleines devant)"
        elif reason:
            desc = (f"{self._short_id(runner)} joue {value} \u2192 {eff} ({reason}) : "
                    f"case {from_x}\u2192{to_x}")
        else:
            desc = f"{self._short_id(runner)} joue {value} : case {from_x}\u2192{to_x}"
        if from_y != to_y:
            desc += f", passe en file {'A' if to_y == 0 else 'B'}"
        self.last_action = (desc, (46, 125, 50))

        self.movement_step += 1
        return len(self.movement_movements) == 0

    def _button_rect(self) -> pygame.Rect:
        """Position du bouton d'action (sous la colonne de panneaux, à gauche)."""
        n = max(1, len(self.game.players))
        y = TOP_H + 8 + n * (self._panel_h() + 8) + 6
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
        """Applique une étape d'aspiration sur le plateau et l'affiche.

        Retourne True si toutes les étapes ont été appliquées.
        """
        if not self.aspiration_movements:
            return True
        step = self.aspiration_movements.pop(0)
        self.game.apply_slipstream_step(step)
        desc = ", ".join(f"{self._short_id(r)} {fx}\u2192{tx}"
                         for r, fx, _fl, tx, _tl in step)
        noun = "coureur" if len(step) == 1 else "coureurs"
        self.last_action = (f"Aspiration : {len(step)} {noun} +1 case ({desc})",
                            (230, 126, 0))
        self.aspiration_step += 1
        return len(self.aspiration_movements) == 0

    def _finish_aspiration_phase(self):
        """Passe en phase terminale : fatigue, victoire éventuelle, nouveau tour."""
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_movements = []
        self.game.current_phase = Phase.TERMINAL
        tired = self.game._assign_fatigue_cards()
        if tired:
            names = ", ".join(self._short_id(r) for r in tired)
            verb = "re\u00e7oit" if len(tired) == 1 else "re\u00e7oivent"
            self.last_action = (f"Fatigue : {names} {verb} une carte 2F (case devant vide)",
                                (180, 90, 0))
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
                elif self.game is None:
                    self._menu_event(event)
                else:
                    self._game_event(event)

            if self.game is None:
                self.screen.fill((28, 32, 38))
                self._draw_header()
                self._draw_menu()
            else:
                self.screen.fill(WHITE)
                self._draw_track()
                self._draw_runners()
                self._draw_ui()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def _game_event(self, event):
        """Événements quand une partie est en cours."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if not self._try_button_click(event.pos):
                    if self.game.current_phase == Phase.ENERGY and self.show_hands:
                        self._handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._select_stage(self.stage)
            elif event.key == pygame.K_ESCAPE:
                self.game = None  # retour au menu de sélection d'étape
            elif event.key == pygame.K_h:
                self.show_hands = not self.show_hands
            elif event.key == pygame.K_d:
                self.show_decks = not self.show_decks
            elif event.key == pygame.K_RETURN:
                self._advance_step()

    # ------------------------------------------------------------------
    # Menu de sélection d'étape
    # ------------------------------------------------------------------

    def _menu_entries(self):
        """Entrées du menu : [(nom, description, code, rect), ...].

        Si la fenêtre est assez large, une colonne de droite est réservée
        à la prévisualisation du tracé de l'étape survolée/sélectionnée.
        """
        from game.game import available_stages
        preview_w = 380 if self.width >= 1100 else 0
        w = min(680, self.width - 60 - preview_w)
        x = 20 if preview_w else (self.width - w) // 2
        y = TOP_H + 46
        entries = []
        for name, desc, code in available_stages():
            rect = pygame.Rect(x, y, w, 58)
            entries.append((name, desc, code, rect))
            y += 66
        return entries

    def _preview_rect(self):
        """Panneau de prévisualisation (colonne de droite du menu) :
        tracé de l'étape + profil d'altitude + image de la carte du jeu."""
        return pygame.Rect(self.width - 350, TOP_H + 40, 330,
                           min(560, self.height - TOP_H - 56))

    def _preview_track_rect(self, rect):
        """Sous-zone du tracé dans le panneau de preview."""
        h = max(120, rect.h - 250)
        return pygame.Rect(rect.x + 10, rect.y + 34, rect.w - 20, h)

    def _preview_profile_rect(self, rect):
        """Sous-zone du profil d'altitude."""
        tr = self._preview_track_rect(rect)
        return pygame.Rect(rect.x + 10, tr.bottom + 8, rect.w - 20, 62)

    def _preview_card_rect(self, rect):
        """Sous-zone de l'image de la carte d'étape (si fournie)."""
        pr = self._preview_profile_rect(rect)
        return pygame.Rect(rect.x + 10, pr.bottom + 8, rect.w - 20,
                           max(80, rect.bottom - pr.bottom - 18))

    def _stage_preview_points(self, name):
        """Polyligne (unités de cases) du tracé d'une étape, mise en cache."""
        if name not in self._preview_cache:
            from game.game import build_stage_track
            from game.track import compute_track_path
            self._preview_cache[name] = compute_track_path(build_stage_track(name), 1.0)
        return self._preview_cache[name]

    def _preview_tile_marks(self, name):
        """[(s au milieu de la tuile, lettre ou None), ...] pour la preview."""
        from game.game import OFFICIAL_STAGES, build_stage_track
        track = build_stage_track(name)
        letters = [c for c in OFFICIAL_STAGES.get(name, "") if c.strip()]
        marks = []
        s = 0.0
        for i, tile in enumerate(track.tiles):
            marks.append((s + tile.length / 2, letters[i] if i < len(letters) else None))
            s += tile.length
        return marks, s  # s final = longueur totale (cases)

    def _draw_menu_preview(self, name, rect):
        """Mini-carte du tracé de l'étape : chemin + séparateurs de tuiles
        + lettres des tuiles (a, b, c...) + départ/arrivée."""
        from game.track import path_point_at
        trect = self._preview_track_rect(rect)
        pts = self._stage_preview_points(name)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        scale = min((trect.w - 16) / max(bb_w, 1e-9), (trect.h - 16) / max(bb_h, 1e-9))
        ox = trect.x + (trect.w - bb_w * scale) / 2 - min(xs) * scale
        oy = trect.y + (trect.h - bb_h * scale) / 2 - min(ys) * scale
        screen_pts = [(ox + px * scale, oy + py * scale) for px, py in pts]

        pygame.draw.rect(self.screen, (45, 50, 58), rect, border_radius=8)
        pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=8)
        title = self.label_font.render(name, True, WHITE)
        self.screen.blit(title, (rect.x + 12, rect.y + 10))

        # Tracé coloré CASE PAR CASE : départ vert, arrivée rouge,
        # montée ROUGE vif, descente BLEU vif, plat gris clair
        from game.game import build_stage_track
        from game.track import CellGeographyType, CellRunType
        track = build_stage_track(name)
        for tile in track.tiles:
            for cell in tile.cells:
                s0 = float(cell.x)
                if cell.run == CellRunType.START:
                    seg_color = (255, 236, 130)  # départ : jaune clair
                elif cell.run == CellRunType.END:
                    seg_color = (240, 210, 60)   # arrivée : jaune vif (différent)
                elif cell.geography == CellGeographyType.UPHILL:
                    seg_color = (220, 50, 50)
                elif cell.geography == CellGeographyType.DOWNHILL:
                    seg_color = (50, 90, 220)
                else:
                    seg_color = (200, 205, 215)
                steps = 3
                seg = []
                for k in range(steps + 1):
                    px, py, _tx, _ty = path_point_at(pts, s0 + k / steps)
                    seg.append((ox + px * scale, oy + py * scale))
                pygame.draw.lines(self.screen, seg_color, False, seg, 5)

        # départ (jaune clair) et arrivée (jaune vif)
        pygame.draw.circle(self.screen, (255, 236, 130), screen_pts[0], 5)
        pygame.draw.circle(self.screen, YELLOW, screen_pts[-1], 5)

        # Séparateurs de tuiles + lettres au milieu de chaque tuile
        marks, total = self._preview_tile_marks(name)
        s = 0.0
        from game.game import build_stage_track
        track = build_stage_track(name)
        for i, tile in enumerate(track.tiles):
            s += tile.length
            if i < len(track.tiles) - 1:  # petite ligne à la jonction
                px, py, tx, ty = path_point_at(pts, s)
                sx, sy = ox + px * scale, oy + py * scale
                nx, ny = -ty, tx
                pygame.draw.line(self.screen, (120, 125, 135),
                                 (sx + nx * 7, sy + ny * 7), (sx - nx * 7, sy - ny * 7), 1)
        for s_mid, letter in marks:
            if not letter:
                continue
            px, py, tx, ty = path_point_at(pts, s_mid)
            sx, sy = ox + px * scale, oy + py * scale
            nx, ny = -ty, tx
            lbl = self.small_font.render(letter, True, (170, 175, 185))
            self.screen.blit(lbl, (sx + nx * 10 - 3, sy + ny * 10 - 5))

        # Profil d'altitude de l'étape (montées +1 / descentes -1 par case)
        self._draw_profile(name, self._preview_profile_rect(rect))
        # Image de la vraie carte d'étape si fournie (assets/stages/<nom>.jpg)
        self._draw_stage_card(name, self._preview_card_rect(rect))

    def _stage_profile(self, name):
        """Altitude relative case par case : montée +1, descente -1, plat 0."""
        if name not in self._profile_cache:
            from game.game import build_stage_track
            from game.track import CellGeographyType
            track = build_stage_track(name)
            alt = [0]
            for tile in track.tiles:
                for cell in tile.cells:
                    g = cell.geography
                    alt.append(alt[-1] + (1 if g == CellGeographyType.UPHILL
                                           else -1 if g == CellGeographyType.DOWNHILL
                                           else 0))
            self._profile_cache[name] = alt
        return self._profile_cache[name]

    def _draw_profile(self, name, rect):
        """Dessine le profil d'altitude de l'étape dans son sous-panneau."""
        alt = self._stage_profile(name)
        pygame.draw.rect(self.screen, (38, 42, 50), rect, border_radius=6)
        lbl = self.small_font.render(f"Profil  (alt. {min(alt)} .. {max(alt)})",
                                     True, (150, 155, 165))
        self.screen.blit(lbl, (rect.x + 6, rect.y + 3))
        lo, hi = min(alt), max(alt)
        span = max(hi - lo, 1)
        inner = pygame.Rect(rect.x + 6, rect.y + 16, rect.w - 12, rect.h - 22)
        n = len(alt) - 1
        pts = [(inner.x + inner.w * i / n,
                inner.bottom - (a - lo) / span * inner.h) for i, a in enumerate(alt)]
        pygame.draw.polygon(self.screen, (96, 140, 90),
                            pts + [(pts[-1][0], inner.bottom), (pts[0][0], inner.bottom)])
        pygame.draw.lines(self.screen, (180, 220, 180), False, pts, 2)

    def _stage_card_path(self, name):
        """Chemin de l'image de la carte d'étape si elle a été déposée dans
        assets/stages/ (ex. 'La Haut Montagne.jpg' ou 'la_haut_montagne.png')."""
        import os
        import re
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'assets', 'stages')
        slug = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')
        for cand in (name, slug):
            for ext in ('.png', '.jpg', '.jpeg'):
                p = os.path.join(base, cand + ext)
                if os.path.exists(p):
                    return p
        return None

    def _draw_stage_card(self, name, rect):
        """Affiche l'image de la vraie carte du jeu à côté de la preview,
        si elle est présente dans assets/stages/."""
        path = self._stage_card_path(name)
        if path:
            try:
                img = pygame.image.load(path)
                scale = min(rect.w / img.get_width(), rect.h / img.get_height())
                img = pygame.transform.smoothscale(
                    img, (max(1, int(img.get_width() * scale)),
                          max(1, int(img.get_height() * scale))))
                self.screen.blit(img, (rect.x + (rect.w - img.get_width()) // 2,
                                       rect.y + (rect.h - img.get_height()) // 2))
                return
            except Exception:
                pass
        hint = self.small_font.render("carte du jeu : assets/stages/<etape>.jpg",
                                      True, (110, 115, 125))
        self.screen.blit(hint, (rect.x + 6, rect.y + rect.h // 2 - 6))

    def _draw_menu(self):
        """Menu de sélection (affiché quand self.game is None)."""
        mouse = pygame.mouse.get_pos()
        if self.menu_step == "players":
            self._draw_players_menu(mouse)
            return
        title = self.title_font.render("Choisis ton étape", True, WHITE)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, HEADER_H + 14))
        hint = self.label_font.render("Clic ou flèches + ENTRÉE", True, (150, 155, 165))
        self.screen.blit(hint, ((self.width - hint.get_width()) // 2, HEADER_H + 52))

        entries = self._menu_entries()
        for i, (name, desc, code, rect) in enumerate(entries):
            selected = (i == self.menu_index)
            hovered = rect.collidepoint(mouse)
            fill = (70, 80, 95) if (selected or hovered) else (45, 50, 58)
            border = (235, 60, 60) if (selected or hovered) else (90, 95, 105)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, width=2 if (selected or hovered) else 1,
                             border_radius=8)
            name_surf = self.phase_font.render(name, True, WHITE)
            self.screen.blit(name_surf, (rect.x + 16, rect.y + 8))
            desc_surf = self.label_font.render(desc, True, (180, 185, 195))
            self.screen.blit(desc_surf, (rect.x + 16, rect.y + 32))
            if code:
                code_surf = self.small_font.render(code, True, (120, 125, 135))
                self.screen.blit(code_surf, (rect.right - 12 - code_surf.get_width(), rect.y + 10))

        # Prévisualisation du tracé de l'étape sélectionnée (grandes fenêtres)
        if self.width >= 1100 and entries:
            self._draw_menu_preview(entries[self.menu_index][0], self._preview_rect())

    def _draw_players_menu(self, mouse):
        """Étape 2 du menu : choix du nombre de joueurs (2-4)."""
        title = self.title_font.render(f"{self._pending_stage} — combien de joueurs ?",
                                       True, WHITE)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, HEADER_H + 14))
        hint = self.label_font.render("Clic ou flèches gauche/droite + ENTRÉE (Échap = retour)",
                                      True, (150, 155, 165))
        self.screen.blit(hint, ((self.width - hint.get_width()) // 2, HEADER_H + 52))
        for count, rect in self._player_count_rects():
            selected = (count == self.player_count)
            hovered = rect.collidepoint(mouse)
            fill = (70, 80, 95) if (selected or hovered) else (45, 50, 58)
            border = (235, 60, 60) if (selected or hovered) else (90, 95, 105)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, width=2 if (selected or hovered) else 1,
                             border_radius=8)
            n_surf = self.big_font.render(str(count), True, WHITE)
            self.screen.blit(n_surf, (rect.centerx - n_surf.get_width() // 2,
                                      rect.centery - n_surf.get_height() // 2))
        if self.width >= 1100 and self._pending_stage:
            self._draw_menu_preview(self._pending_stage, self._preview_rect())

    def _player_count_rects(self):
        """Boutons 2/3/4 joueurs de l'étape 'players' du menu."""
        rects = []
        total_w = 3 * 110 + 2 * 20
        x = (self.width - total_w) // 2
        y = TOP_H + 220
        for count in (2, 3, 4):
            rects.append((count, pygame.Rect(x, y, 110, 80)))
            x += 130
        return rects

    def _select_stage(self, name: str):
        """Démarre une partie sur l'étape choisie (depuis le menu ou R)."""
        self.stage = name
        self.game = Game(stage=name, player_count=self.player_count)
        self.showing_movement = False
        self.movement_step = 0
        self.movement_total = 0
        self.movement_movements = []
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_total = 0
        self.aspiration_movements = []
        self.played_display_index = {}
        self.last_action = None

    def _menu_event(self, event):
        """Événements du menu (étape 1 : choix de l'étape, étape 2 : nb joueurs)."""
        if self.menu_step == "players":
            self._players_menu_event(event)
            return
        entries = self._menu_entries()
        mouse = pygame.mouse.get_pos()
        hovered = None
        for i, (_name, _desc, _code, rect) in enumerate(entries):
            if rect.collidepoint(mouse):
                hovered = i
        if hovered is not None:
            self.menu_index = hovered
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hovered is not None:
            self._pending_stage = entries[hovered][0]
            self.menu_step = "players"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(entries)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(entries)
            elif event.key == pygame.K_RETURN:
                self._pending_stage = entries[self.menu_index][0]
                self.menu_step = "players"

    def _players_menu_event(self, event):
        """Étape 2 du menu : choix du nombre de joueurs (2-4)."""
        counts = [2, 3, 4]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for count, rect in self._player_count_rects():
                if rect.collidepoint(event.pos):
                    self.player_count = count
                    self._select_stage(self._pending_stage)
                    return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.player_count = counts[max(0, counts.index(self.player_count) - 1)]
            elif event.key == pygame.K_RIGHT:
                self.player_count = counts[min(len(counts) - 1, counts.index(self.player_count) + 1)]
            elif event.key == pygame.K_RETURN:
                self._select_stage(self._pending_stage)
            elif event.key == pygame.K_ESCAPE:
                self.menu_step = "stage"

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

        # Teinte des cases spéciales : départ (vert), arrivée (rouge),
        # montées/descentes par case (les virages se voient à leur forme)
        for x_cell in range(track.length):
            run = track.run_at(x_cell)
            cell_geo = track.geography_at(x_cell)
            if run == CellRunType.START:
                color = (200, 240, 200)
            elif run == CellRunType.END:
                color = (250, 205, 205)
            elif cell_geo == CellGeographyType.UPHILL:
                color = UPHILL_FILL
            elif cell_geo == CellGeographyType.DOWNHILL:
                color = DOWNHILL_FILL
            else:
                continue
            sample = []
            for k in range(9):
                px, py, _tx, _ty = self._path_at(geo, x_cell * cell + cell * k / 8)
                sample.append((px, py))
            pygame.draw.lines(self.screen, color, False, sample, width=2 * half)

            # Marqueurs montée/descente : triangles à l'extérieur droit de la route
            cell_geo = track.geography_at(x_cell)
            if cell_geo in (CellGeographyType.UPHILL, CellGeographyType.DOWNHILL):
                px, py, tx, ty = self._path_at(geo, (x_cell + 0.5) * cell)
                nx, ny = -ty, tx
                mx = px + nx * (half + 12)
                my = py + ny * (half + 12)
                forward = 1 if cell_geo == CellGeographyType.UPHILL else -1
                pts = [(mx + tx * 7 * forward, my + ty * 7 * forward),
                       (mx + nx * 5, my + ny * 5),
                       (mx - nx * 5, my - ny * 5)]
                arrow_color = UPHILL_ARROW if cell_geo == CellGeographyType.UPHILL else DOWNHILL_ARROW
                pygame.draw.polygon(self.screen, arrow_color, pts)

        # Ligne médiane (séparation des files) + quadrillage des cases
        pygame.draw.lines(self.screen, WHITE, False, pts, 3)
        for k in range(track.length + 1):
            px, py, tx, ty = self._path_at(geo, k * cell)
            nx, ny = -ty, tx
            pygame.draw.line(self.screen, WHITE,
                             (px + nx * half, py + ny * half),
                             (px - nx * half, py - ny * half), 1)

        # Lignes de DÉPART (bande jaune) et d'ARRIVÉE (damier noir/blanc),
        # bien visibles en travers de toute la route
        line_specs = [(0.0, "start", "DÉPART"),
                      (track.end_line_x() * cell, "end", "ARRIVÉE")]
        for s, kind, label in line_specs:
            px, py, tx, ty = self._path_at(geo, s)
            nx, ny = -ty, tx
            if kind == "start":
                pygame.draw.line(self.screen, (250, 220, 60),
                                 (px + nx * half, py + ny * half),
                                 (px - nx * half, py - ny * half), 7)
                pygame.draw.line(self.screen, (60, 50, 10),
                                 (px + nx * half, py + ny * half),
                                 (px - nx * half, py - ny * half), 1)
            else:
                n = 8  # damier
                for k in range(n):
                    t0 = -half + 2 * half * k / n
                    t1 = -half + 2 * half * (k + 1) / n
                    c = (25, 25, 25) if k % 2 == 0 else (245, 245, 245)
                    pygame.draw.line(self.screen, c,
                                     (px + nx * t0, py + ny * t0),
                                     (px + nx * t1, py + ny * t1), 7)
            # libellé à l'extérieur droit de la route
            lx, ly = px + nx * (half + 22), py + ny * (half + 22)
            lbl = self.label_font.render(label, True,
                                         (250, 220, 60) if kind == "start" else WHITE)
            self.screen.blit(lbl, (lx - lbl.get_width() // 2, ly - lbl.get_height() // 2))

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

    def _phase_info(self):
        """(nom, description, couleur) de la phase en cours, pour le bandeau."""
        if self.game.game_over and self.game.winner:
            return ("ARRIV\u00c9E !",
                    f"{self.game.winner.color} remporte la course \u2014 appuyez sur R pour recommencer",
                    (180, 40, 40))
        if self.showing_movement:
            return ("PHASE DE MOUVEMENT",
                    "Les coureurs avancent un \u00e0 un, du plus en avant vers l'arri\u00e8re (ENTR\u00c9E ou bouton)",
                    (46, 125, 50))
        if self.showing_aspiration:
            return ("ASPIRATION",
                    "Si exactement une case vide s\u00e9pare deux packs, le pack arri\u00e8re glisse d'une case",
                    (230, 126, 0))
        phase = self.game.current_phase
        if phase == Phase.ENERGY:
            if self.game.all_players_ready():
                return ("PHASE D'\u00c9NERGIE",
                        "Tous les coureurs ont jou\u00e9 \u2014 ENTR\u00c9E ou bouton pour lancer le mouvement",
                        (25, 118, 210))
            return ("PHASE D'\u00c9NERGIE",
                    "Jouez une carte par coureur en cliquant sur elle",
                    (25, 118, 210))
        if phase == Phase.MOVEMENT:
            return ("PHASE DE MOUVEMENT",
                    "Mouvements termin\u00e9s \u2014 ENTR\u00c9E ou bouton pour lancer l'aspiration",
                    (46, 125, 50))
        if phase == Phase.ASPIRATION:
            return ("ASPIRATION", "Calcul des glissements de packs...", (230, 126, 0))
        return ("PHASE TERMINALE", "Fatigue puis nouveau tour", (110, 110, 110))

    def _draw_header(self):
        """Bandeau de titre : fanion, nom du jeu, étape et tour en cours."""
        pygame.draw.rect(self.screen, (28, 32, 38), (0, 0, self.width, HEADER_H))

        # Fanion rouge (le "flamme rouge" qui donne son nom au jeu)
        pygame.draw.rect(self.screen, (200, 200, 200), (18, 12, 3, 38))
        pygame.draw.polygon(self.screen, (215, 45, 45),
                           ((21, 12), (48, 20), (21, 28)))

        # Titre bicolore
        flamme = self.title_font.render("FLAMME ", True, WHITE)
        rouge = self.title_font.render("ROUGE", True, (235, 60, 60))
        ty = (HEADER_H - max(flamme.get_height(), rouge.get_height())) // 2
        self.screen.blit(flamme, (58, ty))
        self.screen.blit(rouge, (58 + flamme.get_width(), ty))

        # Étape et tour, alignés à droite (uniquement quand une partie est en cours)
        if self.game is not None:
            stage_name = STAGE_NAMES.get(self.game.stage, self.game.stage)
            stage_surf = self.label_font.render(stage_name, True, (175, 180, 190))
            turn_surf = self.title_font.render(f"Tour {self.game.turn_count}", True, WHITE)
            turn_x = self.width - 16 - turn_surf.get_width()
            self.screen.blit(turn_surf, (turn_x, (HEADER_H - turn_surf.get_height()) // 2))
            self.screen.blit(stage_surf,
                             (turn_x - 14 - stage_surf.get_width(),
                              (HEADER_H - stage_surf.get_height()) // 2))

    def _draw_phase_band(self):
        """Bandeau de phase : nom + description de la phase, coloré."""
        label, desc, color = self._phase_info()
        rect = pygame.Rect(0, HEADER_H + 4, self.width, PHASE_H)
        pygame.draw.rect(self.screen, color, rect)
        name_surf = self.phase_font.render(label, True, WHITE)
        self.screen.blit(name_surf, (16, rect.y + (PHASE_H - name_surf.get_height()) // 2))
        desc_surf = self.label_font.render(desc, True, (250, 250, 250))
        self.screen.blit(desc_surf,
                         (16 + name_surf.get_width() + 18,
                          rect.y + (PHASE_H - desc_surf.get_height()) // 2))

    def _draw_ui(self):
        self._draw_header()
        self._draw_phase_band()

        info_x = self._left_w() + 16

        # Compteurs du pas-à-pas / de la phase d'énergie
        if self.showing_movement:
            counter_text = self.big_font.render(
                f"Mouvement: {self.movement_step}/{self.movement_total} coureurs", True, BLACK)
            self.screen.blit(counter_text, (info_x, TOP_H + 2))
        elif self.showing_aspiration:
            counter_text = self.big_font.render(
                f"Aspiration: {self.aspiration_step}/{self.aspiration_total} packs", True, ORANGE)
            self.screen.blit(counter_text, (info_x, TOP_H + 2))
        elif self.game.current_phase == Phase.ENERGY:
            cards_text = self.big_font.render(
                f"Cartes: {self.game.cards_played_this_turn}/{self.game.total_cards_to_play}", True, BLACK)
            self.screen.blit(cards_text, (info_x, TOP_H + 2))

        # Bandeau : ce qui vient d'être fait (mouvement, aspiration, fatigue)
        if self.last_action:
            action_text, action_color = self.last_action
            action_surf = self.label_font.render(action_text, True, action_color)
            pad = 5
            bg = pygame.Rect(info_x - pad, TOP_H + 42 - pad,
                             action_surf.get_width() + 2 * pad,
                             action_surf.get_height() + 2 * pad)
            pygame.draw.rect(self.screen, (245, 245, 240), bg, border_radius=6)
            pygame.draw.rect(self.screen, action_color, bg, width=2, border_radius=6)
            self.screen.blit(action_surf, (info_x, TOP_H + 42))

        # Prochaine étape (prévisualisation)
        if self.showing_movement and self.movement_movements:
            runner, value = self.movement_movements[0]
            eff, reason = self.game.track.effective_steps(runner.x, value)
            if reason:
                text = f"Suivant: {self._short_id(runner)} joue {value} \u2192 {eff} ({reason})"
            else:
                text = f"Suivant: {self._short_id(runner)} joue {value}"
            self.screen.blit(self.font.render(text, True, BLACK), (info_x, TOP_H + 78))
        elif self.showing_aspiration and self.aspiration_movements:
            step = self.aspiration_movements[0]
            desc = ", ".join(f"{self._short_id(r)}:{fx}\u2192{tx}"
                             for r, fx, _fl, tx, _tl in step)
            self.screen.blit(self.font.render(f"Pack: {desc}", True, ORANGE), (info_x, TOP_H + 78))

        # Instructions (haut à droite, sous le bandeau de phase)
        instructions_y = TOP_H + 2
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
                              (UPHILL_FILL, "Mont\u00e9e"),
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
                    # Survol + montagne : montrer le déplacement effectif avant de jouer
                    if hovered:
                        eff, reason = self.game.track.effective_steps(runner.x, card.value)
                        if reason:
                            hint = self.small_font.render(f"\u2192{eff}", True, (180, 90, 0))
                            self.screen.blit(hint, (rect.right - 14, rect.y - 12))

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
            if block_y < TOP_H + INFO_H:
                break  # plus de place au-dessus du bloc infos
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
