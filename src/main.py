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
BUTTONS_H = 100    # hauteur réservée en bas de colonne pour les 2 boutons
BAR_H = 150        # hauteur de la barre du bas (cartes + log + boutons)
CARD_H_MAIN = 36   # hauteur fixe des cartes à sélectionner (le bloc s'adapte, pas l'inverse)
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


def _dense_points(pts, length, per_cell=6):
    """Échantillonne une polyligne de tuile en points denses (pour un tracé lisse)."""
    from game.track import path_point_at
    return [path_point_at(pts, k / per_cell)[:2] for k in range(length * per_cell + 1)]

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
        self.bold_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 12)

        self.stage = stage  # None -> menu de sélection d'étape affiché
        self.player_count = 2  # nombre de joueurs choisi au menu (2-4)
        self.game = Game(stage=stage, player_count=self.player_count) if stage else None
        self.menu_index = 0
        self.menu_step = "stage"  # "stage" -> "players" / "editor"
        self._pending_stage = None
        self._pending_code = None  # code perso (JSON) si l'entrée choisie est un circuit perso
        self.show_podium = True
        self.editor_code = "a"  # code de la piste en cours d'édition (éditeur)
        self.editor_hover_letter = 'a'  # tuile prévisualisée dans l'éditeur
        self.editor_message = ""  # message (sauvegarde/chargement) dans l'éditeur
        self.editor_naming = False  # saisie du nom de parcours en cours
        self.editor_name = ""       # nom saisi pour la sauvegarde
        import os as _os
        self.saves_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                       '..', 'saves')
        self._preview_cache = {}  # nom d'étape -> polyligne de prévisualisation
        self._profile_cache = {}  # nom d'étape -> profil d'altitude
        self.show_hands = True
        self.played_display_index = {}  # runner_id -> position d'origine de la carte jouée
        self.show_decks = False  # Panneau des cartes restantes (touche D)
        self.show_history = False  # Panneau historique des coups (touche J, overlay)
        self.current_player_idx = 0  # joueur dont les cartes sont affichées (barre du bas)
        self.log_scroll = 0  # scroll de l'écran des logs (molette au-dessus)
        self._pressed_button = None  # bouton actuellement enfoncé (clic maintenu)
        self.zoom = 1.0     # zoom sur le circuit (+/- ou molette)
        self.pan_x = 0.0    # panoramique horizontal (flèches ou clic droit)
        self.pan_y = 0.0
        self._cam_drag = None  # dernier point du drag caméra (clic gauche sur le parcours)
        self._cam_drag_moved = False
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
        """Marge gauche (plus de colonne de panneaux : les cartes sont en bas)."""
        return 8

    def _bar_rect(self) -> pygame.Rect:
        """Barre du bas : panneau de cartes (un joueur à la fois) à gauche,
        panneau de log à droite, boutons à l'extrême droite."""
        return pygame.Rect(4, self.height - BAR_H - 30, self.width - 10, BAR_H)

    def _card_panel_rect(self) -> pygame.Rect:
        """Panneau des cartes du joueur en cours (en bas à gauche), compact :
        largeur ajustée au contenu, cartes de taille fixe."""
        bar = self._bar_rect()
        w = PANEL_PAD + 88 + 5 * (CARD_W + CARD_GAP) - CARD_GAP + PANEL_PAD + 6
        return pygame.Rect(bar.x + 6, bar.y + 22, w, bar.h - 28)

    def _log_panel_rect(self) -> pygame.Rect:
        """Écran des logs entre le panneau de cartes et les boutons de droite
        (scrollable à la molette)."""
        bar = self._bar_rect()
        card = self._card_panel_rect()
        btns = self._purple_button_rects()["random"]
        return pygame.Rect(card.right + 8, bar.y + 6, btns.x - 8 - (card.right + 8),
                           bar.h - 12)

    def _player_tab_rects(self):
        """Onglets des joueurs au-dessus du panneau de cartes (changer de joueur)."""
        bar = self._bar_rect()
        card = self._card_panel_rect()
        return [pygame.Rect(card.x + i * 76, bar.y + 4, 72, 20)
                for i in range(len(self.game.players))]

    def _track_geometry(self) -> dict:
        """Géométrie du circuit (mise en cache), ajustée à la fenêtre.

        Le tracé suit la SÉQUENCE RÉELLE des tuiles (compute_track_path :
        chaque tuile avance de 2 cases, les virages courbent le cap de
        45°/90° selon leur direction), puis est mis à l'échelle et centré
        dans la zone de droite. Chaque case occupe exactement `cell` pixels
        d'arc : les cases restent contiguës, aucun saut.
        """
        key = (self.width, self.height, self.game.stage, round(self.zoom, 4),
               round(self.pan_x, 1), round(self.pan_y, 1))
        if getattr(self, "_geo_key", None) == key:
            return self._geo

        from game.track import compute_track_path
        pts_units = compute_track_path(self.game.track, unit=1.0)

        left = 16
        right = self.width - 12
        top = TOP_H + 8
        bottom = self._bar_rect().y - 34  # la barre du bas est hors du parcours
        avail_w = max(50.0, right - left)
        avail_h = max(50.0, bottom - top)

        xs = [p[0] for p in pts_units]
        ys = [p[1] for p in pts_units]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # marge de 30px de chaque côté pour la demi-largeur de la route
        scale = min((avail_w - 60) / max(bb_w, 1e-9), (avail_h - 60) / max(bb_h, 1e-9))
        cell = max(CELL_MIN, min(CELL_MAX, scale)) * self.zoom  # zoom débride le max
        ox = left + (avail_w - bb_w * cell) / 2 - min(xs) * cell + self.pan_x
        oy = top + (avail_h - bb_h * cell) / 2 - min(ys) * cell + self.pan_y

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
        """Hauteur du panneau de cartes (joueur en cours, en bas à gauche)."""
        return self._card_panel_rect().h

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
        """Géométrie du panneau de cartes DU JOUEUR EN COURS (en bas à gauche).

        Un panneau : en-tête (nom + progression x/2), 2 lignes (Sprinteur /
        Rouleur) avec libellé à gauche et cartes (carte jouée incluse, en
        vert) à droite.
        Retourne [(player, panel_rect, [(runner, label, items, [card_rects])])].
        Utilisé à la fois pour le dessin et pour la détection des clics.
        """
        player = self.game.players[self.current_player_idx]
        panel = self._card_panel_rect()
        panel_h = panel.h
        panel_w = panel.w
        card_h = CARD_H_MAIN  # taille de carte fixe, indépendante du bloc
        label_w = 88  # zone réservée au libellé ("Sprinteur" / "Rouleur")
        card_w = CARD_W

        layout = []
        rows = []
        if True:
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
        """Bouton d'action à l'extrême droite de la barre du bas (sous le violet)."""
        bar = self._bar_rect()
        return pygame.Rect(bar.right - 158, bar.y + 8 + 44, 150, 44)

    def _random_button_rect(self) -> pygame.Rect:
        """Bouton « Tour aléatoire » (violet) en bas à côté des logs."""
        return self._purple_button_rects()["random"]

    def _placement_button_rect(self):
        """(supprimé) Le placement aléatoire se fait via le bouton d'action en phase PLACEMENT."""
        return None

    def _frame_rect(self) -> pygame.Rect:
        """Cadre du parcours (tout l'écran sauf la barre du bas)."""
        bar = self._bar_rect()
        return pygame.Rect(4, TOP_H + 2, self.width - 10, bar.y - TOP_H - 8)

    def _podium_button_rect(self) -> pygame.Rect:
        """Bouton « Podium » dans le bandeau de titre (écran de fin, avec TAB)."""
        return pygame.Rect(self.width - 140, 12, 128, 36)

    def _draw_ui_button(self, rect, label, base_color, mouse, enabled=True, icon=None,
                        pressed=False):
        """Bouton avec effet d'enfoncement léger (ombre en bas) ; au clic,
        le bouton s'enfonce vraiment (ombre inversée). Libellé tronqué pour
        tenir dans le bouton. `icon` : 'loupe', 'groupe' ou 'rect'."""
        hovered = enabled and rect.collidepoint(mouse)
        fill = tuple(min(255, c + 30) for c in base_color) if hovered else base_color
        if not enabled:
            fill = (52, 56, 62)
        if pressed and enabled:
            fill = tuple(max(0, c - 35) for c in fill)  # enfoncé au clic
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        dark = tuple(max(0, c - 45) for c in fill)
        light = tuple(min(255, c + 25) for c in fill)
        if pressed and enabled:
            # enfoncé : ombre en HAUT, liseré en bas (effet inverse)
            pygame.draw.line(self.screen, dark, (rect.x + 6, rect.y + 2),
                             (rect.right - 6, rect.y + 2), 3)
            pygame.draw.line(self.screen, light, (rect.x + 6, rect.bottom - 3),
                             (rect.right - 6, rect.bottom - 3), 1)
        else:
            pygame.draw.line(self.screen, dark, (rect.x + 6, rect.bottom - 3),
                             (rect.right - 6, rect.bottom - 3), 3)
            pygame.draw.line(self.screen, light, (rect.x + 6, rect.y + 2),
                             (rect.right - 6, rect.y + 2), 1)
        pygame.draw.rect(self.screen, dark, rect, width=1, border_radius=8)
        text_color = (120, 124, 130) if not enabled else WHITE
        # icône à gauche
        tx = rect.x + 8
        if icon == "loupe":
            cx, cy = rect.x + 18, rect.centery - 2
            pygame.draw.circle(self.screen, text_color, (cx, cy), 6, 2)
            pygame.draw.line(self.screen, text_color, (cx + 4, cy + 4),
                             (cx + 9, cy + 9), 2)
            tx = rect.x + 32
        elif icon == "rect":  # logo vue d'ensemble : un rectangle (fit écran)
            cx, cy = rect.x + 18, rect.centery
            pygame.draw.rect(self.screen, text_color,
                             (cx - 8, cy - 6, 16, 12), 2, border_radius=2)
            pygame.draw.rect(self.screen, text_color,
                             (cx - 3, cy - 2, 6, 4), 1, border_radius=1)
            tx = rect.x + 32
        elif icon == "groupe":
            cy = rect.centery
            for dx, r in ((-6, 4), (0, 5), (6, 4)):
                pygame.draw.circle(self.screen, text_color, (rect.x + 18 + dx, cy), r)
            tx = rect.x + 34
        # libellé tronqué pour tenir dans le bouton
        max_w = rect.right - 6 - tx
        while label and self.small_font.render(label, True, (0, 0, 0)).get_width() > max_w:
            label = label[:-1]
        surf = self.small_font.render(label, True, text_color)
        self.screen.blit(surf, (tx + (max_w - surf.get_width()) // 2,
                                rect.centery - surf.get_height() // 2))

    def _frame_button_rects(self):
        """Boutons caméra à côté de la légende, en bas à droite du cadre :
        Tête de course (loupe), Peloton (groupe), Vue d'ensemble (dezoom)."""
        frame = self._frame_rect()
        w, h, gap = 150, 30, 6
        y = frame.bottom - h - 6
        return {"tete": pygame.Rect(frame.right - 8 - w, y, w, h),
                "peloton": pygame.Rect(frame.right - 8 - 2 * w - gap, y, w, h),
                "ensemble": pygame.Rect(frame.right - 8 - 3 * w - 2 * gap, y, w, h)}

    def _purple_button_rects(self):
        """Bouton violet en bas à droite de la barre, à côté des logs :
        Tour aléatoire (au-dessus du bouton d'action)."""
        bar = self._bar_rect()
        w = 150
        x = bar.right - w - 8
        return {"random": pygame.Rect(x, bar.y + 8, w, 38)}

    def _camera_button_rects(self):
        """(compat) boutons caméra = ceux du cadre du parcours."""
        r = self._frame_button_rects()
        return {"peloton": r["peloton"], "ensemble": r["ensemble"]}

    def _camera_button_at(self, pos):
        for key, rect in self._camera_button_rects().items():
            if rect.collidepoint(pos):
                return key
        return None

    def _center_camera_on(self, x_cell):
        """Zoom x2 et centre la caméra sur la case x_cell du tracé."""
        self.zoom = 2.0
        geo = self._track_geometry()  # recalculée avec le nouveau zoom
        s = (x_cell + 0.5) * geo["cell"]  # abscisse calculée AVEC le nouveau cell
        px, py, _tx, _ty = self._path_at(geo, s)
        frame = self._frame_rect()
        target_x = frame.x + frame.w / 2
        target_y = frame.y + frame.h / 2
        self.pan_x += target_x - px
        self.pan_y += target_y - py

    def _zoom_on_leader(self):
        """Bouton Tête de course : zoom sur le coureur le plus en avant (file A)."""
        runners = self.game.track.get_all_runners()
        if not runners:
            return
        lead = max(runners, key=lambda t: (t[0], -t[1]))
        self._center_camera_on(lead[0])

    def _zoom_on_peloton(self):
        """Bouton Peloton : zoom sur le plus gros pack (groupe de coureurs
        sans case vide entre eux), centré au milieu du pack."""
        pos = {r.id: (r.x, r.y) for _x, _y, r in self.game.track.get_all_runners()}
        if not pos:
            return
        packs = self.game.track._packs_from_positions(pos)
        if not packs:
            return
        biggest = max(packs, key=len)
        avg_x = sum(pos[rid][0] for rid in biggest) / len(biggest)
        self._center_camera_on(avg_x)

    def _button_info(self):
        """(libellé, couleur) du bouton d'action, ou None s'il n'y en a pas.

        Le bouton est l'équivalent cliquable de la touche ENTRÉE :
        lancer le mouvement, puis avancer un coureur / un pack à la fois.
        """
        if self.game.current_phase == Phase.PLACEMENT:
            return ("Placement aléatoire", (126, 87, 194))
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
        """Gère un clic sur les boutons d'action. Retourne True si consommé."""
        if not self.game.game_over and self._random_button_rect().collidepoint(pos):
            self._play_random_turn()
            return True
        info = self._button_info()
        if info is None or not self._button_rect().collidepoint(pos):
            return False
        self._advance_step()
        return True

    def _play_random_turn(self):
        """Bouton « Tour aléatoire » : placement auto si besoin, une carte au
        hasard par coureur, puis mouvement + aspiration + fatigue d'un coup."""
        import random
        game = self.game
        if game is None or game.game_over:
            return
        if game.current_phase == Phase.PLACEMENT:
            game.auto_place_riders()
        if game.current_phase == Phase.ENERGY:
            for player in game.players:
                for runner in player.get_runners():
                    if game.cards_played_per_runner.get(runner.id, 0) < 1 and runner.hand:
                        game.play_card(player, runner, random.choice(runner.hand))
        if game.current_phase == Phase.ENERGY and game.all_players_ready():
            game.apply_movement_steps(game.resolve_movement_phase())  # phase -> MOVEMENT
            game.apply_aspiration_steps(game.resolve_aspiration_phase())  # -> ASPIRATION
            game.current_phase = Phase.TERMINAL
            game._assign_fatigue_cards()
            if game._check_win_condition():
                game.game_over = True
            else:
                game._cleanup_hands()
                game.start_turn()
        # reset de l'affichage pas-à-pas
        self.showing_movement = False
        self.showing_aspiration = False
        self.movement_step = self.movement_total = 0
        self.aspiration_step = self.aspiration_total = 0
        self.played_display_index = {r.id: 0 for p in game.players for r in p.get_runners()}
        self.last_action = (f"Tour {game.turn_count} joué en aléatoire", (126, 87, 194))

    def _advance_step(self):
        """Avance d'une étape (bouton ou ENTRÉE) selon l'état courant."""
        if self.game.current_phase == Phase.PLACEMENT:
            self.game.auto_place_riders()  # option "placement au hasard"
        elif self.game.current_phase == Phase.ENERGY and self.game.all_players_ready():
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
                # cadre autour de la zone du parcours (tout le reste que la barre du bas)
                frame = self._frame_rect()
                pygame.draw.rect(self.screen, (238, 240, 244), frame, border_radius=10)
                pygame.draw.rect(self.screen, (160, 166, 176), frame, width=2,
                                 border_radius=10)
                # le tracé ne s'affiche QUE dans le cadre du parcours
                self.screen.set_clip(frame)
                self._draw_track()
                self._draw_runners()
                self._draw_unplaced_runners()  # réserve aussi clippée dans le cadre
                self.screen.set_clip(None)
                self._draw_ui()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def _game_event(self, event):
        """Événements quand une partie est en cours."""
        if event.type == pygame.MOUSEWHEEL:
            # molette au-dessus des logs -> scroll de l'historique, sinon zoom
            # (les events MOUSEWHEEL n'ont pas de pos fiable : on prend la souris)
            if self._log_panel_rect().collidepoint(pygame.mouse.get_pos()):
                # scroll vers le haut (y>0) = remonter dans l'historique
                rect = self._log_panel_rect()
                max_lines = max(1, (rect.bottom - rect.y - 28) // 15)
                max_scroll = max(0, len(self._history_lines()) - max_lines)
                self.log_scroll = max(0, min(max_scroll, self.log_scroll + event.y))
            else:
                self.zoom = min(3.0, max(0.5, self.zoom * (1.25 if event.y > 0 else 0.8)))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._cam_drag = event.pos  # début du drag caméra (clic droit)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self._cam_drag = None
        elif event.type == pygame.MOUSEMOTION and self._cam_drag is not None:
            dx = event.pos[0] - self._cam_drag[0]
            dy = event.pos[1] - self._cam_drag[1]
            self.pan_x += dx
            self.pan_y += dy
            if math.hypot(dx, dy) > 2:
                self._cam_drag_moved = True
            self._cam_drag = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._cam_drag is not None:
            # clic gauche sur le parcours sans déplacer = clic simple (placement)
            if not self._cam_drag_moved and self.game.current_phase == Phase.PLACEMENT:
                self._placement_click(event.pos)
            self._cam_drag = None
            self._cam_drag_moved = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._pressed_button = None  # relâche le bouton enfoncé
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                fbtns = self._frame_button_rects()
                hit = None
                for key, rect in fbtns.items():
                    if rect.collidepoint(event.pos):
                        hit = key
                        break
                if hit is None and self._random_button_rect().collidepoint(event.pos):
                    hit = "random"
                if hit is None and self._button_rect().collidepoint(event.pos):
                    hit = "action"
                if hit is None and self.game.game_over and self._podium_button_rect().collidepoint(event.pos):
                    hit = "podium"
                self._pressed_button = hit
                if hit is not None:
                    # actions des boutons (inchangé)
                    if hit == "podium":
                        self.show_podium = not self.show_podium
                    elif hit == "ensemble" and not self.game.game_over:
                        self.zoom, self.pan_x, self.pan_y = 1.0, 0.0, 0.0
                    elif hit == "tete" and not self.game.game_over:
                        self._zoom_on_leader()
                    elif hit == "peloton" and not self.game.game_over:
                        self._zoom_on_peloton()
                    elif hit == "random" and not self.game.game_over:
                        self._play_random_turn()
                    elif hit == "action":
                        self._try_button_click(event.pos)
                    return
                if self._frame_rect().collidepoint(event.pos):
                    # clic GAUCHE sur le parcours = début du drag caméra
                    self._cam_drag = event.pos
                    self._cam_drag_moved = False
                    return
                if not self._try_button_click(event.pos):
                    if self.game.current_phase == Phase.PLACEMENT:
                        self._placement_click(event.pos)
                    elif self.game.current_phase == Phase.ENERGY and self.show_hands:
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
            elif event.key == pygame.K_j:
                self.show_history = not self.show_history
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.zoom = min(3.0, self.zoom * 1.25)   # zoom +
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.zoom = max(0.5, self.zoom / 1.25)   # zoom -
            elif event.key == pygame.K_LEFT:
                self.pan_x += 60
            elif event.key == pygame.K_RIGHT:
                self.pan_x -= 60
            elif event.key == pygame.K_UP:
                self.pan_y += 60
            elif event.key == pygame.K_DOWN:
                self.pan_y -= 60
            elif event.key == pygame.K_TAB and self.game.game_over:
                self.show_podium = not self.show_podium  # podium <-> circuit final
            elif event.key == pygame.K_RETURN:
                self._advance_step()

    # ------------------------------------------------------------------
    # Menu de sélection d'étape
    # ------------------------------------------------------------------

    def _menu_entries(self):
        """Entrées du menu, par catégories :
        [("Circuits du jeu de base", header), 6 étapes officielles,
         ("Circuits perso", header), 1 entrée par JSON de saves/,
         ("Créer un circuit", bouton roue crantée -> éditeur)].
        Chaque entrée = (nom, description, code, rect, kind) avec
        kind in {"header", "base", "perso", "editor"}.
        """
        from game.game import available_stages, list_saved_tracks
        preview_w = 380 if self.width >= 1100 else 0
        w = min(680, self.width - 60 - preview_w)
        x = 20 if preview_w else (self.width - w) // 2
        base = available_stages()
        perso = list_saved_tracks(self.saves_dir)
        n_entries = len(base) + len(perso) + 1
        n_headers = 2
        header_h = 26
        avail = self.height - TOP_H - 56
        row = min(58, max(30, (avail - n_headers * (header_h + 8) - n_entries * 8)
                          // max(n_entries, 1)))
        y = TOP_H + 46
        entries = []

        def add(name, desc, code, kind, h):
            nonlocal y
            rect = pygame.Rect(x, y, w, h)
            entries.append((name, desc, code, rect, kind))
            y += h + 8

        add("— Circuits du jeu de base —", "", "", "header", header_h)
        for name, desc, code in base:
            add(name, desc, code, "base", row)
        add("— Circuits perso (saves/*.json) —", "", "", "header", header_h)
        for s in perso:
            add(s["name"], f"{len(s['code'])} tuiles · code {s['code']}", s["code"],
                "perso", row)
        add("Créer un circuit", "éditeur de piste (roue crantée)", "", "editor", row)
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

    def _stage_preview_points(self, name, code=None):
        """Polyligne (unités de cases) du tracé d'une étape ou d'un code perso."""
        key = ("code", code) if code else name
        if key not in self._preview_cache:
            from game.game import build_stage_track, build_track_from_code
            from game.track import compute_track_path
            track = build_track_from_code(code) if code else build_stage_track(name)
            self._preview_cache[key] = compute_track_path(track, 1.0)
        return self._preview_cache[key]

    def _preview_tile_marks(self, name, code=None):
        """[(s au milieu de la tuile, lettre ou None), ...] pour la preview."""
        from game.game import OFFICIAL_STAGES, build_stage_track, build_track_from_code
        track = build_track_from_code(code) if code else build_stage_track(name)
        letters = [c for c in (code or OFFICIAL_STAGES.get(name, "")) if c.strip()]
        marks = []
        s = 0.0
        for i, tile in enumerate(track.tiles):
            marks.append((s + tile.length / 2, letters[i] if i < len(letters) else None))
            s += tile.length
        return marks, s  # s final = longueur totale (cases)

    def _draw_menu_preview(self, name, rect, code=None):
        """Mini-carte du tracé de l'étape (ou du code perso) : chemin coloré
        case par case + lettres des tuiles (a, b, c...) + départ/arrivée."""
        from game.track import path_point_at
        trect = self._preview_track_rect(rect)
        pts = self._stage_preview_points(name, code=code)
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

        # Tracé coloré CASE PAR CASE : départ jaune clair, arrivée jaune vif,
        # montée ROUGE vif, descente BLEU vif, plat gris clair
        from game.game import build_stage_track, build_track_from_code
        from game.track import CellGeographyType, CellRunType
        track = build_track_from_code(code) if code else build_stage_track(name)
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
        marks, total = self._preview_tile_marks(name, code=code)
        s = 0.0
        from game.game import build_stage_track, build_track_from_code
        track = build_track_from_code(code) if code else build_stage_track(name)
        for i, tile in enumerate(track.tiles):
            s += tile.length
            if i < len(track.tiles) - 1:  # petite ligne à la jonction
                px, py, tx, ty = path_point_at(pts, s)
                sx, sy = ox + px * scale, oy + py * scale
                nx, ny = -ty, tx
                pygame.draw.line(self.screen, (120, 125, 135),
                                 (sx + nx * 7, sy + ny * 7), (sx - nx * 7, sy - ny * 7), 1)
        # lettres des tuiles (a, b, c...) au milieu de chaque tuile
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

    # ------------------------------------------------------------------
    # Éditeur de piste
    # ------------------------------------------------------------------

    EDITOR_LETTERS = "abcdefghijklmnopqrstu"

    def _editor_append(self, ch):
        """Ajoute une tuile au parcours édité.

        Règles : la tuile de départ (a/A) reste en 1re position — cliquer
        sur a ou A bascule sa face ; la tuile d'arrivée (u/U) est toujours la
        DERNIÈRE — cliquer sur u/U bascule sa face si déjà présente, et toute
        autre tuile ajoutée après l'arrivée s'insère juste avant elle.
        """
        if ch.lower() not in self.EDITOR_LETTERS:
            return
        code = self.editor_code
        # une fois l'arrivée placée (dernière tuile), on ne peut plus rien
        # ajouter : seule la tuile d'arrivée reste modifiable (u <-> U)
        if code and code[-1].lower() == 'u' and ch.lower() != 'u':
            return
        if ch.lower() == 'a':
            if code and code[0].lower() == 'a':
                code = ch + code[1:]          # bascule a <-> A en 1re position
            else:
                code = ch + code              # départ toujours en premier
        elif ch.lower() == 'u':
            if code and code[-1].lower() == 'u':
                code = code[:-1] + ch         # bascule u <-> U en dernière position
            else:
                code = code + ch              # arrivée toujours en dernier
        else:
            if code and code[-1].lower() == 'u':
                code = code[:-1] + ch + code[-1]  # on insère avant l'arrivée
            else:
                code = code + ch
        self.editor_code = code
        self._preview_cache.pop("__editor__", None)
        self._profile_cache.pop("__editor__", None)

    def _editor_pop(self):
        if len(self.editor_code) > 1:  # on garde au moins la tuile départ
            self.editor_code = self.editor_code[:-1]
            self._preview_cache.pop("__editor__", None)
            self._profile_cache.pop("__editor__", None)

    def _editor_clear(self):
        self.editor_code = "a"
        self._preview_cache.pop("__editor__", None)
        self._profile_cache.pop("__editor__", None)

    def _editor_play(self):
        """Lance une partie sur le code édité (départ/arrivée auto-ajoutés)."""
        code = self.editor_code
        if code[0].lower() != 'a':
            code = 'a' + code
        if code[-1].lower() != 'u':
            code += 'u'
        self.stage = "Éditeur de piste"
        self.game = Game(stage=self.stage, player_count=self.player_count,
                         auto_place=False, custom_code=code)
        self.menu_step = "stage"
        self.showing_movement = False
        self.showing_aspiration = False
        self.played_display_index = {}
        self.last_action = None
        self.show_podium = True

    def _editor_palette_geom(self):
        """Géométrie de la palette : grosses tuiles qui occupent la gauche,
        hauteur adaptée pour tenir dans la fenêtre (boutons réservés en bas)."""
        cols = 6
        gap = 4
        label_h = 16
        x0, y0 = 20, TOP_H + 96
        bw = 118
        # une ligne de tuiles par catégorie + wrap : 1+3+2+2+1 = 9 lignes
        tile_rows = sum(-(-len(letters) * 2 // cols) for _l, letters in self.EDITOR_CATEGORIES)
        avail = self.height - y0 - 60  # boutons réservés en bas
        bh = min(56, max(24, (avail - tile_rows * gap
                              - len(self.EDITOR_CATEGORIES) * label_h) // tile_rows))
        return x0, y0, bw, bh, gap, cols, label_h

    # catégories de la palette : (nom affiché, lettres) — départ en haut, arrivée en bas
    EDITOR_CATEGORIES = [
        ("Départ", "a"),
        ("Droites", "bcdf lmn".replace(" ", "")),
        ("Virages 90°", "egijop"),
        ("Virages 45°", "hkqrst"),
        ("Arrivée", "u"),
    ]

    def _editor_palette_items(self):
        """Items de la palette : en-têtes de catégories + 42 tuiles (chaque
        tuile suivie de sa face montagne)."""
        items = []
        for label, letters in self.EDITOR_CATEGORIES:
            items.append(("label", label))
            for base in letters:
                items += [("tile", base), ("tile", base.upper())]
        return items

    def _editor_palette_rects(self):
        """Rects des 42 tuiles de la palette, rangées par catégories avec
        en-têtes (exclus ici) — chaque tuile suivie de sa face montagne."""
        x0, y0, bw, bh, gap, cols, label_h = self._editor_palette_geom()
        rects = []
        x, y, col = x0, y0, 0
        for kind, val in self._editor_palette_items():
            if kind == "label":
                if col > 0:  # termine la ligne de tuiles en cours avant le label
                    y += bh + gap
                y += label_h
                x, col = x0, 0
                continue
            rects.append((val, pygame.Rect(x, y, bw, bh)))
            x += bw + gap
            col += 1
            if col >= cols:
                col = 0
                x = x0
                y += bh + gap
        return rects

    def _editor_palette_labels(self):
        """[(texte, x, y)] des noms de catégories à afficher dans la palette."""
        x0, y0, bw, bh, gap, cols, label_h = self._editor_palette_geom()
        labels = []
        x, y, col = x0, y0, 0
        for kind, val in self._editor_palette_items():
            if kind == "label":
                if col > 0:
                    y += bh + gap
                labels.append((val, x, y - 2))
                y += label_h
                x, col = x0, 0
                continue
            x += bw + gap
            col += 1
            if col >= cols:
                col = 0
                x = x0
                y += bh + gap
        return labels

    def _editor_action_rects(self):
        """Boutons d'action de l'éditeur : Retirer, Effacer, Jouer, Retour."""
        labels = [("Retirer", "retirer"), ("Effacer", "effacer"),
                  ("Sauver", "sauver"), ("Charger", "charger"),
                  ("Retour", "retour")]
        if self.width < 1100:  # pas de panneau d'aperçu à droite -> JOUER à gauche
            labels.insert(4, ("JOUER", "jouer"))
        x0, y0, bw, bh, gap, cols, label_h = self._editor_palette_geom()
        rects = {}
        x = x0
        # sous la palette (dernier bouton de tuile + marge)
        palette = self._editor_palette_rects()
        y = (max(r.bottom for _c, r in palette) + 10) if palette else y0 + 100
        for label, key in labels:
            w = 150 if key == "jouer" else 100
            rects[key] = (label, pygame.Rect(x, y, w, 42))
            x += w + 10
        return rects

    def _editor_preview_panel_rect(self):
        """Panneau de l'aperçu global du parcours (à droite dans l'éditeur)."""
        if self.width < 1100:
            return None
        return pygame.Rect(self.width - 350, TOP_H + 246, 330,
                           max(120, min(560, self.height - TOP_H - 56) - 206))

    def _editor_play_rect(self):
        """Bouton JOUER placé SOUS l'aperçu global du parcours (à droite)."""
        prev = self._editor_preview_panel_rect()
        if prev is None:
            return None
        return pygame.Rect(prev.x, min(prev.bottom + 8, self.height - 52), prev.w, 44)

    def _editor_has_finish(self):
        """True si la tuile d'arrivée (u/U) est placée (toujours en dernier)."""
        return bool(self.editor_code) and self.editor_code[-1].lower() == 'u'

    def _editor_save(self):
        """Sauvegarde le parcours édité en JSON dans saves/, avec le nom saisi
        (ou un nom par défaut horodaté)."""
        import datetime
        from game.game import save_track_json
        name = self.editor_name.strip() or f"parcours_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        path = save_track_json(self.editor_code, self.saves_dir, name=name)
        self.editor_message = f"Sauvegardé : {path}"
        self.editor_naming = False
        self.editor_name = ""

    def _editor_load_latest(self):
        """Charge le parcours sauvegardé le plus récent (saves/*.json)."""
        from game.game import list_saved_tracks
        saved = list_saved_tracks(self.saves_dir)
        if not saved:
            self.editor_message = "Aucun parcours sauvegardé"
            return
        self.editor_code = saved[-1]["code"]
        self.editor_message = f"Chargé : {saved[-1]['name']} ({saved[-1]['code']})"
        self._preview_cache.pop("__editor__", None)
        self._profile_cache.pop("__editor__", None)

    def _editor_event(self, event):
        """Événements de l'éditeur : clic palette/boutons ou clavier."""
        if self.editor_naming:
            # saisie du nom de parcours : ENTRÉE valide, Échap annule
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._editor_save()
                elif event.key == pygame.K_ESCAPE:
                    self.editor_naming = False
                    self.editor_name = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.editor_name = self.editor_name[:-1]
                elif len(self.editor_name) < 40 and event.unicode and event.unicode.isprintable():
                    self.editor_name += event.unicode
            return
        if event.type == pygame.MOUSEMOTION:
            for ch, rect in self._editor_palette_rects():
                if rect.collidepoint(event.pos):
                    self.editor_hover_letter = ch
                    break
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for ch, rect in self._editor_palette_rects():
                if rect.collidepoint(event.pos):
                    self.editor_hover_letter = ch
                    self._editor_append(ch)
                    return
            play_rect = self._editor_play_rect()
            if play_rect is not None and play_rect.collidepoint(event.pos):
                if self._editor_has_finish():
                    self._editor_play()
                return
            for key, (_label, rect) in self._editor_action_rects().items():
                if rect.collidepoint(event.pos):
                    if key in ("jouer", "sauver") and not self._editor_has_finish():
                        return  # grisé : pas de tuile d'arrivée
                    if key == "retirer":
                        self._editor_pop()
                    elif key == "effacer":
                        self._editor_clear()
                    elif key == "sauver":
                        # passe en mode saisie du nom avant de sauvegarder
                        import datetime
                        self.editor_naming = True
                        self.editor_name = f"parcours_{datetime.datetime.now():%Y%m%d_%H%M%S}"
                    elif key == "charger":
                        self._editor_load_latest()
                    elif key == "jouer":
                        self._editor_play()
                    elif key == "retour":
                        self.menu_step = "stage"
                    return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.menu_step = "stage"
            elif event.key == pygame.K_BACKSPACE:
                self._editor_pop()
            elif event.key == pygame.K_RETURN:
                if self._editor_has_finish():
                    self._editor_play()
            else:
                name = pygame.key.name(event.key)
                if len(name) == 1 and name.lower() in self.EDITOR_LETTERS:
                    upper = bool(getattr(event, 'mod', 0) & pygame.KMOD_SHIFT)
                    self._editor_append(name.upper() if upper else name)

    def _editor_track(self):
        from game.game import build_track_from_code
        return build_track_from_code(self.editor_code)

    def _draw_editor(self, mouse):
        """Écran de l'éditeur de piste : palette + code + aperçu + profil."""
        title = self.title_font.render("Éditeur de piste", True, WHITE)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, HEADER_H + 14))
        hint = self.label_font.render(
            "Clique une tuile (ou tape a-u, MAJ = face montagne) · RETOUR = jouer · Échap = retour",
            True, (150, 155, 165))
        self.screen.blit(hint, ((self.width - hint.get_width()) // 2, HEADER_H + 52))

        # code en cours + message (sauvegarde/chargement)
        code_surf = self.font.render(f"Code : {self.editor_code}", True, (240, 210, 60))
        self.screen.blit(code_surf, (20, TOP_H + 66))
        if self.editor_naming:
            # champ de saisie du nom de parcours
            box = pygame.Rect(20 + code_surf.get_width() + 20, TOP_H + 60, 320, 30)
            pygame.draw.rect(self.screen, (24, 28, 34), box, border_radius=6)
            pygame.draw.rect(self.screen, (240, 210, 60), box, width=2, border_radius=6)
            label = self.label_font.render("Nom du parcours : ", True, (150, 155, 165))
            self.screen.blit(label, (box.x, box.y - 20))
            name_surf = self.font.render(self.editor_name + ("|" if pygame.time.get_ticks() // 500 % 2 else ""), True, WHITE)
            self.screen.blit(name_surf, (box.x + 8, box.y + 6))
        elif self.editor_message:
            msg = self.label_font.render(self.editor_message, True, (120, 220, 140))
            self.screen.blit(msg, (20 + code_surf.get_width() + 20, TOP_H + 68))

        # noms des catégories au-dessus de chaque groupe
        for text, x, y in self._editor_palette_labels():
            surf = self.label_font.render(text, True, (150, 155, 165))
            self.screen.blit(surf, (x, y))

        # palette des 42 tuiles : des BOUTS DE PISTE cliquables (forme réelle),
        # avec la lettre en petit dans le coin pour identifier la tuile
        locked = bool(self.editor_code) and self.editor_code[-1].lower() == 'u'
        for ch, rect in self._editor_palette_rects():
            hovered = rect.collidepoint(mouse) and not (locked and ch.lower() != 'u')
            fill = (60, 66, 78)  # même fond pour toutes les tuiles (majuscules comprises)
            if hovered:
                fill = tuple(min(255, c + 35) for c in fill)
            pygame.draw.rect(self.screen, fill, rect, border_radius=6)
            pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=6)
            self._draw_mini_tile(ch, rect.centerx - 10, rect.centery, 1.0, 0.0,
                                 size=rect.h - 14)
            txt = self.small_font.render(ch, True, (200, 205, 215))
            self.screen.blit(txt, (rect.right - 18, rect.y + 5))
            if locked and ch.lower() != 'u':
                # arrivée placée : toutes les autres tuiles sont grisées
                overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                overlay.fill((18, 20, 24, 210))
                self.screen.blit(overlay, rect.topleft)

        # boutons d'action (même rendu enfoncé que dans le jeu ; JOUER/Sauver
        # grisés sans tuile d'arrivée)
        has_finish = self._editor_has_finish()
        for key, (label, rect) in self._editor_action_rects().items():
            disabled = key in ("jouer", "sauver") and not has_finish
            color = (46, 125, 50) if key == "jouer" else (70, 80, 95)
            self._draw_ui_button(rect, label, color, mouse, enabled=not disabled)

        # preview de la tuile survolée (panneau dédié, en haut à droite)
        if self.width >= 1100:
            self._draw_tile_preview(self.editor_hover_letter, self._tile_preview_rect())
            # aperçu du tracé + profil dans le panneau juste en dessous
            prev = self._editor_preview_panel_rect()
            self._draw_editor_preview(prev)
            # bouton JOUER sous l'aperçu global du parcours (grisé sans arrivée)
            self._draw_ui_button(self._editor_play_rect(), "JOUER", (46, 125, 50),
                                 mouse, enabled=self._editor_has_finish())
        else:
            self._draw_tile_preview(self.editor_hover_letter,
                                    pygame.Rect(self.width - 240, TOP_H + 40, 220, 160))

    def _tile_preview_rect(self):
        """Panneau de preview de la tuile (au-dessus de l'aperçu du tracé)."""
        return pygame.Rect(self.width - 340, TOP_H + 40, 320, 190)

    def _tile_cell_summary(self, tile):
        """Résumé des cases par type : ex. « 4 descente, 2 plat » ou
        « 6 plat », plus les lignes départ/arrivée."""
        from collections import Counter
        from game.track import CellGeographyType, CellRunType
        # les cases avec une ligne (départ/arrivée) ne comptent pas dans le relief
        geos = Counter(c.geography for c in tile.cells if c.run == CellRunType.NONE)
        runs = Counter(c.run for c in tile.cells)
        parts = []
        for g, name in ((CellGeographyType.UPHILL, "montée"),
                        (CellGeographyType.DOWNHILL, "descente"),
                        (CellGeographyType.FLAT, "plat")):
            if geos.get(g):
                parts.append(f"{geos[g]} {name}")
        if runs.get(CellRunType.START):
            parts.append(f"{runs[CellRunType.START]} départ")
        if runs.get(CellRunType.END):
            parts.append(f"{runs[CellRunType.END]} arrivée")
        return "cases : " + (", ".join(parts) if parts else "aucune")

    def _draw_tile_preview(self, ch, rect):
        """Panneau en haut à droite de l'éditeur : DESCRIPTION texte de la tuile
        survolée (lettre, forme, nb de cases par type, largeur, face)."""
        from game.game import build_tile
        tile = build_tile(ch)
        pygame.draw.rect(self.screen, (45, 50, 58), rect, border_radius=8)
        pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=8)
        big = self.big_font.render(ch, True, WHITE)
        self.screen.blit(big, (rect.x + 12, rect.y + 10))
        if tile.turn is not None:
            deg = round(math.degrees(tile.turn[0]))
            sens = "droite" if tile.turn[1] < 0 else "gauche"
            shape = f"virage {deg}° {sens}"
        else:
            shape = "ligne droite"
        lines = [
            shape,
            self._tile_cell_summary(tile),
            f"{tile.length} cases · {tile.width} files",
            "face montagne" if ch.isupper() else "face plate",
        ]
        from game.track import CellGeographyType
        geos = {c.geography for c in tile.cells}
        if CellGeographyType.UPHILL in geos:
            lines.append("montée (rouge)")
        if CellGeographyType.DOWNHILL in geos:
            lines.append("descente (bleu)")
        y = rect.y + 52
        for line in lines:
            surf = self.label_font.render(line, True, (200, 205, 215))
            self.screen.blit(surf, (rect.x + 12, y))
            y += 24

    def _draw_editor_preview(self, rect):
        """Aperçu du tracé du code édité + profil, dans le panneau de droite."""
        from game.track import path_point_at, compute_track_path, CellGeographyType, CellRunType
        track = self._editor_track()
        pts = compute_track_path(track, 1.0)
        pygame.draw.rect(self.screen, (45, 50, 58), rect, border_radius=8)
        pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=8)
        title = self.label_font.render("Aperçu", True, WHITE)
        self.screen.blit(title, (rect.x + 12, rect.y + 10))
        trect = self._preview_track_rect(rect)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bb_w = max(xs) - min(xs) if xs else 1
        bb_h = max(ys) - min(ys) if ys else 1
        scale = min((trect.w - 16) / max(bb_w, 1e-9), (trect.h - 16) / max(bb_h, 1e-9))
        ox = trect.x + (trect.w - bb_w * scale) / 2 - min(xs) * scale
        oy = trect.y + (trect.h - bb_h * scale) / 2 - min(ys) * scale
        for tile in track.tiles:
            for cell in tile.cells:
                if cell.run == CellRunType.START:
                    c = (255, 236, 130)
                elif cell.run == CellRunType.END:
                    c = (240, 210, 60)
                elif cell.geography == CellGeographyType.UPHILL:
                    c = (220, 50, 50)
                elif cell.geography == CellGeographyType.DOWNHILL:
                    c = (50, 90, 220)
                else:
                    c = (200, 205, 215)
                seg = []
                for k in range(4):
                    px, py, _tx, _ty = path_point_at(pts, cell.x + k / 3)
                    seg.append((ox + px * scale, oy + py * scale))
                pygame.draw.lines(self.screen, c, False, seg, 5)
        # lettres des tuiles au milieu de chacune (aperçu global = lettres)
        s = 0.0
        for ch, tile in zip(self.editor_code, track.tiles):
            px, py, tx, ty = path_point_at(pts, s + tile.length / 2)
            nx, ny = -ty, tx
            lbl = self.small_font.render(ch, True, (170, 175, 185))
            self.screen.blit(lbl, (ox + px * scale + nx * 10 - 3, oy + py * scale + ny * 10 - 5))
            s += tile.length
        # profil sous le tracé
        alt = [0]
        for tile in track.tiles:
            for cell in tile.cells:
                g = cell.geography
                alt.append(alt[-1] + (1 if g == CellGeographyType.UPHILL
                                       else -1 if g == CellGeographyType.DOWNHILL else 0))
        self._draw_profile_array(alt, self._preview_profile_rect(rect))

    def _tile_shape_color(self, tile):
        """Couleur de la forme d'une tuile : jaune clair (départ), jaune vif
        (arrivée), rouge si montée, bleu si descente, gris sinon."""
        from game.track import CellGeographyType, CellRunType
        runs = {c.run for c in tile.cells}
        if CellRunType.START in runs:
            return (255, 236, 130)
        if CellRunType.END in runs:
            return (240, 210, 60)
        geos = {c.geography for c in tile.cells}
        if CellGeographyType.UPHILL in geos:
            return (220, 50, 50)
        if CellGeographyType.DOWNHILL in geos:
            return (50, 90, 220)
        return (200, 205, 215)

    def _draw_tile_shape(self, pts, tile, tr, width):
        """Dessine la FORME de la tuile (ligne suivant le tracé), colorée CASE
        PAR CASE (montée rouge, descente bleue, départ/arrivée jaunes, plat
        gris) — les tuiles mixtes sont donc fidèles — avec de fins séparateurs
        blancs entre les cases."""
        from game.track import path_point_at, CellGeographyType, CellRunType
        dense = _dense_points(pts, tile.length)
        per_cell = len(dense) // tile.length
        for ci, cell in enumerate(tile.cells):
            if cell.run == CellRunType.START:
                c = (255, 236, 130)
            elif cell.run == CellRunType.END:
                c = (240, 210, 60)
            elif cell.geography == CellGeographyType.UPHILL:
                c = (220, 50, 50)
            elif cell.geography == CellGeographyType.DOWNHILL:
                c = (50, 90, 220)
            else:
                c = (200, 205, 215)
            seg = [tr(p) for p in dense[ci * per_cell:(ci + 1) * per_cell + 1]]
            pygame.draw.lines(self.screen, c, False, seg, max(3, int(width)))
        for k in range(1, tile.length):
            p = tr(path_point_at(pts, k)[:2])
            pygame.draw.circle(self.screen, WHITE, (int(p[0]), int(p[1])), 1)

    def _draw_mini_tile(self, ch, sx, sy, tx, ty, size=36):
        """Dessine la tuile `ch` en miniature, centrée en (sx, sy) et orientée
        selon la tangente (tx, ty) du tracé. Chaque case est un segment coloré
        (géographie/ligne) séparé par un trait blanc, et le NOMBRE DE CASES
        est affiché sous la tuile (ex. « ×6 »)."""
        from game.game import build_tile
        from game.track import (Track, compute_track_path, path_point_at,
                                CellGeographyType, CellRunType)
        tile = build_tile(ch)
        t = Track()
        t.add_tile(build_tile(ch))
        pts = compute_track_path(t, 1.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx0 = (min(xs) + max(xs)) / 2
        cy0 = (min(ys) + max(ys)) / 2
        bb = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
        scale = size / bb
        ang = math.atan2(ty, tx)
        cos, sin = math.cos(ang), math.sin(ang)

        def tr(p):
            x, y = (p[0] - cx0) * scale, (p[1] - cy0) * scale
            return (sx + x * cos - y * sin, sy + x * sin + y * cos)

        # forme simple de la tuile (pas de barres), couleur = relief
        self._draw_tile_shape(pts, tile, tr, size * 0.22)

    def _draw_profile_array(self, alt, rect):
        """Variante de _draw_profile prenant directement le tableau d'altitudes."""
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

    def _draw_menu(self):
        """Menu de sélection (affiché quand self.game is None)."""
        mouse = pygame.mouse.get_pos()
        if self.menu_step == "players":
            self._draw_players_menu(mouse)
            return
        if self.menu_step == "editor":
            self._draw_editor(mouse)
            return
        title = self.title_font.render("Choisis ton étape", True, WHITE)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, HEADER_H + 14))
        hint = self.label_font.render("Clic ou flèches + ENTRÉE", True, (150, 155, 165))
        self.screen.blit(hint, ((self.width - hint.get_width()) // 2, HEADER_H + 52))

        entries = self._menu_entries()
        for i, (name, desc, code, rect, kind) in enumerate(entries):
            if kind == "header":
                hdr = self.label_font.render(name, True, (150, 155, 165))
                self.screen.blit(hdr, (rect.x + 4, rect.y + 4))
                continue
            selected = (i == self.menu_index)
            hovered = rect.collidepoint(mouse)
            fill = (70, 80, 95) if (selected or hovered) else (45, 50, 58)
            border = (235, 60, 60) if (selected or hovered) else (90, 95, 105)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, width=2 if (selected or hovered) else 1,
                             border_radius=8)
            if kind == "editor":
                # bouton avec roue crantée pour créer un circuit
                self._draw_gear((rect.x + 34, rect.centery), 15,
                                (240, 210, 60) if (selected or hovered) else (200, 205, 215))
                name_surf = self.phase_font.render(name, True, WHITE)
                self.screen.blit(name_surf, (rect.x + 60, rect.centery - 11))
            else:
                name_surf = self.phase_font.render(name, True, WHITE)
                self.screen.blit(name_surf, (rect.x + 16, rect.y + 6))
                desc_surf = self.label_font.render(desc, True, (180, 185, 195))
                self.screen.blit(desc_surf, (rect.x + 16, rect.y + rect.h - 20))
            if code and kind == "base":
                code_surf = self.small_font.render(code, True, (120, 125, 135))
                self.screen.blit(code_surf, (rect.right - 12 - code_surf.get_width(), rect.y + 8))

        # Prévisualisation du tracé de l'entrée sélectionnée (grandes fenêtres)
        if self.width >= 1100 and entries:
            name, _d, code, _r, kind = entries[self.menu_index]
            if kind in ("base", "perso"):
                self._draw_menu_preview(name, self._preview_rect(), code=code if kind == "perso" else None)

    def _draw_gear(self, center, r, color):
        """Dessine une roue crantée (engrenage) en `center`."""
        cx, cy = center
        for k in range(8):
            a = k * math.pi / 4
            x0 = cx + (r - 4) * math.cos(a)
            y0 = cy + (r - 4) * math.sin(a)
            pygame.draw.line(self.screen, color, (x0, y0),
                             (cx + (r + 4) * math.cos(a), cy + (r + 4) * math.sin(a)), 4)
        pygame.draw.circle(self.screen, color, (cx, cy), r, 3)
        pygame.draw.circle(self.screen, (45, 50, 58), (cx, cy), max(2, r // 3))

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
        """Démarre une partie sur l'étape choisie (depuis le menu ou R).
        Si un code perso est en attente (circuit perso JSON), il est utilisé."""
        self.stage = name
        code = self._pending_code
        self._pending_code = None
        self.game = Game(stage=name, player_count=self.player_count, auto_place=False,
                         custom_code=code)
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
        self.current_player_idx = 0
        self.log_scroll = 0
        self._pressed_button = None
        self._cam_drag = None
        self._cam_drag_moved = False
        self.show_podium = True  # écran de victoire : podium (TAB = circuit final)
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def _menu_event(self, event):
        """Événements du menu (étape 1 : choix de l'étape, étape 2 : nb joueurs)."""
        if self.menu_step == "players":
            self._players_menu_event(event)
            return
        if self.menu_step == "editor":
            self._editor_event(event)
            return
        entries = self._menu_entries()
        mouse = pygame.mouse.get_pos()
        hovered = None
        for i, (_name, _desc, _code, rect, kind) in enumerate(entries):
            if kind != "header" and rect.collidepoint(mouse):
                hovered = i
        if hovered is not None:
            self.menu_index = hovered
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hovered is not None:
            self._menu_validate(entries[hovered])
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(entries)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(entries)
            elif event.key == pygame.K_RETURN:
                self._menu_validate(entries[self.menu_index])

    def _menu_validate(self, entry):
        """Validation d'une entrée du menu : éditeur, étape de base ou perso."""
        name, _desc, code, _rect, kind = entry
        if kind == "header":
            return
        if kind == "editor":
            self.menu_step = "editor"
        else:
            self._pending_stage = name
            self._pending_code = code if kind == "perso" else None
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

    def _placement_click(self, pos):
        """Phase de placement : clic sur une case derrière la ligne DÉPART."""
        game = self.game
        if game.current_phase != Phase.PLACEMENT:
            return
        limit = game.track.start_line_x()
        geo = self._track_geometry()
        cell = geo["cell"]
        half = geo["half"]
        best = None
        best_d = cell * 0.75
        for x in range(limit):
            px, py, tx, ty = self._cell_anchor(x)
            nx, ny = -ty, tx
            for lane, off in ((0, half * 0.5), (1, -half * 0.5)):  # A = droite
                if not game.can_place_at(x, lane):
                    continue
                cx, cy = px + nx * off, py + ny * off
                d = math.hypot(pos[0] - cx, pos[1] - cy)
                if d < best_d:
                    best_d = d
                    best = (x, lane)
        if best and game.place_runner_at(*best):
            cur = game.current_placement()
            if cur:
                p, r = cur
                print(f"[OK] {p.color} placera ensuite son "
                      f"{'Sprinteur' if r.type.name == 'SPRINTER' else 'Rouleur'}")
            else:
                print("[OK] Placement terminé, début de la course !")

    def _handle_click(self, pos):
        """Gère un clic : onglet de joueur, ou jouer une carte du joueur en cours."""
        if not self.show_hands or self.game.current_phase != Phase.ENERGY:
            return
        # clic sur un onglet de joueur -> on affiche ce joueur
        for i, tab in enumerate(self._player_tab_rects()):
            if tab.collidepoint(pos):
                self.current_player_idx = i
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
                            # panneau suivant : joueur prochain qui n'a pas fini
                            if (self.game.cards_played_per_runner[player.sprinter.id] >= 1
                                    and self.game.cards_played_per_runner[player.roller.id] >= 1):
                                n = len(self.game.players)
                                for k in range(1, n + 1):
                                    j = (self.current_player_idx + k) % n
                                    p = self.game.players[j]
                                    if (self.game.cards_played_per_runner[p.sprinter.id] < 1
                                            or self.game.cards_played_per_runner[p.roller.id] < 1):
                                        self.current_player_idx = j
                                        break
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

        # Teinte des cases spéciales en POLYGONE borné par les bords de la
        # route (ne déborde pas dans les virages) : départ/arrivée jaunes,
        # montée rouge, descente bleue
        for x_cell in range(track.length):
            run = track.run_at(x_cell)
            cell_geo = track.geography_at(x_cell)
            if run == CellRunType.START:
                color = (255, 240, 190)   # jaune clair (comme la preview)
            elif run == CellRunType.END:
                color = (250, 230, 120)   # jaune vif (comme la preview)
            elif cell_geo == CellGeographyType.UPHILL:
                color = UPHILL_FILL
            elif cell_geo == CellGeographyType.DOWNHILL:
                color = DOWNHILL_FILL
            else:
                color = None
            if color is not None:
                s0, s1 = x_cell * cell, (x_cell + 1) * cell
                seg = [self._path_at(geo, s0 + (s1 - s0) * k / 8) for k in range(9)]
                right = [(x - ty * half, y + tx * half) for x, y, tx, ty in seg]
                left = [(x + ty * half, y - tx * half) for x, y, tx, ty in seg]
                pygame.draw.polygon(self.screen, color, right + left[::-1])

            # Marqueurs montée/descente : triangles à l'extérieur droit de la route
            if cell_geo in (CellGeographyType.UPHILL, CellGeographyType.DOWNHILL):
                px, py, tx, ty = self._path_at(geo, (x_cell + 0.5) * cell)
                nx, ny = -ty, tx
                mx = px + nx * (half + 12)
                my = py + ny * (half + 12)
                forward = 1 if cell_geo == CellGeographyType.UPHILL else -1
                tri = [(mx + tx * 7 * forward, my + ty * 7 * forward),
                       (mx + nx * 5, my + ny * 5),
                       (mx - nx * 5, my - ny * 5)]
                arrow_color = UPHILL_ARROW if cell_geo == CellGeographyType.UPHILL else DOWNHILL_ARROW
                pygame.draw.polygon(self.screen, arrow_color, tri)

        # Ligne médiane entre les deux files (sur tout le tracé) + quadrillage des cases
        pygame.draw.lines(self.screen, WHITE, False,
                          [(x, y) for x, y, _tx, _ty in samples], 2)
        for k in range(track.length + 1):
            px, py, tx, ty = self._path_at(geo, k * cell)
            nx, ny = -ty, tx
            pygame.draw.line(self.screen, WHITE,
                             (px + nx * half, py + ny * half),
                             (px - nx * half, py - ny * half), 1)

        # Lignes de DÉPART (bande jaune) et d'ARRIVÉE (damier noir/blanc),
        # bien visibles en travers de toute la route
        line_specs = [(track.start_line_x() * cell, "start", "DÉPART"),
                      (track.end_line_x() * cell, "end", "ARRIVÉE")]
        for s, kind, label in line_specs:
            px, py, tx, ty = self._path_at(geo, s)
            nx, ny = -ty, tx
            if kind == "start":
                pygame.draw.line(self.screen, (255, 236, 130),
                                 (px + nx * half, py + ny * half),
                                 (px - nx * half, py - ny * half), 7)
                pygame.draw.line(self.screen, (60, 50, 10),
                                 (px + nx * half, py + ny * half),
                                 (px - nx * half, py - ny * half), 1)
            else:
                # damier dans le jaune vif de l'arrivée (comme la preview)
                n = 8
                for k in range(n):
                    t0 = -half + 2 * half * k / n
                    t1 = -half + 2 * half * (k + 1) / n
                    c = (240, 210, 60) if k % 2 == 0 else (60, 50, 10)
                    pygame.draw.line(self.screen, c,
                                     (px + nx * t0, py + ny * t0),
                                     (px + nx * t1, py + ny * t1), 7)
            # libellé à l'extérieur droit de la route
            lx, ly = px + nx * (half + 22), py + ny * (half + 22)
            lbl = self.label_font.render(label, True,
                                         (255, 236, 130) if kind == "start" else (240, 210, 60))
            self.screen.blit(lbl, (lx - lbl.get_width() // 2, ly - lbl.get_height() // 2))

        # Phase de placement : surligner les files libres derrière la ligne DÉPART
        if self.game.current_phase == Phase.PLACEMENT:
            cur = self.game.current_placement()
            if cur:
                player, _runner = cur
                color = PLAYER_COLORS.get(player.color, WHITE)
                limit = track.start_line_x()
                for x in range(limit):
                    px, py, tx, ty = self._cell_anchor(x)
                    nx, ny = -ty, tx
                    for lane, off in ((0, half * 0.5), (1, -half * 0.5)):
                        if self.game.can_place_at(x, lane):
                            cx, cy = px + nx * off, py + ny * off
                            pygame.draw.circle(self.screen, color,
                                               (int(cx), int(cy)),
                                               max(4, int(cell * 0.28)), 2)

        # Numéros de case tous les 5, à l'extérieur de la route
        for x_cell in range(0, track.length, 5):
            px, py, tx, ty = self._path_at(geo, (x_cell + 0.5) * cell)
            nx, ny = -ty, tx
            num = self.small_font.render(str(x_cell), True, GRAY)
            self.screen.blit(num, num.get_rect(
                center=(px - nx * (half + 11), py - ny * (half + 11))))

    def _draw_runners(self):
        """Dessine les coureurs placés sur la piste (source de vérité : la
        piste). Les coureurs non placés (phase PLACEMENT) ne sont PAS sur la
        piste : ils sont affichés en réserve par _draw_unplaced_runners."""
        geo = self._track_geometry()
        lane_off = geo["lane_w"] / 2
        radius = int(geo["lane_w"] * 0.55)

        players_by_runner = {r.id: p for p in self.game.players
                             for r in p.get_runners()}
        for x, lane, runner in self.game.track.get_all_runners():
            player = players_by_runner[runner.id]
            px, py, tx, ty = self._cell_anchor(x)
            nx, ny = -ty, tx
            sign = 1 if lane == 0 else -1  # file A = droite du sens de marche
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
        if phase == Phase.PLACEMENT:
            cur = self.game.current_placement()
            if cur:
                player, runner = cur
                what = "Sprinteur" if runner.type.name == "SPRINTER" else "Rouleur"
                return ("PLACEMENT AU DÉPART",
                        f"Joueur {player.color} place son {what} : cliquez une case libre "
                        f"derrière la ligne DÉPART (bouton = tout placer au hasard)",
                        (126, 87, 194))
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

        # Étape et tour, juste après le titre (uniquement en partie)
        if self.game is not None:
            stage_name = STAGE_NAMES.get(self.game.stage, self.game.stage)
            info = self.label_font.render(
                f"{stage_name} · Tour {self.game.turn_count}", True, (175, 180, 190))
            self.screen.blit(info, (58 + flamme.get_width() + rouge.get_width() + 18,
                                    (HEADER_H - info.get_height()) // 2))
            # contrôles en une ligne au milieu du bandeau (tronquée avant les boutons)
            controls = (f"H mains · D decks · J histo · R restart · "
                        f"+/- zoom x{self.zoom:.2f} · flèches/clic gauche pan")
            cx = 58 + flamme.get_width() + rouge.get_width() + 18 + info.get_width() + 24
            max_w = self._camera_button_rects()["peloton"].x - 16 - cx
            csurf = self.small_font.render(controls, True, (140, 146, 156))
            if csurf.get_width() > max_w > 0:
                # tronque le texte pour ne jamais toucher les boutons
                while controls and self.small_font.render(controls + "…", True, (0, 0, 0)).get_width() > max_w:
                    controls = controls[:-1]
                csurf = self.small_font.render(controls + "…", True, (140, 146, 156))
            self.screen.blit(csurf, (cx, (HEADER_H - csurf.get_height()) // 2))
            # bouton podium à droite en fin de partie (les boutons caméra sont
            # dans le cadre du parcours, en haut à droite)
            if self.game.game_over:
                plabel = "Voir le circuit" if self.show_podium else "Voir le podium"
                self._draw_ui_button(self._podium_button_rect(), plabel, (240, 210, 60),
                                     pygame.mouse.get_pos())

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

        # À droite du bandeau de phase : compteur + action faite / prochaine étape
        right_lines = []
        if self.showing_movement:
            right_lines.append(f"Mouvement {self.movement_step}/{self.movement_total}")
        elif self.showing_aspiration:
            right_lines.append(f"Aspiration {self.aspiration_step}/{self.aspiration_total}")
        elif self.game.current_phase == Phase.ENERGY:
            right_lines.append(f"Cartes {self.game.cards_played_this_turn}/"
                               f"{self.game.total_cards_to_play}")
        if self.last_action:
            right_lines.append(self.last_action[0])
        if self.showing_movement and self.movement_movements:
            runner, value = self.movement_movements[0]
            eff, reason = self.game.track.effective_steps(runner.x, value)
            txt = f"Suivant : {self._short_id(runner)} joue {value}"
            if eff != value:
                txt += f" → {eff}"
            if reason:
                txt += f" ({reason})"
            right_lines.append(txt)
        elif self.showing_aspiration and self.aspiration_movements:
            step = self.aspiration_movements[0]
            right_lines.append("Pack : " + ", ".join(
                f"{self._short_id(r)}:{fx}→{tx}" for r, fx, _fl, tx, _tl in step))
        for i, line in enumerate(right_lines[-2:]):
            surf = self.small_font.render(line, True, (250, 250, 250))
            self.screen.blit(surf, (rect.right - 10 - surf.get_width(),
                                    rect.y + 6 + i * 16))

    def _draw_ui(self):
        self._draw_header()
        self._draw_phase_band()

        info_x = self._left_w() + 16  # (les compteurs/infos sont dans le bandeau de phase)
        # Barre du bas : panneau de cartes du joueur en cours (en bas à gauche)
        # + petit écran "ce qui se passe" (historique) à sa droite — toujours visibles
        if self.show_hands:
            bar = self._bar_rect()
            pygame.draw.rect(self.screen, (238, 240, 244), bar, border_radius=10)
            pygame.draw.rect(self.screen, (160, 166, 176), bar, width=2, border_radius=10)
            self._draw_hands()
            self._draw_log_panel()

        # (la réserve des coureurs non placés est dessinée dans le clip du cadre,
        #  directement dans la boucle principale — jamais hors du cadre)

        # Affichage des cartes restantes
        if self.show_decks:
            self._draw_decks()

        # Boutons dessinés APRÈS le reste pour ne jamais être couverts :
        # - pile en haut à droite DANS le cadre du parcours (caméra + violets)
        # - bouton d'action à droite de la barre du bas
        self._draw_frame_buttons(pygame.mouse.get_pos())
        self._draw_purple_buttons(pygame.mouse.get_pos())
        button_info = self._button_info()
        if button_info is not None:
            label, button_color = button_info
            self._draw_ui_button(self._button_rect(), label, button_color,
                                 pygame.mouse.get_pos(),
                                 pressed=(self._pressed_button == "action"))

    def _draw_frame_buttons(self, mouse):
        """Boutons caméra à côté de la légende (bas droite du cadre) :
        Tête de course (loupe), Peloton (groupe), Vue d'ensemble (dezoom)."""
        labels = {"tete": ("Tête de course", (70, 80, 95), not self.game.game_over, "loupe"),
                  "peloton": ("Peloton", (70, 80, 95), not self.game.game_over, "groupe"),
                  "ensemble": ("Vue d'ensemble", (70, 80, 95), True, "rect")}
        for key, rect in self._frame_button_rects().items():
            label, color, enabled, icon = labels[key]
            self._draw_ui_button(rect, label, color, mouse, enabled, icon,
                                 pressed=(self._pressed_button == key))

    def _draw_purple_buttons(self, mouse):
        """Bouton violet en bas à droite de la barre, à côté des logs :
        Tour aléatoire."""
        rect = self._purple_button_rects()["random"]
        self._draw_ui_button(rect, "Tour aléatoire", (126, 87, 194), mouse,
                             enabled=not self.game.game_over,
                             pressed=(self._pressed_button == "random"))

        # Panneau latéral : historique des coups joués (touche J)
        if self.show_history:
            self._draw_history()

        # Légende des couleurs du circuit (bas du cadre) sur fond blanc,
        # pour ne rien superposer ; les boutons caméra sont à sa droite
        legend_y = self._bar_rect().y - 24  # légende en bas du cadre du parcours
        legend_x = self._left_w() + 20
        items = [((255, 236, 130), "Départ"), ((240, 210, 60), "Arrivée"),
                 (UPHILL_FILL, "Montée"), (DOWNHILL_FILL, "Descente")]
        # fond blanc derrière la légende
        total_w = 0
        for _sw, label in items:
            total_w += 18 + self.label_font.render(label, True, (0, 0, 0)).get_width() + 14
        frame = self._frame_rect()
        pygame.draw.rect(self.screen, WHITE,
                         (frame.x + 4, legend_y - 5, total_w + 14, 24), border_radius=6)
        pygame.draw.rect(self.screen, (160, 166, 176),
                         (frame.x + 4, legend_y - 5, total_w + 14, 24), width=1,
                         border_radius=6)
        for swatch, label in items:
            pygame.draw.rect(self.screen, swatch, (legend_x, legend_y, 14, 14), border_radius=3)
            pygame.draw.rect(self.screen, BLACK, (legend_x, legend_y, 14, 14),
                             width=1, border_radius=3)
            text_surf = self.label_font.render(label, True, BLACK)
            self.screen.blit(text_surf, (legend_x + 18, legend_y - 2))
            legend_x += 18 + text_surf.get_width() + 14

        # Écran de victoire : overlay podium (le bouton est dans le bandeau de titre)
        # (TAB ou le bouton basculent avec l'état final du circuit)
        if self.game.game_over and self.show_podium:
            self._draw_podium()

    def _draw_podium(self):
        """Écran de fin de course : podium des 3 premiers coureurs."""
        game = self.game
        overlay = pygame.Rect(self.width // 2 - 270, self.height // 2 - 230, 540, 420)
        pygame.draw.rect(self.screen, (24, 28, 34), overlay, border_radius=12)
        pygame.draw.rect(self.screen, (240, 210, 60), overlay, width=2, border_radius=12)
        title = self.title_font.render("VICTOIRE", True, (240, 210, 60))
        self.screen.blit(title, title.get_rect(center=(overlay.centerx, overlay.y + 34)))

        rank = game.ranking()[:3]
        heights = [130, 95, 70]     # 1er, 2e, 3e
        offsets = [0, -1, 1]        # 1er au CENTRE, 2e à gauche, 3e à droite
        base_y = overlay.bottom - 46
        for i, entry in enumerate(rank):
            x = overlay.centerx + offsets[i] * 130 - 55
            h = heights[i]
            pygame.draw.rect(self.screen, (60, 66, 78), (x, base_y - h, 110, h),
                             border_radius=6)
            num = self.big_font.render(str(i + 1), True, WHITE)
            self.screen.blit(num, num.get_rect(center=(x + 55, base_y - h + 26)))
            player, runner = entry
            color = PLAYER_COLORS.get(player.color, WHITE)
            kind = "S" if runner.type.name == "SPRINTER" else "R"
            pygame.draw.circle(self.screen, color, (x + 55, base_y - h - 24), 16)
            pygame.draw.circle(self.screen, BLACK, (x + 55, base_y - h - 24), 16, 1)
            lbl = self.label_font.render(f"{player.color} {kind}", True, WHITE)
            self.screen.blit(lbl, lbl.get_rect(center=(x + 55, base_y - h - 50)))

        if game.winner:
            w = self.font.render(f"Gagnant : joueur {game.winner.color} !", True,
                                 (240, 210, 60))
            self.screen.blit(w, w.get_rect(center=(overlay.centerx, overlay.bottom - 30)))
        hint = self.label_font.render("TAB : voir le circuit final   ·   R : recommencer   ·   Échap : menu",
                                      True, (150, 155, 165))
        self.screen.blit(hint, hint.get_rect(center=(overlay.centerx, overlay.bottom + 16)))

    def _history_lines(self):
        """Lignes d'historique (texte, couleur, gras), ORDRE CHRONOLOGIQUE.
        - une ligne vide avant chaque nouveau tour
        - nom du tour et des phases en GRAS
        - chaque phrase liée à une équipe est dans la couleur de l'équipe."""
        lines = []
        for entry in self.game.history:
            if lines:
                lines.append(("", None, False))  # ligne vide entre les tours
            lines.append((f"Tour {entry['turn']}", (240, 210, 60), True))
            if entry["cards"]:
                lines.append(("Énergie", (200, 205, 215), True))
                for color, kind, val in entry["cards"]:
                    team = PLAYER_COLORS.get(color, (200, 205, 215))
                    lines.append((f"  {kind} joue {val}", team, False))
            if entry["moves"]:
                lines.append(("Mouvement", (200, 205, 215), True))
                for rid, color, fx, tx, val, eff, reason in entry["moves"]:
                    team = PLAYER_COLORS.get(color, (180, 220, 180))
                    txt = f"  {fx}->{tx} (carte {val}"
                    if eff != val:
                        txt += f" -> {eff}"
                    if reason:
                        txt += f", {reason}"
                    txt += ")"
                    lines.append((txt, team, False))
            if entry["slips"]:
                lines.append(("Aspiration", (200, 205, 215), True))
                for slip in entry["slips"]:
                    desc = ", ".join(f"{rid}:{fx}->{tx}" for rid, fx, tx in slip)
                    lines.append((f"  {desc}", (255, 200, 120), False))
        return lines

    def _draw_log_panel(self):
        """Petit écran à droite du panneau de cartes : ce qui se passe
        (dernières lignes de l'historique), toujours visible."""
        rect = self._log_panel_rect()
        pygame.draw.rect(self.screen, (24, 28, 34), rect, border_radius=8)
        pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=8)
        lines = self._history_lines()
        line_h = 15
        max_lines = (rect.bottom - rect.y - 10) // line_h
        max_scroll = max(0, len(lines) - max_lines)
        self.log_scroll = max(0, min(max_scroll, self.log_scroll))
        # ancré en bas : les plus récentes en dernier (en bas), les nouvelles
        # poussent les autres vers le haut ; log_scroll = lignes cachées en haut
        start = max(0, len(lines) - max_lines - self.log_scroll)
        visible = lines[start:start + max_lines]
        y = rect.bottom - 6 - line_h * len(visible)
        for txt, color, bold in visible:
            if not txt:
                continue  # ligne vide entre les tours
            font = self.bold_font if bold else self.small_font
            surf = font.render(txt, True, color if color else (200, 205, 215))
            self.screen.blit(surf, (rect.x + 10, y))
            y += line_h
        # indicateur de scroll (sans le mot « molette »)
        if max_scroll > 0:
            hint = self.small_font.render(f"▲ {self.log_scroll}/{max_scroll}",
                                          True, (110, 115, 125))
            self.screen.blit(hint, (rect.right - 10 - hint.get_width(), rect.y + 6))

    def _draw_history(self):
        """Overlay historique complet (touche J) : toutes les lignes."""
        rect = pygame.Rect(self.width - 370, TOP_H + 8, 358,
                           self.height - TOP_H - 60)
        pygame.draw.rect(self.screen, (24, 28, 34), rect, border_radius=10)
        pygame.draw.rect(self.screen, (90, 95, 105), rect, width=1, border_radius=10)
        title = self.phase_font.render("Historique des coups", True, WHITE)
        self.screen.blit(title, (rect.x + 12, rect.y + 10))
        y = rect.y + 40
        line_h = 17
        max_lines = (rect.bottom - 10 - y) // line_h
        for txt, color, bold in self._history_lines()[-max_lines:]:
            if not txt:
                y += line_h // 2
                continue
            font = self.bold_font if bold else self.small_font
            surf = font.render(txt, True, color if color else (200, 205, 215))
            self.screen.blit(surf, (rect.x + 12, y))
            y += line_h

    def _draw_unplaced_runners(self):
        """Phase de placement : les coureurs pas encore placés sont dessinés
        en réserve à côté de la ligne de départ, espacés (pas superposés)."""
        if not self.game or self.game.current_phase != Phase.PLACEMENT:
            return
        placed = {r.id for _x, _l, r in self.game.track.get_all_runners()}
        unplaced = [r for p in self.game.players for r in (p.sprinter, p.roller)
                    if r.id not in placed]
        if not unplaced:
            return
        geo = self._track_geometry()
        half = geo["half"]
        px, py, tx, ty = self._path_at(geo, 0.0)  # début du circuit
        nx, ny = -ty, tx
        # point de départ de la rangée : côté extérieur de la route au départ
        bx = px - nx * (half + 30)
        by = py - ny * (half + 30)
        reserve = self.small_font.render("réserve", True, GRAY)
        self.screen.blit(reserve, (bx - 6, by - half - 22))
        for i, r in enumerate(unplaced):
            cx = bx + tx * (i * 26)
            cy = by + ty * (i * 26)
            color = PLAYER_COLORS.get(r.color, WHITE)
            pygame.draw.circle(self.screen, color, (int(cx), int(cy)), 9)
            pygame.draw.circle(self.screen, BLACK, (int(cx), int(cy)), 9, 1)
            lbl = self.small_font.render("S" if r.type.name == "SPRINTER" else "R",
                                         True, BLACK)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy - lbl.get_height() // 2))

    def _draw_hands(self):
        """Panneau de cartes DU JOUEUR EN COURS (en bas à gauche), avec les
        onglets des joueurs au-dessus pour changer de joueur.

        Panneau compact : en-tête (nom + progression x/2), 2 lignes
        (Sprinteur / Rouleur), surbrillance au survol, carte jouée en vert.
        Cartes cliquables qu'en phase d'énergie (cf. _handle_click).
        """
        mouse = pygame.mouse.get_pos()
        # onglets des joueurs
        for i, (player, tab) in enumerate(zip(self.game.players, self._player_tab_rects())):
            active = (i == self.current_player_idx)
            hovered = tab.collidepoint(mouse)
            color = PLAYER_COLORS.get(player.color, BLACK)
            fill = color if active else ((tuple(min(255, c + 40) for c in color))
                                         if hovered else (60, 66, 78))
            pygame.draw.rect(self.screen, fill, tab, border_radius=5)
            pygame.draw.rect(self.screen, BLACK if active else (90, 95, 105), tab,
                             width=1, border_radius=5)
            t = self.small_font.render(player.color[:4], True,
                                       BLACK if active else WHITE)
            self.screen.blit(t, t.get_rect(center=tab.center))
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
                if not rects:
                    continue  # main vide (ex. phase de placement)
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
