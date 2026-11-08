import pygame
import sys
import math
from bisect import bisect_right
from game.game import Game, Phase
from game.card import CardType
from game.track import CellGeographyType, CellRunType, WeatherType

# Initialiser Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 920
MIN_WIDTH = 900    # taille minimale de la fenêtre
MIN_HEIGHT = 600
CELLS_PER_ROW = None  # (obsolète : le tracé suit désormais la séquence des tuiles)
CELL_MIN = 10       # plancher absolu de taille de case (le tracé tient toujours à l'écran)
CELL_MAX = 60
HEADER_H = 60       # bandeau de titre (toute la largeur)
PHASE_H = 44        # bandeau de phase (toute la largeur)
TOP_H = HEADER_H + PHASE_H + 8  # début de la zone de jeu sous les bandeaux
MENU_TOP = HEADER_H + 48         # début du contenu des écrans de menu (juste sous le titre)
INFO_H = 100        # hauteur du bloc infos (compteur, action, prochain)

CARD_W = 44        # taille des cartes en main
CARD_H = 58
CARD_GAP = 6       # espace entre cartes
PANEL_PAD = 10     # padding des panneaux de joueur
PANEL_HEADER = 30  # hauteur de l'en-tête des panneaux (nom + progression)
PANEL_H = 170      # hauteur d'un panneau de joueur (colonne de gauche)
BUTTONS_H = 100    # hauteur réservée en bas de colonne pour les 2 boutons
BAR_H = 150        # hauteur de la barre du bas (cartes + log + boutons)
PROFILE_H = 150    # hauteur du bandeau profil de course, SOUS le parcours
CARD_H_MAIN = 36   # hauteur fixe des cartes à sélectionner (le bloc s'adapte, pas l'inverse)
GREEN_CARD_FILL = (185, 230, 176)    # carte jouée (sélectionnée)
GREEN_CARD_BORDER = (46, 125, 50)

LIGHT_TURN_FILL = (255, 250, 205)    # virage léger
SHARP_TURN_FILL = (255, 224, 178)   # virage serré
UPHILL_FILL = (255, 205, 205)       # montée (bords rouges dans le jeu officiel)
DOWNHILL_FILL = (205, 225, 255)     # descente (bords bleus)
COBBLE_FILL = (176, 176, 184)       # pavés (Peloton) : gris pavé
SUPPLY_FILL = (198, 232, 198)       # zone d'approvisionnement (Peloton) : vert clair

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 165, 0)      # assez foncé pour être lisible sur fond clair
YELLOW = (215, 175, 0)   # idem (jaune vif illisible sur blanc)
ORANGE = (255, 165, 0)

PLAYER_COLORS = {
    "red": RED,
    "blue": BLUE,
    "green": GREEN,
    "yellow": YELLOW,
    "pink": (232, 120, 170),
    "white": (250, 250, 252),
}

# ===================== DESIGN SYSTEM (thème clair « soft ») =====================
# Palette
BG_TOP = (233, 246, 233)        # fond en haut (dégradé vert clair)
BG_BOT = (215, 235, 215)        # fond en bas (dégradé vert)
BG = BG_TOP                      # fond de référence (menu)
HEADER_BG = (255, 255, 255)     # bandeau de titre
PANEL = (255, 255, 255)         # surfaces (cartes, panneaux)
PANEL_ALT = (245, 247, 250)     # sous-fonds (chips, onglets inactifs)
BORDER = (198, 204, 212)        # bordures 1 px
ROW_SEL = (226, 232, 240)       # survol
INK = (33, 37, 45)              # texte principal
TEXT_DIM = (95, 102, 114)       # texte secondaire
ACCENT = (200, 45, 45)          # rouge principal (boutons SUIVANT/JOUER, logo)
ACCENT_SOFT = (60, 170, 150)    # teal doux, complémentaire du rouge (Créer un circuit)
SHADOW_RGB = (30, 35, 45)       # couleur des ombres portées
ROAD_SHADOW = (205, 211, 221)   # ombre sous la route
# Échelle de rayons
R_SM = 8                        # petites cartes
CARD_R = 12                     # grandes cartes/panneaux
BTN_R = 10                      # boutons
CHIP_R = 999                    # pastilles (plein arrondi)
# Grille d'espacement (multiple de 4/8)
PAD = 8


def _mix(c1, c2, t):
    """Mélange linéaire entre deux couleurs RGB, t=0 -> c1, t=1 -> c2."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _dense_points(pts, length, per_cell=6):
    """Échantillonne une polyligne de tuile en points denses (pour un tracé lisse)."""
    from game.track import path_point_at
    return [path_point_at(pts, k / per_cell)[:2] for k in range(length * per_cell + 1)]

# Noms d'affichage des étapes
STAGE_NAMES = {
    "test": "Piste d'essai",
    "Avenue Corso Paseo": "Avenue Corso Paseo",
}

# Cyclistes connus pour nommer les groupes intermédiaires
CYCLISTES_CONNUS = ["Pogačar", "Vingegaard", "Evenepoel", "Van der Poel", "Roglič",
                    "Merckx", "Hinault", "Anquetil", "Poulidor", "Coppi",
                    "Bartali", "Van Aert", "Nibali", "Fignon"]


def col_category(climb_len: int):
    """Catégorie d'un col selon la LONGUEUR de la montée qui précède le
    sommet (en cases/km) : HC pour les très longues, 1 pour les longues,
    4 pour les petites."""
    if climb_len <= 0:
        return None  # plat : pas de col à catégoriser
    if climb_len >= 10:
        return "HC"
    if climb_len >= 7:
        return "1"
    if climb_len >= 5:
        return "2"
    if climb_len >= 3:
        return "3"
    return "4"


def climb_length_at(alt, i: int) -> int:
    """Longueur (en cases) de la montée continue qui précède le point i."""
    length = 0
    j = i
    while j > 0 and alt[j] > alt[j - 1]:
        length += 1
        j -= 1
    return length


def climb_length_before_summit(alt) -> int:
    """Longueur (en cases) de la montée continue qui précède le sommet."""
    imax = max(range(len(alt)), key=lambda i: alt[i])
    return climb_length_at(alt, imax)


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
        self.display_font = pygame.font.SysFont("Arial", 42, bold=True)  # hero menu
        self.phase_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.card_font = pygame.font.SysFont("Arial", 18)
        self.label_font = pygame.font.SysFont("Arial", 16)
        self.bold_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 12)

        self.stage = stage  # None -> menu de sélection d'étape affiché
        self.player_count = 2  # nombre de joueurs choisi au menu (2-4)
        self.game = Game(stage=stage, player_count=self.player_count) if stage else None
        self.menu_index = 1          # à l'arrivée, sélection sur le 1er parcours (index 0 = en-tête)
        self.menu_step = "stage"    # écran de sélection (nb de joueurs + extensions + étape)
        self._pending_stage = None
        self.menu_scroll = 0        # scroll de la liste du menu
        self.menu_search = ""       # filtre de recherche (parcours perso)
        self.ext_meteo = False      # extension Météo activée ?
        self.team_modes = {}       # slot équipe -> "human" | "peloton" | "muscle" (défaut human)
        self.ext_peloton = False    # extension Peloton activée ?
        self.menu_search_active = False
        self._menu_sb_drag = None   # offset du drag du thumb de la scrollbar
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
        self.log_sel = None  # sélection de texte dans le log : (ligne_début, ligne_fin) ou None
        self.log_sel_drag = False
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
        self.animations = []  # animations fluides en cours (déplacements des coureurs)
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
        bottom = self._frame_rect().bottom - 28  # légende en bas du cadre, profil sous le parcours
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
        from_x, from_y = runner.x, runner.y
        reason = self.game.apply_movement_step(move)  # gère chute pluie / relevé −2
        to_x, to_y = runner.x, runner.y
        eff = to_x - from_x
        self._push_animation(runner.id, from_x, from_y, to_x, to_y)

        # Bandeau : ce qui vient de se passer
        if reason and "chute" in reason and to_x == from_x:
            desc = f"{self._short_id(runner)} joue {value} : CHUTE sous la pluie !"
        elif to_x == from_x:
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
        """Cadre du parcours : entre les bandeaux du haut et le bandeau profil
        de course (sous le parcours), lui-même au-dessus de la barre du bas."""
        strip = self._profile_strip_rect()
        return pygame.Rect(4, TOP_H + 2, self.width - 10, strip.y - 6 - (TOP_H + 2))

    def _profile_strip_rect(self) -> pygame.Rect:
        """Bandeau du profil de course SOUS le parcours, plein largeur, entre le
        cadre du parcours et la barre du bas."""
        bar = self._bar_rect()
        return pygame.Rect(4, bar.y - PROFILE_H - 6, self.width - 10, PROFILE_H)

    def _podium_button_rect(self) -> pygame.Rect:
        """Bouton « Podium » dans le bandeau de titre (écran de fin, avec TAB)."""
        return pygame.Rect(self.width - 140, 12, 128, 36)

    def _draw_card(self, rect, fill=PANEL, radius=CARD_R, shadow=True, border=True):
        """Grande carte/panneau moderne : ombre portée douce + fond arrondi."""
        if shadow:
            s = pygame.Surface((rect.w + 8, rect.h + 10), pygame.SRCALPHA)
            pygame.draw.rect(s, (30, 35, 45, 26), (4, 6, rect.w, rect.h),
                             border_radius=radius)
            self.screen.blit(s, (rect.x - 4, rect.y - 2))
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=radius)

    def _draw_ui_button(self, rect, label, base_color, mouse, enabled=True, icon=None,
                        pressed=False, font=None):
        """Bouton moderne « pill » avec ombre portée et effet d'enfoncement au
        clic (ombre inversée). Libellé tronqué pour tenir dans le bouton.
        `icon` : 'loupe', 'groupe', 'rect' ou 'gear'. `font` : police du libellé."""
        fnt = font or self.small_font
        hovered = enabled and rect.collidepoint(mouse)
        fill = tuple(min(255, c + 30) for c in base_color) if hovered else base_color
        if not enabled:
            fill = PANEL_ALT
        if pressed and enabled:
            fill = tuple(max(0, c - 35) for c in fill)  # enfoncé au clic
        # ombre portée douce sous le bouton
        s = pygame.Surface((rect.w + 8, rect.h + 10), pygame.SRCALPHA)
        pygame.draw.rect(s, (30, 35, 45, 30), (4, 6, rect.w, rect.h),
                         border_radius=BTN_R)
        self.screen.blit(s, (rect.x - 4, rect.y - 2))
        # corps en dégradé vertical (haut éclairci -> base), look moderne
        self._grad_fill(rect, tuple(min(255, c + 22) for c in fill), fill, BTN_R)
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
        pygame.draw.rect(self.screen, dark, rect, width=1, border_radius=BTN_R)
        # contraste auto : texte FONCÉ sur bouton clair, BLANC sur bouton foncé
        if not enabled:
            text_color = TEXT_DIM
        else:
            lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
            text_color = INK if lum > 150 else WHITE
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
        elif icon == "gear":
            self._draw_gear((rect.x + 18, rect.centery), 12, text_color)
            tx = rect.x + 36
        # libellé tronqué pour tenir dans le bouton
        max_w = rect.right - 6 - tx
        while label and fnt.render(label, True, (0, 0, 0)).get_width() > max_w:
            label = label[:-1]
        surf = fnt.render(label, True, text_color)
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
        self.animations = []
        self.movement_step = self.movement_total = 0
        self.aspiration_step = self.aspiration_total = 0
        self.played_display_index = {r.id: 0 for p in game.players for r in p.get_runners()}
        self.last_action = (f"Tour {game.turn_count} joué en aléatoire", (126, 87, 194))

    # ------------------------------------------------------------------
    # Animations fluides des déplacements (glissade le long du circuit)
    # ------------------------------------------------------------------

    def _push_animation(self, rid, from_x, from_lane, to_x, to_lane):
        """Enregistre une animation de glissade d'un coureur d'une case à
        l'autre. Durée proportionnelle à la distance parcourue."""
        if (from_x, from_lane) == (to_x, to_lane):
            return  # bloqué : pas de déplacement, rien à animer
        dist = abs(to_x - from_x)
        dur = min(0.85, 0.22 + 0.055 * dist)  # secondes
        self.animations.append({"rid": rid, "from_x": from_x, "from_lane": from_lane,
                                "to_x": to_x, "to_lane": to_lane,
                                "t0": pygame.time.get_ticks(), "dur": int(dur * 1000)})

    def _animations_active(self) -> bool:
        now = pygame.time.get_ticks()
        return any(now < a["t0"] + a["dur"] for a in self.animations)

    def _prune_animations(self):
        now = pygame.time.get_ticks()
        self.animations = [a for a in self.animations if now < a["t0"] + a["dur"] + 50]

    def _advance_step(self):
        """Avance d'une étape (bouton ou ENTRÉE) selon l'état courant.
        Bloqué tant qu'une animation de déplacement est en cours."""
        if self._animations_active():
            return
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
        for r, fx, fl, tx, tl in step:  # positions AVANT application
            self._push_animation(r.id, fx, fl, tx, tl)
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
                # fond en dégradé vertical très doux
                self._grad_fill(pygame.Rect(0, 0, self.width, self.height),
                                BG_TOP, BG_BOT, 0)
                self._draw_header()
                self._draw_menu()
            else:
                self._grad_fill(pygame.Rect(0, 0, self.width, self.height),
                                (248, 253, 248), (222, 240, 222), 0)
                # cadre autour de la zone du parcours (tout le reste que la barre du bas)
                frame = self._frame_rect()
                self._draw_card(frame, (232, 243, 232), radius=CARD_R)
                # le tracé ne s'affiche QUE dans le cadre du parcours
                self.screen.set_clip(frame)
                # ombre interne en haut du cadre (effet "table" enfoncée)
                ins = pygame.Surface((frame.w, 12), pygame.SRCALPHA)
                for i in range(12):
                    pygame.draw.line(ins, (30, 35, 45, int(26 * (1 - i / 12))),
                                     (0, i), (frame.w, i))
                self.screen.blit(ins, (frame.x, frame.y))
                self._draw_track()
                self._draw_runners()
                self._draw_unplaced_runners()  # réserve aussi clippée dans le cadre
                self.screen.set_clip(None)
                self._draw_ui()
            self._prune_animations()
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
        elif event.type == pygame.MOUSEMOTION and self.log_sel_drag:
            # drag dans le log = étend la sélection de texte
            line = self._log_line_at(event.pos)
            if line is not None and self.log_sel:
                self.log_sel = (self.log_sel[0], line)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.log_sel_drag = False
            self._pressed_button = None  # relâche le bouton enfoncé
            # clic gauche sur le parcours sans déplacer = clic simple (placement)
            if self._cam_drag is not None:
                if not self._cam_drag_moved and self.game.current_phase == Phase.PLACEMENT:
                    self._placement_click(event.pos)
                self._cam_drag = None
                self._cam_drag_moved = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self._back_button_rect().collidepoint(event.pos):
                    self.game = None  # comme ÉCHAP : retour au menu
                    return
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
                if self._log_panel_rect().collidepoint(event.pos):
                    # clic dans le log = début de sélection de texte
                    line = self._log_line_at(event.pos)
                    if line is not None:
                        self.log_sel = (line, line)
                        self.log_sel_drag = True
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
            if event.key == pygame.K_c and (getattr(event, 'mod', 0) & pygame.KMOD_CTRL):
                self._log_copy_selection()  # copie la sélection du log
            elif event.key == pygame.K_a and (getattr(event, 'mod', 0) & pygame.KMOD_CTRL):
                lines = self._history_lines()
                if lines:
                    self.log_sel = (0, len(lines) - 1)  # tout sélectionner
            elif event.key == pygame.K_r:
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

    MENU_ROW = 36      # hauteur fixe d'une entrée du menu (compacte, sans détails)
    MENU_HEADER_H = 22 # hauteur d'un titre de catégorie
    EDITOR_ROW = 56    # hauteur du gros bouton « Créer un circuit » épinglé en bas

    def _menu_list_w(self) -> int:
        """Largeur de la zone de sélection (recherche + liste) : ~1/4 de la
        fenêtre en grand écran, centrée sinon."""
        if self.width < 1100:
            return min(680, self.width - 60)
        return max(260, self.width // 4 - 20)

    def _menu_preview_w(self) -> int:
        """Largeur du panneau de preview à droite du menu : tout le reste de
        la fenêtre (0 si fenêtre étroite, liste centrée alors)."""
        if self.width < 1100:
            return 0
        return self.width - self._menu_list_w() - 60

    def _menu_search_rect(self):
        """Barre de recherche (filtre les parcours perso par nom/code),
        dans le cadre de sélection, à droite de la scrollbar."""
        frame = self._menu_frame_rect()
        return pygame.Rect(frame.x + 20, MENU_TOP + 8, frame.w - 28, 28)

    def _options_frame_rect(self):
        """Panneau de gauche de l'écran d'options (joueurs + extensions),
        affiché APRÈS la sélection du parcours."""
        return pygame.Rect(12, MENU_TOP, min(620, self.width - 24),
                           self.height - 12 - MENU_TOP - 90)

    def _players_block_rect(self):
        """Bloc du choix du nombre de joueurs (2-6), en haut du panneau options."""
        fr = self._options_frame_rect()
        return pygame.Rect(fr.x + 10, fr.y + 64, fr.w - 20, 64)

    def _player_count_option_rects(self):
        """Petits boutons 2..6 dans le bloc joueurs."""
        br = self._players_block_rect()
        bw = (br.w - 20 - 5 * 4) // 6
        return {n: pygame.Rect(br.x + 10 + (n - 2) * (bw + 4), br.y + 30, bw, br.h - 38)
                for n in range(2, 7)}

    def _draw_players_block(self, mouse):
        """Bloc « JOUEURS » avec les options 2-6 ; 5/6 -> Peloton impératif."""
        br = self._players_block_rect()
        self._draw_card(br, PANEL_ALT, radius=10, shadow=False)
        h = self.small_font.render("JOUEURS", True, TEXT_DIM)
        self.screen.blit(h, (br.x + 10, br.y + 5))
        if self.player_count >= 5:
            note = self.small_font.render("Peloton requis", True, ACCENT)
            self.screen.blit(note, (br.right - 10 - note.get_width(), br.y + 6))
        for n, rect in self._player_count_option_rects().items():
            selected = (n == self.player_count)
            hovered = rect.collidepoint(mouse)
            if selected:
                pygame.draw.rect(self.screen, ACCENT, rect, border_radius=6)
            else:
                pygame.draw.rect(self.screen, PANEL if not hovered else ROW_SEL, rect,
                                 border_radius=6)
                pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=6)
            lbl = self.label_font.render(str(n), True, WHITE if selected else INK)
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _team_mode_row_rects(self):
        """Une ligne par équipe (1..player_count) sur l'écran d'options, entre le
        bloc joueurs et les extensions : choix Joueur / IA (Peloton/Muscle)."""
        pr = self._players_block_rect()
        y = pr.bottom + 8
        rows = []
        for i in range(self.player_count):
            rows.append((i, pygame.Rect(pr.x, y, pr.w, 34)))
            y += 40
        return rows

    def _team_mode_button_rect(self, row):
        return pygame.Rect(row.right - 128, row.y + 4, 118, 26)

    def _team_mode(self, i):
        return self.team_modes.get(i, "human")

    def _team_modes_list(self):
        """Liste des modes par équipe, passée au moteur."""
        return [self._team_mode(i) for i in range(self.player_count)]

    def _peloton_required(self):
        """Extension Peloton verrouillée (active et non désactivable) :
        5/6 joueurs OU au moins une équipe en IA Peloton / IA Muscle."""
        return (self.player_count >= 5
                or any(m in ("peloton", "muscle") for m in self._team_modes_list()))

    def _extensions_rect(self):
        """Panneau « Extensions » (blocs Météo / Peloton), sous les lignes d'équipes
        sur l'écran d'options (après sélection du parcours)."""
        fr = self._options_frame_rect()
        rows = self._team_mode_row_rects()
        y = rows[-1][1].bottom + 8 if rows else self._players_block_rect().bottom + 8
        return pygame.Rect(fr.x + 10, y, fr.w - 20, 64)

    def _draw_extensions(self, mouse):
        """Section Extensions : deux BLOCS côte à côte (Météo / Peloton), tout le
        bloc est cliquable ; actif = fond teinté accent + bordure + coche,
        inactif = bloc neutre (survol = léger highlight)."""
        er = self._extensions_rect()
        self._draw_card(er, PANEL_ALT, radius=10, shadow=False)
        h = self.small_font.render("EXTENSIONS", True, TEXT_DIM)
        self.screen.blit(h, (er.x + 10, er.y + 5))
        for key, label, icon_col in (("meteo", "Météo", (250, 190, 40)),
                                     ("peloton", "Peloton", (126, 87, 194))):
            tr = self._ext_tick_rects()[key]
            on = self.ext_meteo if key == "meteo" else self.ext_peloton
            hovered = tr.collidepoint(mouse)
            if on:  # actif : bloc mis en évidence
                pygame.draw.rect(self.screen, _mix(ACCENT, WHITE, 0.85), tr, border_radius=8)
                pygame.draw.rect(self.screen, ACCENT, tr, width=2, border_radius=8)
            else:  # inactif : bloc neutre
                pygame.draw.rect(self.screen, PANEL if not hovered else ROW_SEL, tr,
                                 border_radius=8)
                pygame.draw.rect(self.screen, BORDER, tr, width=1, border_radius=8)
            pygame.draw.circle(self.screen, icon_col, (tr.x + 15, tr.centery), 6)
            pygame.draw.circle(self.screen, WHITE, (tr.x + 15, tr.centery), 6, 1)
            lbl = self.label_font.render(label, True, INK if on else TEXT_DIM)
            self.screen.blit(lbl, (tr.x + 27, tr.centery - lbl.get_height() // 2))
            locked = key == "peloton" and self._peloton_required()
            if on and locked:  # cadenas : Peloton requis (5/6 joueurs ou IA Peloton/Muscle)
                lx, ly = tr.right - 15, tr.centery
                pygame.draw.arc(self.screen, ACCENT, (lx - 4, ly - 9, 8, 10), math.pi, 0, 2)
                pygame.draw.rect(self.screen, ACCENT, (lx - 6, ly - 1, 12, 9), border_radius=2)
            elif on:  # coche
                pygame.draw.line(self.screen, ACCENT, (tr.right - 15, tr.centery),
                                 (tr.right - 10, tr.bottom - 9), 2)
                pygame.draw.line(self.screen, ACCENT, (tr.right - 10, tr.bottom - 9),
                                 (tr.right - 4, tr.y + 8), 2)
    def _ext_tick_rects(self):
        """Blocs des extensions : {'meteo': Rect, 'peloton': Rect}, deux blocs
        côte à côte dans le panneau (toute la surface du bloc est cliquable)."""
        er = self._extensions_rect()
        bw = (er.w - 28) // 2  # deux blocs côte à côte sous l'en-tête
        by = er.y + 24
        bh = er.h - 30
        return {"meteo": pygame.Rect(er.x + 10, by, bw, bh),
                "peloton": pygame.Rect(er.x + 18 + bw, by, bw, bh)}
    def _menu_list_area(self):
        """Zone visible (scrollable) de la liste des parcours : sous la recherche."""
        top = self._menu_search_rect().bottom + 6
        return pygame.Rect(0, top, self.width, self.height - 40 - top)

    def _menu_frame_rect(self):
        """Cadre de la zone de sélection à gauche du menu (~1/4 de la fenêtre).
        La scrollbar tient dans la marge gauche du cadre (x+4), le contenu
        (recherche + liste) commence à x+20."""
        w = self._menu_list_w()
        x = 12 if self.width >= 1100 else (self.width - w) // 2 - 8
        return pygame.Rect(x, MENU_TOP, w + 28,
                           self.height - 12 - MENU_TOP)  # prend toute la place en bas

    def _next_button_rect(self):
        """Gros bouton rouge en bas à droite pour passer à l'écran suivant."""
        return pygame.Rect(self.width - 244, self.height - 68, 228, 54)

    def _menu_scrollbar_rects(self):
        """Barre de scroll verticale à GAUCHE mais DANS le cadre de sélection
        (marge gauche du cadre) : (track, thumb)."""
        area = self._menu_list_area()
        frame = self._menu_frame_rect()
        # clampée dans le cadre : ne dépasse ni en haut ni en bas
        top = max(area.y, frame.y + 4)
        bottom = min(area.bottom, frame.bottom - 4)
        track = pygame.Rect(frame.x + 4, top, 10, max(10, bottom - top))
        max_scroll = getattr(self, "_menu_max_scroll", 0)
        if max_scroll <= 0:
            return track, None
        content_h = getattr(self, "_menu_content_h", area.h)
        thumb_h = max(24, area.h * area.h // max(content_h, 1))
        thumb_y = area.y + (area.h - thumb_h) * self.menu_scroll // max_scroll
        return track, pygame.Rect(track.x, thumb_y, track.w, thumb_h)

    def _menu_entries(self):
        """Entrées du menu, par catégories, SCROLLABLES (menu_scroll) et filtrées
        par la recherche (menu_search, ne filtre que les parcours perso) :
        [("— Circuits du jeu de base —", header), 6 étapes officielles,
         ("— Circuits perso —", header) + entrées perso filtrées,
         ("Créer un circuit", éditeur)].
        Chaque entrée = (nom, description, code, rect, kind)."""
        from game.game import available_stages, list_saved_tracks
        frame = self._menu_frame_rect()
        w = frame.w - 28
        x = frame.x + 20
        base = available_stages()
        perso = list_saved_tracks(self.saves_dir)
        q = self.menu_search.strip().lower()
        if q:
            # la recherche s'applique à TOUS les choix (base + perso)
            base = [b for b in base if q in b[0].lower() or q in b[2].lower()]
            perso = [s for s in perso
                     if q in s["name"].lower() or q in s["code"].lower()]
        row, header_h = self.MENU_ROW, self.MENU_HEADER_H
        area = self._menu_list_area()
        # zone scrollable = liste moins le gros bouton « Créer un circuit » en bas
        scroll_area = pygame.Rect(area.x, area.y, area.w, area.h - self.EDITOR_ROW)
        self._menu_scroll_area = scroll_area
        content_h = (2 + len(base) + (1 if perso else 0) + len(perso)) * (row + 6) \
            + 2 * (header_h + 6)
        max_scroll = max(0, content_h - scroll_area.h)
        self._menu_content_h = content_h
        self._menu_max_scroll = max_scroll
        self.menu_scroll = max(0, min(max_scroll, self.menu_scroll))
        y = scroll_area.y - self.menu_scroll
        entries = []

        def add(name, desc, code, kind, h):
            nonlocal y
            rect = pygame.Rect(x, y, w, h)
            entries.append((name, desc, code, rect, kind))
            y += h + 6

        if base:
            add("— Circuits du jeu de base —", "", "", "header", header_h)
            for name, desc, code in base:
                add(name, desc, code, "base", row)
        if perso:
            add("— Circuits perso —", "", "", "header", header_h)
            for s in perso:
                add(s["name"], f"{len(s['code'])} tuiles · code {s['code']}",
                    s["code"], "perso", row)
        # « Créer un circuit » : TOUJOURS visible, épinglé en bas de la zone liste
        # (hors scroll, hors filtre de recherche) — gros bouton
        entries.append(("Créer un circuit", "éditeur de piste", "",
                        pygame.Rect(x, scroll_area.bottom, w, self.EDITOR_ROW), "editor"))
        return entries

    def _preview_rect(self):
        """Panneau de prévisualisation (colonne de droite du menu) :
        tracé de l'étape + profil d'altitude. Sa taille suit la fenêtre,
        en laissant la place au gros bouton rouge en bas à droite."""
        pw = self._menu_preview_w() or 330
        return pygame.Rect(self.width - pw - 16, MENU_TOP, pw,
                           self.height - MENU_TOP - 12 - 76)  # toute la hauteur (moins le bouton rouge)

    def _preview_track_rect(self, rect):
        """Sous-zone du tracé dans le panneau de preview (le profil fait
        au plus 120 px en dessous)."""
        h = max(120, rect.h - 178)
        return pygame.Rect(rect.x + 10, rect.y + 34, rect.w - 20, h)

    def _preview_profile_rect(self, rect):
        """Sous-zone du profil d'altitude (avec échelle km + D+ + drapeau)."""
        tr = self._preview_track_rect(rect)
        return pygame.Rect(rect.x + 10, tr.bottom + 8, rect.w - 20, 84)

    def _menu_profile_rect(self, rect):
        """Profil du menu : hauteur réduite (plafonnée à 120 px) sous le tracé."""
        tr = self._preview_track_rect(rect)
        top = tr.bottom + 8
        return pygame.Rect(rect.x + 10, top, rect.w - 20,
                           min(120, max(84, rect.bottom - 8 - top)))

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

        self._draw_card(rect, PANEL, radius=10)
        title = self.phase_font.render(name, True, INK)
        self.screen.blit(title, (rect.x + 12, rect.y + 8))

        # Tracé coloré CASE PAR CASE, route large : mêmes couleurs que le
        # profil (montée orange, descente bleu), plat en gris très foncé,
        # départ jaune clair, arrivée jaune vif
        road_w = max(9, min(16, round(scale * 1.3)))  # largeur de la route
        from game.game import build_stage_track, build_track_from_code
        from game.track import CellGeographyType, CellRunType
        track = build_track_from_code(code) if code else build_stage_track(name)
        # Polyligne complète du tracé (4 sous-points par case) avec normales
        # BISSEctrices communes à toutes les cases : la jonction entre deux
        # cases est une arête en onglet partagée exactement par les deux
        # polygones -> bords parfaitement droits ET couleurs strictement
        # contenues dans leur case (aucun débordement).
        steps = 4
        all_pts = []     # points écran du tracé complet
        cell_spans = []  # (index début, index fin, couleur) par case
        for tile in track.tiles:
            for cell in tile.cells:
                s0 = float(cell.x)
                if cell.run in (CellRunType.START, CellRunType.END):
                    seg_color = (48, 52, 60)     # départ/arrivée en noir : identifiés par leurs lignes
                elif cell.geography == CellGeographyType.UPHILL:
                    seg_color = (235, 145, 50)   # montée : orange (comme le profil)
                elif cell.geography == CellGeographyType.DOWNHILL:
                    seg_color = (80, 120, 235)   # descente : bleu (comme le profil)
                elif cell.geography == CellGeographyType.COBBLE:
                    seg_color = (150, 150, 158)  # pavés : gris pavé
                elif cell.geography == CellGeographyType.SUPPLY:
                    seg_color = (110, 180, 110)  # zone d'approvisionnement : vert
                else:
                    seg_color = (48, 52, 60)     # plat : gris très foncé
                # la case reprend le DERNIER point posé (frontière partagée avec
                # la case précédente) : les polygones se touchent exactement,
                # aucun interstice entre les cases
                start = len(all_pts) - 1 if all_pts else 0
                for k in range(steps + 1):
                    if k == 0 and all_pts:
                        continue  # point frontière déjà posé par la case précédente
                    px, py, _tx, _ty = path_point_at(pts, s0 + k / steps)
                    all_pts.append((ox + px * scale, oy + py * scale))
                cell_spans.append((start, len(all_pts) - 1, seg_color))
        normals = []
        for i, pt in enumerate(all_pts):
            if i == 0:
                dx, dy = all_pts[1][0] - pt[0], all_pts[1][1] - pt[1]
            elif i == len(all_pts) - 1:
                dx, dy = pt[0] - all_pts[i - 1][0], pt[1] - all_pts[i - 1][1]
            else:
                dx, dy = all_pts[i + 1][0] - all_pts[i - 1][0], all_pts[i + 1][1] - all_pts[i - 1][1]
            norm = math.hypot(dx, dy) or 1.0
            normals.append((-dy / norm, dx / norm))
        # Fond de la route en entier (même géométrie) : bouche les éventuels
        # interstices de rasterisation entre polygones de cases adjacentes
        full_left = [(all_pts[i][0] + normals[i][0] * road_w / 2,
                      all_pts[i][1] + normals[i][1] * road_w / 2) for i in range(len(all_pts))]
        full_right = [(all_pts[i][0] - normals[i][0] * road_w / 2,
                       all_pts[i][1] - normals[i][1] * road_w / 2) for i in range(len(all_pts))]
        full_road = full_left + full_right[::-1]
        # ombre douce sous la route
        pygame.draw.polygon(self.screen, ROAD_SHADOW, [(x, y + 3) for x, y in full_road])
        pygame.draw.polygon(self.screen, (48, 52, 60), full_road)
        # Chaque case = bandeau polygonal (offset exact +/- road_w/2 le long
        # des normales partagées) : bords parfaitement droits.
        for start, end, seg_color in cell_spans:
            left = [(all_pts[i][0] + normals[i][0] * road_w / 2,
                     all_pts[i][1] + normals[i][1] * road_w / 2) for i in range(start, end + 1)]
            right = [(all_pts[i][0] - normals[i][0] * road_w / 2,
                      all_pts[i][1] - normals[i][1] * road_w / 2) for i in range(start, end + 1)]
            pygame.draw.polygon(self.screen, seg_color, left + right[::-1])
        # ligne continue et très fine au MILIEU de la route (séparation des 2 files)
        pygame.draw.lines(self.screen, (235, 238, 242), False, all_pts, 1)

        # Un trait par CASE (pas par tuile) : FINE ligne claire à chaque
        # jonction de case, exactement sur la largeur de la route (1 px)
        _marks, total = self._preview_tile_marks(name, code=code)
        half = road_w / 2 + 3          # pour les lignes de départ/arrivée
        tick_half = road_w / 2         # les séparateurs de cases restent fins
        for s in range(1, int(total)):
            px, py, tx, ty = path_point_at(pts, float(s))
            sx, sy = ox + px * scale, oy + py * scale
            nx, ny = -ty, tx
            pygame.draw.line(self.screen, (225, 229, 235),
                             (sx + nx * tick_half, sy + ny * tick_half),
                             (sx - nx * tick_half, sy - ny * tick_half), 1)

        # Départ noté à la LIGNE de départ, arrivée à la LIGNE d'arrivée :
        # lignes en travers de la route à ces positions + mots « départ » /
        # « arrivée » en plus gros à côté (départ côté +n, arrivée côté -n)
        s_start = float(track.start_line_x())
        s_end = float(track.end_line_x())
        for s_line, col, word, side in ((s_start, (255, 236, 130), "départ", 1),
                                        (s_end, None, "arrivée", -1)):
            px, py, tx, ty = path_point_at(pts, s_line)
            sx, sy = ox + px * scale, oy + py * scale
            nx, ny = -ty, tx
            if col is not None:  # ligne de départ : trait jaune clair
                pygame.draw.line(self.screen, col,
                                 (sx + nx * half, sy + ny * half),
                                 (sx - nx * half, sy - ny * half), 3)
            lbl = self.label_font.render(word, True, (40, 44, 52))
            lx = sx + nx * (half + 8) * side - lbl.get_width() // 2
            ly = sy + ny * (half + 8) * side - lbl.get_height() // 2
            self.screen.blit(lbl, (lx, ly))

        # Ligne d'arrivée sur le tracé : DAMIER noir/blanc en travers de la
        # route, exactement sur la largeur de la route (sans dépasser),
        # avec au moins deux rangées de carreaux le long de la piste
        ex, ey, etx, ety = path_point_at(pts, s_end)
        sx, sy = ox + ex * scale, oy + ey * scale
        nx, ny = -ety, etx
        step = 4                    # taille d'un carreau
        rh = road_w / 2             # le damier tient DANS la route
        rows = max(2, int(road_w // (2 * step)))  # rangées le long de la piste
        for r in range(rows):
            u0 = -step * rows / 2 + r * step   # bande le long de la tangente
            u1 = u0 + step
            a = -rh
            i = 0
            while a < rh:
                b = min(a + step, rh)
                c = BLACK if (i + r) % 2 == 0 else WHITE
                quad = [(sx + nx * a + etx * u0, sy + ny * a + ety * u0),
                        (sx + nx * b + etx * u0, sy + ny * b + ety * u0),
                        (sx + nx * b + etx * u1, sy + ny * b + ety * u1),
                        (sx + nx * a + etx * u1, sy + ny * a + ety * u1)]
                pygame.draw.polygon(self.screen, c, quad)
                a = b
                i += 1

        # Profil d'altitude de l'étape / du parcours perso (code si fourni),
        # en grand : il occupe tout l'espace restant sous le tracé
        alt = self._stage_profile(name, code=code)
        self._draw_profile_array(alt, self._menu_profile_rect(rect))

    def _stage_profile(self, name, code=None):
        """Altitude relative case par case : montée +1, descente -1, plat 0.
        `code` = code de tuiles perso (prioritaire sur le nom d'étape)."""
        key = ("code", code) if code else name
        if key not in self._profile_cache:
            from game.game import build_stage_track, build_track_from_code
            from game.track import CellGeographyType
            track = build_track_from_code(code) if code else build_stage_track(name)
            alt = [0]
            for tile in track.tiles:
                for cell in tile.cells:
                    g = cell.geography
                    alt.append(alt[-1] + (1 if g == CellGeographyType.UPHILL
                                           else -1 if g == CellGeographyType.DOWNHILL
                                           else 0))
            self._profile_cache[key] = alt
        return self._profile_cache[key]

    def _draw_profile(self, name, rect):
        """Dessine le profil d'altitude de l'étape dans son sous-panneau."""
        alt = self._stage_profile(name)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=6)
        lbl = self.small_font.render(f"Profil  (alt. {min(alt)} .. {max(alt)})",
                                     True, TEXT_DIM)
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
                         auto_place=False, custom_code=code, meteo=self.ext_meteo,
                         peloton=self.ext_peloton)
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
                  ("Ouvrir...", "dossier"), ("Retour", "retour")]
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
            if self._back_button_rect().collidepoint(event.pos):
                self.menu_step = "stage"  # comme ÉCHAP : retour au choix d'étape
                return
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
                    elif key == "dossier":
                        self._open_saves_folder()
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

    def _open_saves_folder(self):
        """Ouvre le dossier des parcours perso (saves/) dans l'explorateur de
        fichiers de l'OS."""
        import os
        path = os.path.abspath(self.saves_dir)
        os.makedirs(path, exist_ok=True)
        if hasattr(os, "startfile"):  # Windows
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])

    def _editor_track(self):
        from game.game import build_track_from_code
        return build_track_from_code(self.editor_code)

    def _draw_editor(self, mouse):
        """Écran de l'éditeur de piste : palette + code + aperçu + profil."""
        title = self.title_font.render("Éditeur de piste", True, BLACK)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, HEADER_H + 14))
        hint = self.label_font.render(
            "Clique une tuile (ou tape a-u, MAJ = face montagne) · RETOUR = jouer · Échap = retour",
            True, TEXT_DIM)
        self.screen.blit(hint, ((self.width - hint.get_width()) // 2, HEADER_H + 52))

        # code en cours + message (sauvegarde/chargement)
        code_surf = self.font.render(f"Code : {self.editor_code}", True, (240, 210, 60))
        self.screen.blit(code_surf, (20, TOP_H + 66))
        if self.editor_naming:
            # champ de saisie du nom de parcours
            box = pygame.Rect(20 + code_surf.get_width() + 20, TOP_H + 60, 320, 30)
            pygame.draw.rect(self.screen, PANEL_ALT, box, border_radius=6)
            pygame.draw.rect(self.screen, (240, 210, 60), box, width=2, border_radius=6)
            label = self.label_font.render("Nom du parcours : ", True, TEXT_DIM)
            self.screen.blit(label, (box.x, box.y - 20))
            name_surf = self.font.render(self.editor_name + ("|" if pygame.time.get_ticks() // 500 % 2 else ""), True, BLACK)
            self.screen.blit(name_surf, (box.x + 8, box.y + 6))
        elif self.editor_message:
            msg = self.label_font.render(self.editor_message, True, (120, 220, 140))
            self.screen.blit(msg, (20 + code_surf.get_width() + 20, TOP_H + 68))

        # noms des catégories au-dessus de chaque groupe
        for text, x, y in self._editor_palette_labels():
            surf = self.label_font.render(text, True, TEXT_DIM)
            self.screen.blit(surf, (x, y))

        # palette des 42 tuiles : des BOUTS DE PISTE cliquables (forme réelle),
        # avec la lettre en petit dans le coin pour identifier la tuile
        locked = bool(self.editor_code) and self.editor_code[-1].lower() == 'u'
        for ch, rect in self._editor_palette_rects():
            hovered = rect.collidepoint(mouse) and not (locked and ch.lower() != 'u')
            fill = PANEL_ALT  # même fond pour toutes les tuiles (majuscules comprises)
            if hovered:
                # lift au survol : ombre + fond éclairci + rayon plus doux
                sh = pygame.Surface((rect.w + 6, rect.h + 8), pygame.SRCALPHA)
                pygame.draw.rect(sh, (*SHADOW_RGB, 40), (3, 5, rect.w, rect.h),
                                 border_radius=R_SM)
                self.screen.blit(sh, (rect.x - 3, rect.y - 2))
                fill = tuple(min(255, c + 35) for c in fill)
            pygame.draw.rect(self.screen, fill, rect, border_radius=R_SM)
            pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=R_SM)
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
            color = (46, 125, 50) if key == "jouer" else ROW_SEL
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

        # Bouton « ← Retour » en haut à droite (bandeau titre), comme ÉCHAP
        self._draw_ui_button(self._back_button_rect(), "← Retour", (90, 96, 110),
                             mouse, pressed=(self._pressed_button == "back"))

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
        self._draw_card(rect, PANEL, radius=10)
        big = self.big_font.render(ch, True, BLACK)
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
        self._draw_card(rect, PANEL, radius=10)
        title = self.label_font.render("Aperçu", True, BLACK)
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
                elif cell.geography == CellGeographyType.COBBLE:
                    c = (140, 140, 148)
                elif cell.geography == CellGeographyType.SUPPLY:
                    c = (120, 190, 120)
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
            lbl = self.small_font.render(ch, True, TEXT_DIM)
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
            elif cell.geography == CellGeographyType.COBBLE:
                c = (140, 140, 148)
            elif cell.geography == CellGeographyType.SUPPLY:
                c = (120, 190, 120)
            else:
                c = (200, 205, 215)
            seg = [tr(p) for p in dense[ci * per_cell:(ci + 1) * per_cell + 1]]
            pygame.draw.lines(self.screen, c, False, seg, max(3, int(width)))
        for k in range(1, tile.length):
            p = tr(path_point_at(pts, k)[:2])
            pygame.draw.circle(self.screen, BORDER, (int(p[0]), int(p[1])), 1)

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

    def _draw_profile_array(self, alt, rect, markers=None, weather_tiles=None):
        """Profil d'altitude par segment : montée = orange doux, descente =
        bleu doux, plat = gris. 1 case = 1 km : échelle en dessous avec
        distance totale et D+ dans le titre, mots « départ » / « arrivée »
        aux extrémités et petit drapeau damier sur la ligne d'arrivée.
        `markers` = [(case_x, couleur, libellé)] -> marqueurs dessinés SUR la
        ligne de profil (groupes de la course en cours).
        `weather_tiles` = [(case début, longueur, WeatherType)] -> animation
        météo sur TOUTE LA LONGUEUR de chaque tuile météo sur le profil."""
        n = max(len(alt) - 1, 1)  # nombre de cases = kilomètres
        dplus = sum(max(0, alt[i + 1] - alt[i]) for i in range(n))
        self._draw_card(rect, PANEL, radius=8, shadow=False)
        # en haut à gauche, à côté de « Profil » : longueur en km et D+ en m
        # (1 case montante = 100 m de dénivelé)
        lbl = self.small_font.render(
            f"Profil — {n} km · D+ {dplus * 100} m  (alt. {min(alt)} .. {max(alt)})",
            True, TEXT_DIM)
        self.screen.blit(lbl, (rect.x + 6, rect.y + 3))
        if weather_tiles:
            # LÉGENDE météo dans le bloc profil : mini-icône + libellé par type présent
            wnames = {WeatherType.TAILWIND: "vent arrière", WeatherType.HEADWIND: "vent de face",
                      WeatherType.CROSSWIND: "vent de travers", WeatherType.RAIN: "pluie",
                      WeatherType.NONE: "soleil"}
            seen = []
            for _tx, _tl, w in weather_tiles:
                if w not in seen:
                    seen.append(w)
            lx = rect.x + 6 + lbl.get_width() + 18
            for w in seen:
                if lx > rect.right - 110:  # ne pas toucher le badge
                    break
                mini = pygame.Rect(lx, rect.y + 7, 18, 18)
                pygame.draw.circle(self.screen, PANEL_ALT, mini.center, 9)
                pygame.draw.circle(self.screen, BORDER, mini.center, 9, 1)
                self._draw_weather_icon(w, mini.centerx, mini.centery, 1.0, 0.0, 0.0, -1.0, 0)
                t = self.small_font.render(wnames.get(w, "?"), True, TEXT_DIM)
                self.screen.blit(t, (mini.right + 4, mini.centery - t.get_height() // 2))
                lx = mini.right + 4 + t.get_width() + 14
        lo, hi = min(alt), max(alt)
        span = max(hi - lo, 1)
        # marge haute de 40 px DANS le panneau pour les mâts des fanions de col
        inner = pygame.Rect(rect.x + 6, rect.y + 40, rect.w - 12, rect.h - 40 - 34)
        pts = [(inner.x + inner.w * i / n,
                inner.bottom - (a - lo) / span * inner.h) for i, a in enumerate(alt)]
        # profil très légèrement accidenté comme un vrai : petits aléas en
        # hauteur mais BEAUCOUP plus fréquents (chaque segment est subdivisé),
        # aléatoires (seedés -> pas de clignotement), uniquement ENTRE les cols
        # (sur les portions plates)
        import random as _random
        amp = max(0.6, inner.h * 0.02)
        sub = 2  # sous-segments par case -> aléas peu fréquents
        line_pts = [pts[0]]
        for i in range(n):
            for k in range(1, sub + 1):
                frac = k / sub
                bx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * frac
                by = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * frac
                if k < sub and alt[i + 1] == alt[i]:  # intérieur d'un plat
                    by += _random.Random(1000 + i * sub + k).uniform(-amp, amp)
                line_pts.append((bx, by))
        jpts = line_pts[::sub]  # points aux cases (pour le fanion)
        soft_fill = {1: (255, 205, 150), -1: (160, 195, 255), 0: (214, 219, 227)}
        seg_line = {1: (235, 145, 50), -1: (80, 120, 235), 0: TEXT_DIM}
        for i in range(n):
            d = alt[i + 1] - alt[i]
            key = 1 if d > 0 else -1 if d < 0 else 0
            top = line_pts[i * sub:(i + 1) * sub + 1]
            quad = top + [(top[-1][0], inner.bottom), (top[0][0], inner.bottom)]
            pygame.draw.polygon(self.screen, soft_fill[key], quad)
            pygame.draw.lines(self.screen, seg_line[key], False, top, 2)
        # marqueurs (groupes de la course) sur la ligne de profil : pastille
        # couleur d'équipe au point du coureur le plus avancé + libellé en
        # dessous, en quinconce pour éviter les chevauchements
        if markers:
            self.screen.set_clip(rect)
            for gi, (cell_x, color, label) in enumerate(markers):
                ci = max(0, min(int(cell_x), n))
                fx, fy = pts[ci]
                # marqueur = PETIT VÉLO couleur d'équipe (pas un point), posé sur la ligne
                pygame.draw.circle(self.screen, WHITE, (int(fx), int(fy)), 8)  # halo blanc
                self._draw_cyclist(int(fx), int(fy) - 1, 0.38, color)
                # NOM du groupe en gras, au-dessus ou en dessous de la ligne
                # (alterné pour éviter les chevauchements)
                lt = self.bold_font.render(label, True, INK)
                ly = int(fy) - 26 if gi % 2 == 0 else int(fy) + 9
                self.screen.blit(lt, (int(fx) - lt.get_width() // 2, ly))
            self.screen.set_clip(None)
        # animation météo sur TOUTE LA LONGUEUR de chaque tuile météo du profil
        if weather_tiles:
            self.screen.set_clip(rect)
            now = pygame.time.get_ticks()
            for tile_x, tile_len, w in weather_tiles:
                c0 = max(0, min(int(tile_x), n))
                c1 = max(c0 + 1, min(int(tile_x + tile_len), n))
                x0, y0 = pts[c0]
                x1 = pts[c1][0]
                fy = min(pts[c0][1], pts[c1][1])
                # pluie : zone au niveau de la ligne -> les traits tombent SUR la route
                zone_y = fy - 4 if w == WeatherType.RAIN else fy - 14
                self._draw_weather_zone(w, x0, x1, zone_y, now)
            self.screen.set_clip(None)
        # petit fanion rouge sur CHAQUE col : une cote = une montée qui se
        # TERMINE par du plat (ou par l'arrivée, qui peut donc être un col).
        # Catégorie selon la longueur de la montée qui précède ce col.
        for i in range(1, len(alt)):
            if alt[i] > alt[i - 1] and (i + 1 >= len(alt) or alt[i] >= alt[i + 1]):
                cat = col_category(climb_length_at(alt, i))
                if cat is None:
                    continue
                mx, my = jpts[i]
                # mât pour CHAQUE col, mais plus petit (18 px), et toujours
                # DANS le panneau profil (clampé sous la marge haute)
                top = max(rect.y + 18, my - 18)
                pygame.draw.line(self.screen, (90, 90, 90), (mx, my), (mx, top), 2)
                # drapeau rouge avec la catégorie écrite DESSUS (blanc sur rouge)
                fw, fh = 26, 13
                pygame.draw.rect(self.screen, (215, 45, 45),
                                 (mx + 1, top, fw, fh), border_radius=2)
                pygame.draw.rect(self.screen, (150, 25, 25),
                                 (mx + 1, top, fw, fh), width=1, border_radius=2)
                clbl = self.small_font.render(cat, True, WHITE)
                self.screen.blit(clbl, (mx + 1 + (fw - clbl.get_width()) // 2,
                                        top + (fh - clbl.get_height()) // 2))
        # ligne d'arrivée : mât en pointillés jaunes sur toute la hauteur du
        # profil + drapeau damier hissé tout en haut du panneau
        fx = pts[-1][0]
        for yy in range(inner.y, inner.bottom, 6):
            pygame.draw.line(self.screen, (240, 210, 60),
                             (fx, yy), (fx, min(yy + 3, inner.bottom)), 2)
        fy = rect.y + 2  # drapeau en haut du panneau
        pygame.draw.line(self.screen, (120, 120, 120), (fx, fy), (fx, inner.bottom), 2)
        fw, fh = 16, 10
        for i in range(4):
            for j in range(2):
                c = BLACK if (i + j) % 2 == 0 else WHITE
                pygame.draw.rect(self.screen, c,
                                 (fx - 2 - fw + i * (fw // 4), fy + j * (fh // 2),
                                  fw // 4, fh // 2))
        # échelle de distance sous le profil : 1 case = 1 km
        sy = inner.bottom + 6
        pygame.draw.line(self.screen, TEXT_DIM, (pts[0][0], sy), (fx, sy), 1)
        for km in range(0, n + 1, 10):
            tx = pts[0][0] + (fx - pts[0][0]) * km / n
            pygame.draw.line(self.screen, TEXT_DIM, (tx, sy - 4), (tx, sy), 1)
        # libellés sous l'échelle : « départ » à gauche, « arrivée » à droite,
        # kilomètres au milieu (tous les 20 km pour rester lisible)
        base_y = sy + 4
        dep = self.small_font.render("départ", True, (190, 150, 30))
        self.screen.blit(dep, (max(inner.x, pts[0][0]), base_y))
        arr = self.small_font.render("arrivée", True, (160, 130, 10))
        ax = min(fx - arr.get_width() - 4, inner.right - arr.get_width())
        self.screen.blit(arr, (max(inner.x, ax), base_y))
        for km in range(20, n, 20):
            tx = pts[0][0] + (fx - pts[0][0]) * km / n
            ksurf = self.small_font.render(str(km), True, TEXT_DIM)
            self.screen.blit(ksurf, (tx - ksurf.get_width() // 2, base_y))

    def _draw_menu(self):
        """Menu de sélection (affiché quand self.game is None)."""
        mouse = pygame.mouse.get_pos()
        if self.menu_step == "editor":
            self._draw_editor(mouse)
            return
        if self.menu_step == "options":
            self._draw_options_menu(mouse)
            return
        # Hero du menu : grand titre à gauche + sous-titre, alignés sur le cadre
        title = self.display_font.render("Choix de l'étape", True, INK)
        self.screen.blit(title, (20, HEADER_H + 2))
        sub = self.label_font.render("Flamme Rouge — jeu de course cycliste", True, TEXT_DIM)
        self.screen.blit(sub, (24 + title.get_width(), HEADER_H + 2 + title.get_height() - sub.get_height() - 4))

        # la sélection (recherche + liste) est dans un CADRE à gauche (~1/4 de
        # la fenêtre), le reste de la largeur est pour la preview à droite
        srect = self._menu_search_rect()
        frame = self._menu_frame_rect()
        self._draw_card(frame, PANEL, radius=CARD_R)

        # barre de recherche (filtre les parcours perso)
        pygame.draw.rect(self.screen, PANEL_ALT if self.menu_search_active else PANEL,
                         srect, border_radius=8)
        pygame.draw.rect(self.screen, (235, 60, 60) if self.menu_search_active else BORDER,
                         srect, width=2 if self.menu_search_active else 1, border_radius=8)
        stext = self.menu_search if self.menu_search else "Rechercher un parcours perso…"
        surf = self.label_font.render(stext, True, BLACK if self.menu_search else TEXT_DIM)
        self.screen.blit(surf, (srect.x + 10, srect.centery - surf.get_height() // 2))

        entries = self._menu_entries()
        area = getattr(self, "_menu_scroll_area", self._menu_list_area())
        self.screen.set_clip(area)  # la liste scrollable est clippée (l'entrée épinglée reste en dessous)
        for i, (name, desc, code, rect, kind) in enumerate(entries):
            if kind == "editor":
                continue  # dessinée à part, toujours visible en bas
            if kind == "header":
                hdr = self.label_font.render(name, True, TEXT_DIM)
                self.screen.blit(hdr, (rect.x + 4, rect.y + 4))
                continue
            selected = (i == self.menu_index)
            hovered = rect.collidepoint(mouse)
            if kind == "editor":
                # bouton avec roue crantée pour créer un circuit (avec entourage)
                fill = ROW_SEL if (selected or hovered) else PANEL
                border = (235, 60, 60) if (selected or hovered) else BORDER
                pygame.draw.rect(self.screen, fill, rect, border_radius=8)
                pygame.draw.rect(self.screen, border, rect, width=2 if (selected or hovered) else 1,
                                 border_radius=8)
                self._draw_gear((rect.x + 34, rect.centery), 15,
                                (240, 210, 60) if (selected or hovered) else (200, 205, 215))
                name_surf = self.phase_font.render(name, True, BLACK)
                self.screen.blit(name_surf, (rect.x + 60, rect.centery - 11))
            else:
                # entrée de parcours : fond BLANC, grisé au survol, jamais
                # entourée ; si sélectionnée, trait rouge à gauche ; pastille
                # de type d'étape (plat = gris, vallonné = orange, montagne = rouge)
                fill = ROW_SEL if hovered else PANEL
                pygame.draw.rect(self.screen, fill, rect, border_radius=8)
                if selected:
                    pygame.draw.rect(self.screen, ACCENT,
                                     (rect.x, rect.y + 2, 4, rect.h - 4))
                try:
                    alt = self._stage_profile(name, code=code if kind == "perso" else None)
                    dplus = sum(max(0, alt[i + 1] - alt[i]) for i in range(len(alt) - 1))
                except Exception:
                    dplus = -1  # code perso invalide : pastille neutre
                dot = (150, 156, 168) if dplus <= 0 else (ACCENT if dplus >= 15 else (240, 150, 50))
                pygame.draw.circle(self.screen, dot, (rect.x + 13, rect.centery), 5)
                name_surf = self.label_font.render(name, True, INK)
                self.screen.blit(name_surf, (rect.x + 26,
                                             rect.centery - name_surf.get_height() // 2))

        self.screen.set_clip(None)  # fin de la zone scrollable
        # entrée « Créer un circuit » épinglée en bas, toujours visible :
        # exactement le même bouton que SUIVANT (même rendu _draw_ui_button,
        # même typo phase_font, même profondeur/ombre, enfoncement au clic),
        # seule la couleur diffère : teal doux, complémentaire du rouge
        for name, desc, code, rect, kind in entries:
            if kind == "editor":
                self._draw_ui_button(rect, name, (60, 170, 150), pygame.mouse.get_pos(),
                                     icon="gear", font=self.phase_font,
                                     pressed=(self._pressed_button == "editor"))
        # barre de scroll verticale à gauche de la liste (si contenu > zone)
        track, thumb = self._menu_scrollbar_rects()
        if thumb is not None:
            pygame.draw.rect(self.screen, BORDER, track, border_radius=5)
            hovered = thumb.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, (150, 158, 170) if hovered else (110, 118, 130),
                             thumb, border_radius=5)
        # Prévisualisation du tracé de l'entrée SÉLECTIONNÉE (clic = sélectionner)
        if self.width >= 1100 and entries and 0 <= self.menu_index < len(entries):
            name, _d, code, _r, kind = entries[self.menu_index]
            if kind in ("base", "perso"):
                self._draw_menu_preview(name, self._preview_rect(), code=code if kind == "perso" else None)
        # Gros bouton en bas à droite : SUIVANT -> écran d'options (joueurs +
        # extensions), affiché APRÈS la sélection du parcours
        self._draw_ui_button(self._next_button_rect(), "SUIVANT →", ACCENT,
                             mouse, pressed=(self._pressed_button == "next"),
                             font=self.phase_font)

    # ------------------------------------------------------------------
    # Écran d'options (APRÈS la sélection du parcours) : joueurs + extensions
    # ------------------------------------------------------------------

    def _options_validate(self):
        """JOUER sur l'écran d'options : démarre la partie (équipes humain/IA choisies ici)."""
        self._select_stage(self._pending_stage)

    def _options_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_button_rect().collidepoint(event.pos):
                self.menu_step = "stage"  # retour à la sélection du parcours
                return
            if self._next_button_rect().collidepoint(event.pos):
                self._pressed_button = "next"
                self._options_validate()
                self._pressed_button = None
                return
            for n, rect in self._player_count_option_rects().items():
                if rect.collidepoint(event.pos):
                    self.player_count = n
                    if n >= 5:
                        self.ext_peloton = True  # 5/6 joueurs -> Peloton IMPÉRATIF
                    return
            for i, row in self._team_mode_row_rects():
                if self._team_mode_button_rect(row).collidepoint(event.pos):
                    cycle = ["human", "peloton", "muscle"]
                    self.team_modes[i] = cycle[(cycle.index(self._team_mode(i)) + 1) % 3]
                    if self.team_modes[i] in ("peloton", "muscle"):
                        self.ext_peloton = True  # IA Peloton/Muscle -> Peloton obligatoire
                    return
            for key, tr in self._ext_tick_rects().items():
                if tr.collidepoint(event.pos):
                    if key == "meteo":
                        self.ext_meteo = not self.ext_meteo
                    elif key == "peloton":
                        if self._peloton_required():
                            self.ext_peloton = True  # verrouillé : 5/6 joueurs ou IA Peloton/Muscle
                        else:
                            self.ext_peloton = not self.ext_peloton
                    return
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._options_validate()

    def _draw_options_menu(self, mouse):
        """Écran d'options (après sélection du parcours) : panneau de gauche avec
        le bloc JOUEURS (2-6) et les blocs Extensions (Météo/Peloton), preview du
        parcours choisi à droite, JOUER en bas à droite."""
        frame = self._options_frame_rect()
        self._draw_card(frame, PANEL, radius=CARD_R)
        title = self.display_font.render("Options", True, INK)
        self.screen.blit(title, (frame.x + 20, frame.y + 14))
        stage_name = STAGE_NAMES.get(self._pending_stage, self._pending_stage or "")
        sub = self.label_font.render(f"Parcours : {stage_name}", True, TEXT_DIM)
        self.screen.blit(sub, (frame.x + 22, frame.y + 14 + title.get_height() + 6))
        self._draw_players_block(mouse)
        # lignes des équipes : couleur + mode (Joueur / IA Peloton / IA Muscle)
        for i, row in self._team_mode_row_rects():
            hovered = row.collidepoint(mouse)
            pygame.draw.rect(self.screen, ROW_SEL if hovered else PANEL_ALT, row,
                             border_radius=8)
            pygame.draw.rect(self.screen, BORDER, row, width=1, border_radius=8)
            col = PLAYER_COLORS.get(["red", "blue", "green", "yellow", "pink", "white"][i], BLACK)
            pygame.draw.circle(self.screen, col, (row.x + 16, row.centery), 8)
            pygame.draw.circle(self.screen, BORDER, (row.x + 16, row.centery), 8, 1)
            mode = self._team_mode(i)
            lbl = self.label_font.render(f"Équipe {i + 1}", True, INK)
            self.screen.blit(lbl, (row.x + 32, row.centery - lbl.get_height() // 2))
            b = self._team_mode_button_rect(row)
            label = {"human": "Joueur", "peloton": "IA Peloton", "muscle": "IA Muscle"}[mode]
            self._draw_ui_button(b, label, ACCENT if mode != "human" else (90, 96, 110),
                                 mouse, font=self.small_font)
        self._draw_extensions(mouse)
        # preview du parcours choisi à droite (sans chevaucher le panneau options)
        if self.width >= 1100 and self._pending_stage:
            pr = pygame.Rect(frame.right + 16, MENU_TOP,
                             self.width - 16 - (frame.right + 16),
                             self.height - 12 - MENU_TOP)
            self._draw_menu_preview(self._pending_stage, pr, code=self._pending_code)
        # JOUER en bas à droite + retour en haut à droite
        self._draw_ui_button(self._next_button_rect(), "JOUER", ACCENT,
                             mouse, pressed=(self._pressed_button == "next"),
                             font=self.phase_font)
        self._draw_ui_button(self._back_button_rect(), "← Retour", (90, 96, 110),
                             mouse, pressed=(self._pressed_button == "back"))

    def _draw_gear(self, center, r, color):
        """Dessine un écrou en `center` : hexagone plein avec trou central."""
        cx, cy = center
        pts = [(cx + r * math.cos(math.pi / 6 + k * math.pi / 3),
                cy + r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
        pygame.draw.polygon(self.screen, color, pts)                       # corps
        pygame.draw.polygon(self.screen, tuple(max(0, c - 45) for c in color),
                            pts, 2)                                        # chanfrein
        pygame.draw.circle(self.screen, PANEL, (int(cx), int(cy)),
                           max(2, r // 2))                                 # trou
        pygame.draw.circle(self.screen, tuple(max(0, c - 45) for c in color),
                           (int(cx), int(cy)), max(2, r // 2), 1)         # bord du trou

    def _draw_cyclist(self, cx, cy, s, color):
        """Silhouette de cycliste (vélo + coureur) en `color`, échelle `s`."""
        w = max(2, int(2 * s))
        r = 10 * s
        # roues
        pygame.draw.circle(self.screen, color, (int(cx - 14 * s), int(cy)), int(r), w)
        pygame.draw.circle(self.screen, color, (int(cx + 14 * s), int(cy)), int(r), w)
        # cadre
        for (ax, ay), (bx, by) in (((-14, 0), (-2, -12)), ((-2, -12), (6, -12)),
                                    ((6, -12), (14, 0)), ((-14, 0), (-8, -13)),
                                    ((14, 0), (18, -14)), ((-8, -13), (-2, -12))):
            pygame.draw.line(self.screen, color, (cx + ax * s, cy + ay * s),
                             (cx + bx * s, cy + by * s), w)
        # coureur : dos, bras, jambes, tête
        hip = (cx - 6 * s, cy - 13 * s)
        shoulder = (cx + 10 * s, cy - 22 * s)
        head = (cx + 13 * s, cy - 26 * s)
        pygame.draw.line(self.screen, color, hip, shoulder, w + 1)                       # dos
        pygame.draw.line(self.screen, color, shoulder, (cx + 18 * s, cy - 14 * s), w)     # bras
        pygame.draw.line(self.screen, color, hip, (cx + 2 * s, cy - 4 * s), w)            # cuisse
        pygame.draw.line(self.screen, color, (cx + 2 * s, cy - 4 * s), (cx + 8 * s, cy), w)  # mollet
        pygame.draw.circle(self.screen, color, (int(head[0]), int(head[1])), int(4 * s))  # tête

    def _select_stage(self, name: str):
        """Démarre une partie sur l'étape choisie (depuis le menu ou R).
        Si un code perso est en attente (circuit perso JSON), il est utilisé."""
        self.stage = name
        code = self._pending_code
        self._pending_code = None
        self.game = Game(stage=name, player_count=self.player_count, auto_place=False,
                         custom_code=code, meteo=self.ext_meteo, peloton=self.ext_peloton,
                         team_modes=self._team_modes_list())
        self.showing_movement = False
        self.movement_step = 0
        self.movement_total = 0
        self.movement_movements = []
        self.showing_aspiration = False
        self.aspiration_step = 0
        self.aspiration_total = 0
        self.aspiration_movements = []
        self.animations = []
        self.played_display_index = {}
        self.last_action = None
        self.current_player_idx = 0
        self.log_scroll = 0
        self._pressed_button = None
        self._cam_drag = None
        self._cam_drag_moved = False
        self.log_sel = None
        self.log_sel_drag = False
        self.show_podium = True  # écran de victoire : podium (TAB = circuit final)
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def _menu_event(self, event):
        """Événements du menu (étape 1 : choix de l'étape, étape 2 : nb joueurs)."""
        if self.menu_step == "editor":
            self._editor_event(event)
            return
        if self.menu_step == "options":
            self._options_event(event)
            return
        entries = self._menu_entries()
        mouse = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEWHEEL:
            # molette sur la liste = scroll du menu
            area = self._menu_list_area()
            if area.collidepoint(mouse) or True:
                self.menu_scroll = max(0, self.menu_scroll - event.y * 40)
                self._menu_entries()  # re-clamp le scroll
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            track, thumb = self._menu_scrollbar_rects()
            if thumb is not None and (thumb.collidepoint(event.pos)
                                      or track.collidepoint(event.pos)):
                area = self._menu_list_area()
                if thumb.collidepoint(event.pos):
                    self._menu_sb_drag = event.pos[1] - thumb.y  # drag du thumb
                else:
                    # clic sur la piste = page haut/bas
                    self.menu_scroll += area.h if event.pos[1] > thumb.centery else -area.h
                    self._menu_entries()
                return
        if event.type == pygame.MOUSEMOTION and getattr(self, "_menu_sb_drag", None) is not None:
            track, thumb = self._menu_scrollbar_rects()
            if thumb is not None:
                area = self._menu_list_area()
                max_scroll = self._menu_max_scroll
                frac = (event.pos[1] - self._menu_sb_drag - area.y) / max(1, area.h - thumb.h)
                self.menu_scroll = int(frac * max_scroll)
                self._menu_entries()
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._menu_sb_drag = None
        if self.menu_search_active and event.type == pygame.KEYDOWN:
            # saisie dans la barre de recherche
            if event.key == pygame.K_ESCAPE:
                self.menu_search_active = False
                self.menu_search = ""
                self.menu_scroll = 0
            elif event.key == pygame.K_BACKSPACE:
                self.menu_search = self.menu_search[:-1]
                self.menu_scroll = 0
            elif event.key == pygame.K_RETURN:
                self.menu_search_active = False
            elif event.unicode and event.unicode.isprintable() and len(self.menu_search) < 40:
                self.menu_search += event.unicode
                self.menu_scroll = 0
            return
        hovered = None
        for i, (_name, _desc, _code, rect, kind) in enumerate(entries):
            if kind != "header" and rect.collidepoint(mouse):
                hovered = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._next_button_rect().collidepoint(event.pos):
                # gros bouton rouge = passer à l'écran suivant
                # (même animation d'enfoncement que les autres boutons)
                self._pressed_button = "next"
                self._menu_validate(entries[self.menu_index])
                self._pressed_button = None  # revient à l'état initial après le clic
                return
            if self._menu_search_rect().collidepoint(event.pos):
                self.menu_search_active = True  # focus barre de recherche
                return
            if hovered is not None:
                if entries[hovered][4] == "editor":
                    # « Créer un circuit » = comme le bouton SUIVANT : ouvre
                    # l'éditeur au clic direct, avec animation d'enfoncement
                    self._pressed_button = "editor"
                    self._menu_validate(entries[hovered])
                    self._pressed_button = None
                    return
                self.menu_index = hovered  # les autres entrées : clic = sélectionner
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(entries)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(entries)
            elif event.key == pygame.K_RETURN:
                self._menu_validate(entries[self.menu_index])
            elif event.key == pygame.K_PAGEUP:
                self.menu_scroll = max(0, self.menu_scroll - 200)
            elif event.key == pygame.K_PAGEDOWN:
                self.menu_scroll += 200
                self._menu_entries()

    def _menu_validate(self, entry):
        """Validation d'une entrée du menu : éditeur, étape de base ou perso."""
        name, _desc, code, _rect, kind = entry
        if kind == "header":
            return
        if kind == "editor":
            self.menu_step = "editor"
        else:
            # parcours sélectionné -> écran d'options (nb joueurs + extensions)
            self._pending_stage = name
            self._pending_code = code if kind == "perso" else None
            self.menu_step = "options"

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

    def _draw_weather_zone(self, w, x0, x1, y, now):
        """Animation météo sur TOUTE LA LONGUEUR de la tuile (entre x0 et x1,
        centrée en y sur le profil de course) : mêmes codes que _draw_weather_icon
        (vent = traits qui défilent, pluie = traits vers le bas + gouttes au sol,
        vent latéral = effet de profondeur, soleil = voile jaune)."""
        now = now // 3  # ralenti, comme les icônes
        span = max(8, x1 - x0)
        if w == WeatherType.RAIN:
            for x in range(int(x0), int(x1), 6):  # traits vers le bas sur toute la tuile
                dy = (now // 10 + x * 7) % 12
                pygame.draw.line(self.screen, (90, 130, 210), (x, y - 8 + dy), (x, y - 2 + dy), 2)
            for x in range(int(x0) + 3, int(x1), 12):  # petites gouttes par terre
                pygame.draw.circle(self.screen, (60, 100, 190), (x, int(y + 7)), 1)
        elif w in (WeatherType.TAILWIND, WeatherType.HEADWIND):
            c = (225, 185, 35) if w == WeatherType.TAILWIND else (60, 110, 220)
            sgn = 1 if w == WeatherType.TAILWIND else -1
            for k in range(3):  # traits sur toute la longueur, qui défilent
                ry = y - 8 + k * 5
                for j in range(2):
                    p = (now // 9 + j * (span // 2) + k * 7) % span
                    sx = x0 + p if sgn > 0 else x1 - p
                    pygame.draw.line(self.screen, c, (sx, ry), (sx + 8 * sgn, ry), 2)
        elif w == WeatherType.CROSSWIND:
            # vent de travers : des TRAITS qui apparaissent puis disparaissent
            # complètement (opacité sinusoïdale déphasée, 0 = trait disparu),
            # répartis sur toute la longueur de la tuile
            c = (60, 170, 80)
            for j in range(6):
                a = max(0.0, math.sin(now / 150.0 + j * 1.1))  # 0..1, apparition/disparition BEAUCOUP plus rapide  # 0..1
                a = a * a  # courbe nette : apparition/disparition franche
                if a <= 0.02:
                    continue  # trait complètement disparu
                x = x0 + (j + 0.5) * span / 6
                col = _mix(WHITE, c, a)
                pygame.draw.line(self.screen, col, (x, y - 7), (x, y + 7), 2)
        else:  # soleil (pas de météo spécifique) : SEULEMENT le petit soleil animé au milieu
            self._draw_weather_icon(WeatherType.NONE, (x0 + x1) / 2, y, 1.0, 0.0, 0.0, -1.0,
                                    now * 3)  # now*3 car l'icône re-ralentit en interne

    def _draw_weather_tile(self, w, tile, geo, cell, half, now):
        """Animation météo sur TOUTE LA LONGUEUR de la tuile sur le parcours :
        les traits ne sont PAS limités à une case — vent = longs traits qui
        défilent le long de la tuile, pluie = traits qui tombent sur toute la
        tuile + gouttes au sol, vent de travers = traits qui apparaissent et
        disparaissent sur toute la tuile. Soleil (NONE) : un seul petit soleil
        au milieu de la tuile."""
        now = now // 3  # ralenti
        t0, t1 = tile.x, tile.x + tile.length
        span = max(1, t1 - t0)
        if w == WeatherType.NONE:  # un seul soleil par tuile, au milieu
            mid = (t0 + t1) // 2
            px, py, tx, ty = self._path_at(geo, (mid + 0.5) * cell)
            nx, ny = -ty, tx
            self._draw_weather_icon(w, px - nx * (half + 14), py - ny * (half + 14),
                                    tx, ty, nx, ny, now * 3)
            return
        if w == WeatherType.RAIN:  # pluie sur toute la tuile
            for xc in range(t0, t1):
                px, py, tx, ty = self._path_at(geo, (xc + 0.5) * cell)
                nx, ny = -ty, tx
                mx, my = px - nx * (half + 12), py - ny * (half + 12)
                dy = (now // 10 + xc * 3) % 12
                pygame.draw.line(self.screen, (90, 130, 210), (mx, my - 8 + dy), (mx, my - 2 + dy), 2)
                pygame.draw.circle(self.screen, (60, 100, 190), (int(mx), int(my + 6)), 1)
        elif w in (WeatherType.TAILWIND, WeatherType.HEADWIND):
            # longs traits (~1 case) qui défilent LE LONG de toute la tuile
            c = (225, 185, 35) if w == WeatherType.TAILWIND else (60, 110, 220)
            sgn = 1 if w == WeatherType.TAILWIND else -1
            for j in range(2):
                o = (now // 9 + j * (span // 2)) % span
                for frac in (0.0, 0.5):
                    xc = t0 + o + frac
                    if xc >= t1:
                        continue
                    px, py, tx, ty = self._path_at(geo, (xc + 0.5) * cell)
                    nx, ny = -ty, tx
                    mx, my = px - nx * (half + 12), py - ny * (half + 12)
                    ln = 0.8 * cell
                    pygame.draw.line(self.screen, c, (mx, my),
                                     (mx + tx * sgn * ln, my + ty * sgn * ln), 2)
        else:  # CROSSWIND : traits qui apparaissent/disparaissent sur toute la tuile
            c = (60, 170, 80)
            for j in range(6):
                a = max(0.0, math.sin(now / 150.0 + j * 1.1))  # 0..1, apparition/disparition BEAUCOUP plus rapide
                a = a * a
                if a <= 0.02:
                    continue
                xc = t0 + (j + 0.5) * span / 6
                if xc >= t1:
                    continue
                px, py, tx, ty = self._path_at(geo, (xc + 0.5) * cell)
                nx, ny = -ty, tx
                mx, my = px - nx * (half + 12), py - ny * (half + 12)
                col = _mix((232, 243, 232), c, a)  # fondu vers le fond vert du cadre
                pygame.draw.line(self.screen, col,
                                 (mx - nx * 5, my - ny * 5), (mx + nx * 5, my + ny * 5), 2)

    def _draw_weather_icon(self, w, cx, cy, tx, ty, nx, ny, now):
        """Icône météo ANIMÉE (écran de course), centrée en (cx, cy), orientée
        selon la tangente (tx, ty) et la normale (nx, ny) de la route :
        - vent arrière / de face : TRAITS SUR LE CÔTÉ qui défilent dans le sens
          du vent (jaune ->, bleu <-) ;
        - vent de travers (latéral) : traits traversants avec EFFET DE
          PROFONdeur (proche = plus long et foncé, loin = plus court et clair) ;
        - pluie : TRAITS VERS LE BAS qui tombent + petites gouttes par terre ;
        - sinon (NONE) : SOLEIL (disque + rayons qui tournent)."""
        now = now // 3  # animations ralenties, mais un peu accélérées
        if w == WeatherType.RAIN:
            for k in range(3):  # traits vers le bas qui tombent en boucle
                dy = (now // 10 + k * 5) % 14
                x = cx - 5 + k * 5
                pygame.draw.line(self.screen, (90, 130, 210),
                                 (x, cy - 7 + dy), (x, cy - 1 + dy), 2)
            # petites gouttes par terre
            pygame.draw.circle(self.screen, (60, 100, 190), (int(cx - 3), int(cy + 6)), 2)
            pygame.draw.circle(self.screen, (60, 100, 190), (int(cx + 3), int(cy + 7)), 1)
            return
        if w == WeatherType.NONE:  # soleil : disque + rayons tournants
            pygame.draw.circle(self.screen, (250, 210, 60), (int(cx), int(cy)), 5)
            for k in range(8):
                a = now / 350.0 + k * math.pi / 4
                pygame.draw.line(self.screen, (250, 210, 60),
                                 (cx + math.cos(a) * 6, cy + math.sin(a) * 6),
                                 (cx + math.cos(a) * 9, cy + math.sin(a) * 9), 2)
            return
        if w in (WeatherType.TAILWIND, WeatherType.HEADWIND):
            c = (225, 185, 35) if w == WeatherType.TAILWIND else (60, 110, 220)
            sgn = 1 if w == WeatherType.TAILWIND else -1
            for k in range(3):  # traits sur le côté, défilant selon le vent
                o = (now // 9 + k * 6) % 14 - 7
                lat = (k - 1) * 5
                bx, by = cx + nx * lat, cy + ny * lat
                pygame.draw.line(self.screen, c,
                                 (bx + tx * sgn * o, by + ty * sgn * o),
                                 (bx + tx * sgn * (o + 5), by + ty * sgn * (o + 5)), 2)
        else:  # CROSSWIND : rafales qui traversent en FONDU (apparition/disparition)
            c = (60, 170, 80)
            for k in range(3):
                a = max(0.08, 0.5 + 0.5 * math.sin(now / 550.0 + k * 2.1))
                col = _mix(WHITE, c, a)
                o = (now // 9 + k * 6) % 16 - 8
                ax, ay = cx + nx * o, cy + ny * o
                pygame.draw.line(self.screen, col,
                                 (ax - nx * 4, ay - ny * 4), (ax + nx * 4, ay + ny * 4), 2)
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
        # ombre douce sous la route (décalée de 3 px)
        pygame.draw.polygon(self.screen, ROAD_SHADOW, [(x, y + 3) for x, y in road])
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
            elif cell_geo == CellGeographyType.COBBLE:
                color = COBBLE_FILL
            elif cell_geo == CellGeographyType.SUPPLY:
                color = SUPPLY_FILL
            else:
                color = None
            if color is not None:
                s0, s1 = x_cell * cell, (x_cell + 1) * cell
                seg = [self._path_at(geo, s0 + (s1 - s0) * k / 8) for k in range(9)]
                right = [(x - ty * half, y + tx * half) for x, y, tx, ty in seg]
                left = [(x + ty * half, y - tx * half) for x, y, tx, ty in seg]
                pygame.draw.polygon(self.screen, color, right + left[::-1])



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
                color = PLAYER_COLORS.get(player.color, BLACK)
                limit = track.start_line_x()
                for x in range(limit):
                    px, py, tx, ty = self._cell_anchor(x)
                    nx, ny = -ty, tx
                    cell0 = track.get_cell(x, 0)
                    n_lanes = len(cell0.runners) if cell0 else 2
                    for lane in range(n_lanes):
                        off = 0 if n_lanes == 1 else half * (1 - 2 * lane / (n_lanes - 1))
                        if self.game.can_place_at(x, lane):
                            cx, cy = px + nx * off, py + ny * off
                            # rond de sélection toujours INFÉRIEUR à la case :
                            # diamètre extérieur (2r+2) < cell, et r <= half*0.45
                            # pour rester dans sa file (ne touche pas l'autre file)
                            r = max(1, min(int((cell - 2) * 0.45), int(half * 0.45)))
                            pygame.draw.circle(self.screen, color,
                                               (int(cx), int(cy)), r, 2)

        # Extension Météo : animation sur TOUTE LA LONGUEUR de chaque tuile à
        # jeton (hors départ/arrivée) — les traits traversent toute la tuile,
        # ils ne sont pas limités à une case ; soleil (NONE) : un seul par tuile
        if getattr(self.game, "meteo", False):
            now = pygame.time.get_ticks()
            for tile in track.tiles:
                if tile.turn is not None or not tile.cells:
                    continue
                if any(c.run in (CellRunType.START, CellRunType.END) for c in tile.cells):
                    continue
                self._draw_weather_tile(tile.cells[0].weather, tile, geo, cell, half, now)

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
        # rayon borné par la taille de la case : la pastille + son anneau blanc
        # restent plus petites que la case (2*(radius+2) < cell)
        radius = max(2, min(int(geo["lane_w"] * 0.55), int(geo["cell"] * 0.5) - 3))

        players_by_runner = {r.id: p for p in self.game.players
                             for r in p.get_runners()}
        now = pygame.time.get_ticks()
        anims = {}
        for a in self.animations:  # la dernière animation par coureur gagne
            if now < a["t0"] + a["dur"]:
                anims[a["rid"]] = a
        for x, lane, runner in self.game.track.get_all_runners():
            player = players_by_runner[runner.id]
            a = anims.get(runner.id)
            if a:
                # glissade fluide le long du tracé : interpolation de
                # l'abscisse curviligne + de la file, easing ease-out
                t = min(1.0, (now - a["t0"]) / a["dur"])
                e = 1 - (1 - t) ** 3
                s0 = (a["from_x"] + 0.5) * geo["cell"]
                s1 = (a["to_x"] + 0.5) * geo["cell"]
                px, py, tx, ty = self._path_at(geo, s0 + (s1 - s0) * e)
                off0 = lane_off if a["from_lane"] == 0 else -lane_off
                off1 = lane_off if a["to_lane"] == 0 else -lane_off
                off = off0 + (off1 - off0) * e
            else:
                px, py, tx, ty = self._cell_anchor(x)
                cell0 = self.game.track.get_cell(x, 0)
                n_lanes = len(cell0.runners) if cell0 else 2
                if n_lanes <= 1:
                    off = 0
                elif n_lanes == 2:
                    off = lane_off if lane == 0 else -lane_off  # file A = droite
                else:
                    off = lane_off - lane * (2 * lane_off / (n_lanes - 1))
            nx, ny = -ty, tx
            cx = px + nx * off
            cy = py + ny * off

            color = PLAYER_COLORS.get(player.color, BLACK)
            # ombre douce + anneau blanc + pastille glossy (reflet haut-gauche)
            pygame.draw.ellipse(self.screen, (208, 213, 222),
                                (int(cx) - radius, int(cy) + radius - 3,
                                 radius * 2, 6))
            pygame.draw.circle(self.screen, WHITE, (int(cx), int(cy)), radius + 2)
            pygame.draw.circle(self.screen, color, (int(cx), int(cy)), radius)
            pygame.draw.circle(self.screen, _mix(color, WHITE, 0.45),
                               (int(cx) - radius // 3, int(cy) - radius // 3),
                               max(2, radius // 2))

            # Initiale du type de coureur, bien centrée DANS le cercle
            type_text = "S" if runner.type.name == "SPRINTER" else "R"
            type_surf = self.bold_font.render(type_text, True, BLACK)
            self.screen.blit(type_surf, type_surf.get_rect(center=(int(cx), int(cy))))

            # Extension Météo : coureur couché (chute sous la pluie) = croix rouge
            if runner.crashed:
                r = radius + 3
                pygame.draw.line(self.screen, (200, 30, 30),
                                 (cx - r, cy - r), (cx + r, cy + r), 3)
                pygame.draw.line(self.screen, (200, 30, 30),
                                 (cx - r, cy + r), (cx + r, cy - r), 3)

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

    def _grad_fill(self, rect, c_top, c_bot, radius=BTN_R):
        """Remplissage en dégradé vertical (haut -> bas) dans un rect arrondi.
        radius > 0 : le dégradé est découpé par un masque à coins arrondis
        (sinon simples lignes, pour les fonds plein écran en radius=0)."""
        if radius and radius > 0:
            s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            for i in range(rect.h):
                t = i / max(1, rect.h - 1)
                pygame.draw.line(s, _mix(c_top, c_bot, t), (0, i), (rect.w, i))
            mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.w, rect.h),
                             border_radius=min(radius, rect.w // 2, rect.h // 2))
            s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(s, (rect.x, rect.y))
            return
        for i in range(rect.h):
            t = i / max(1, rect.h - 1)
            c = _mix(c_top, c_bot, t)
            pygame.draw.line(self.screen, c, (rect.x, rect.y + i), (rect.right, rect.y + i))

    def _draw_header(self):
        """Bandeau de titre moderne : pastille logo, titre, pastille étape/tour."""
        pygame.draw.rect(self.screen, HEADER_BG, (0, 0, self.width, HEADER_H))
        # ombre douce sous le bandeau
        s = pygame.Surface((self.width, 8), pygame.SRCALPHA)
        for i in range(8):
            a = int(30 * (1 - i / 8))
            pygame.draw.line(s, (30, 35, 45, a), (0, i), (self.width, i))
        self.screen.blit(s, (0, HEADER_H))

        # Pastille logo : carré arrondi rouge avec fanion blanc
        chip = pygame.Rect(16, 10, 40, 40)
        pygame.draw.rect(self.screen, ACCENT, chip, border_radius=11)
        pygame.draw.polygon(self.screen, WHITE,
                            ((chip.x + 10, chip.y + 9), (chip.x + 30, chip.y + 16),
                             (chip.x + 10, chip.y + 23)))

        # Titre bicolore
        flamme = self.title_font.render("FLAMME ", True, INK)
        rouge = self.title_font.render("ROUGE", True, ACCENT)
        ty = (HEADER_H - max(flamme.get_height(), rouge.get_height())) // 2
        self.screen.blit(flamme, (66, ty))
        self.screen.blit(rouge, (66 + flamme.get_width(), ty))

        # Étape et tour en pastille (chip), juste après le titre (en partie)
        if self.game is not None:
            stage_name = STAGE_NAMES.get(self.game.stage, self.game.stage)
            info = self.label_font.render(
                f"{stage_name} · Tour {self.game.turn_count}", True, INK)
            ix = 66 + flamme.get_width() + rouge.get_width() + 18
            chip = pygame.Rect(ix, (HEADER_H - 30) // 2, info.get_width() + 24, 30)
            pygame.draw.rect(self.screen, PANEL_ALT, chip, border_radius=CHIP_R)
            pygame.draw.rect(self.screen, BORDER, chip, width=1, border_radius=CHIP_R)
            self.screen.blit(info, (chip.x + 12, chip.centery - info.get_height() // 2))
            # contrôles en une ligne au milieu du bandeau (tronquée avant les boutons)
            controls = (f"H mains · D decks · J histo · R restart · "
                        f"+/- zoom x{self.zoom:.2f} · flèches/clic gauche pan")
            cx = chip.right + 16
            max_w = self._camera_button_rects()["peloton"].x - 16 - cx
            csurf = self.small_font.render(controls, True, TEXT_DIM)
            if csurf.get_width() > max_w > 0:
                # tronque le texte pour ne jamais toucher les boutons
                while controls and self.small_font.render(controls + "…", True, (0, 0, 0)).get_width() > max_w:
                    controls = controls[:-1]
                csurf = self.small_font.render(controls + "…", True, TEXT_DIM)
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
        # pastille de phase FLOTTANTE et centrée (pas un bandeau plein largeur) :
        # fond teinté, bordure couleur, pastille indicatrice, texte foncé
        name_surf = self.phase_font.render(label, True, _mix(color, BLACK, 0.45))
        desc_surf = self.label_font.render(desc, True, (60, 66, 78))
        pw = 14 + 10 + name_surf.get_width() + 18 + desc_surf.get_width() + 16
        pw = min(pw, self.width - 240)  # laisser la place au bouton retour à droite
        pill = pygame.Rect((self.width - pw) // 2, rect.y + 4, pw, PHASE_H - 8)
        pygame.draw.rect(self.screen, _mix(color, WHITE, 0.86), pill, border_radius=CHIP_R)
        pygame.draw.rect(self.screen, color, pill, width=1, border_radius=CHIP_R)
        pygame.draw.circle(self.screen, color, (pill.x + 16, pill.centery), 6)
        self.screen.blit(name_surf, (pill.x + 30, pill.centery - name_surf.get_height() // 2))
        self.screen.blit(desc_surf, (pill.x + 30 + name_surf.get_width() + 18,
                                     pill.centery - desc_surf.get_height() // 2))

        # Bouton « retour » en haut à droite, DANS le bandeau de phase (hors du
        # bandeau FLAMME ROUGE) : fait comme ÉCHAP (retour au menu)
        self._draw_ui_button(self._back_button_rect(), "← Retour", (90, 96, 110),
                             pygame.mouse.get_pos())

    def _back_button_rect(self):
        """Bouton « ← Retour » en haut à droite. Dans les menus : dans le
        bandeau titre (bien en haut). En partie : dans le bandeau de phase,
        hors du bandeau titre FLAMME ROUGE."""
        if self.game is None:
            return pygame.Rect(self.width - 112, 12, 100, 34)
        return pygame.Rect(self.width - 104, HEADER_H + 4 + (PHASE_H - 26) // 2,
                           96, 26)

    def _group_names(self):
        """Une entrée par pack, de l'avant vers l'arrière : le premier est la
        « tête de course », le plus gros le « peloton », le dernier la
        « lanterne rouge », les autres « groupe <cycliste connu> ».
        Retourne [(label, [runners], case du coureur le plus avancé), ...]."""
        groups = list(reversed(self.game.track.get_groups()))  # avant -> arrière
        if not groups:
            return []
        biggest = max(range(len(groups)), key=lambda i: len(groups[i]))
        out = []
        ci = 0
        for i, g in enumerate(groups):
            if len(groups) == 1:
                label = "Peloton"
            elif i == 0:
                label = "Tête de course"
            elif i == biggest:
                label = "Peloton"
            elif i == len(groups) - 1:
                label = "Lanterne rouge"
            else:
                label = f"Groupe {CYCLISTES_CONNUS[ci % len(CYCLISTES_CONNUS)]}"
                ci += 1
            out.append((label, g, max(r.x for r in g)))
        return out

    def _race_profile_rect(self) -> pygame.Rect:
        """Panneau du profil de course EN COURS : SOUS le parcours, dans le
        bandeau plein largeur entre le cadre du parcours et la barre du bas."""
        strip = self._profile_strip_rect()
        return pygame.Rect(strip.x + 6, strip.y + 4, strip.w - 12, strip.h - 8)

    def _race_profile_markers(self):
        """Marqueurs des groupes sur le profil de course :
        [(case du coureur le plus avancé, couleur équipe, libellé court)]."""
        players_by_runner = {r.id: p for p in self.game.players
                             for r in p.get_runners()}
        out = []
        for label, group, lead_x in self._group_names():
            lead = max(group, key=lambda r: r.x)
            color = PLAYER_COLORS.get(players_by_runner[lead.id].color, BLACK)
            out.append((lead_x, color, label))  # nom complet du groupe
        return out

    def _game_weather_tiles(self):
        """[(case de début de tuile, WeatherType)] pour chaque tuile avec un
        jeton météo (icônes animées à leur emplacement sur le profil)."""
        if self.game is None or not getattr(self.game, "meteo", False):
            return []
        return [(t.x, t.length, t.cells[0].weather) for t in self.game.track.tiles
                if t.turn is None and t.cells
                and not any(c.run in (CellRunType.START, CellRunType.END) for c in t.cells)]

    def _draw_race_profile(self):
        """Profil d'altitude de la course en cours, en haut à droite du cadre du
        parcours, avec un marqueur par groupe (tête de course, peloton, ...) et
        le badge météo animé si l'extension Météo est active."""
        if self.game is None:
            return
        rect = self._race_profile_rect()
        alt = self._stage_profile(self.game.stage, code=self.game.custom_code)
        self._draw_profile_array(alt, rect, markers=self._race_profile_markers(),
                                 weather_tiles=self._game_weather_tiles() or None)

    def _draw_ui(self):
        self._draw_header()
        self._draw_phase_band()
        self._draw_race_profile()  # panneau groupes -> noms des groupes SUR le profil

        info_x = self._left_w() + 16  # (les compteurs/infos sont dans le bandeau de phase)
        # Barre du bas : panneau de cartes du joueur en cours (en bas à gauche)
        # + petit écran "ce qui se passe" (historique) à sa droite — toujours visibles
        if self.show_hands:
            bar = self._bar_rect()
            self._draw_card(bar, (244, 246, 250), radius=CARD_R)
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
        labels = {"tete": ("Tête de course", ROW_SEL, not self.game.game_over, "loupe"),
                  "peloton": ("Peloton", ROW_SEL, not self.game.game_over, "groupe"),
                  "ensemble": ("Vue d'ensemble", ROW_SEL, True, "rect")}
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

        # Légende des couleurs du circuit (bas du cadre) en PASTILLES (chips) :
        # chaque item = pill arrondi avec pastille couleur + libellé
        legend_y = self._frame_rect().bottom - 26  # légende en bas du cadre du parcours
        legend_x = self._left_w() + 20
        items = [((255, 236, 130), "Départ"), ((240, 210, 60), "Arrivée"),
                 (UPHILL_FILL, "Montée"), (DOWNHILL_FILL, "Descente")]
        if getattr(self.game, "peloton", False):
            items += [(COBBLE_FILL, "Pavés"), (SUPPLY_FILL, "Appro")]
        for swatch, label in items:
            text_surf = self.small_font.render(label, True, INK)
            chip = pygame.Rect(legend_x, legend_y, 14 + 8 + text_surf.get_width() + 12, 22)
            pygame.draw.rect(self.screen, PANEL_ALT, chip, border_radius=CHIP_R)
            pygame.draw.rect(self.screen, BORDER, chip, width=1, border_radius=CHIP_R)
            pygame.draw.circle(self.screen, swatch,
                               (chip.x + 12, chip.centery), 6)
            pygame.draw.circle(self.screen, BORDER,
                               (chip.x + 12, chip.centery), 6, 1)
            self.screen.blit(text_surf, (chip.x + 24, chip.centery - text_surf.get_height() // 2))
            legend_x += chip.w + 8

        # Écran de victoire : overlay podium (le bouton est dans le bandeau de titre)
        # (TAB ou le bouton basculent avec l'état final du circuit)
        if self.game.game_over and self.show_podium:
            self._draw_podium()

    def _draw_podium(self):
        """Écran de fin de course : podium des 3 premiers coureurs."""
        game = self.game
        # voile assombri sur toute la partie derrière le podium
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        veil.fill((20, 24, 32, 110))
        self.screen.blit(veil, (0, 0))
        overlay = pygame.Rect(self.width // 2 - 290, self.height // 2 - 250, 580, 460)
        self._draw_card(overlay, PANEL, radius=16)
        pygame.draw.rect(self.screen, (240, 210, 60), overlay, width=2, border_radius=14)
        title = self.title_font.render("VICTOIRE", True, (240, 210, 60))
        self.screen.blit(title, title.get_rect(center=(overlay.centerx, overlay.y + 34)))

        rank = game.ranking()[:3]
        heights = [130, 95, 70]     # 1er, 2e, 3e
        offsets = [0, -1, 1]        # 1er au CENTRE, 2e à gauche, 3e à droite
        base_y = overlay.bottom - 46
        medals = [(240, 210, 60), (192, 198, 208), (205, 127, 50)]  # or/argent/bronze
        for i, entry in enumerate(rank):
            x = overlay.centerx + offsets[i] * 130 - 55
            h = heights[i]
            # barre en dégradé + médaille au-dessus
            self._grad_fill(pygame.Rect(x, base_y - h, 110, h),
                            _mix(medals[i], WHITE, 0.35), medals[i], 10)
            pygame.draw.rect(self.screen, _mix(medals[i], BLACK, 0.25),
                             (x, base_y - h, 110, h), width=1, border_radius=10)
            pygame.draw.circle(self.screen, medals[i], (x + 55, base_y - h - 20), 16)
            pygame.draw.circle(self.screen, _mix(medals[i], BLACK, 0.25),
                               (x + 55, base_y - h - 20), 16, 2)
            num = self.big_font.render(str(i + 1), True, INK)
            self.screen.blit(num, num.get_rect(center=(x + 55, base_y - h - 20)))
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
                                      True, TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(overlay.centerx, overlay.bottom + 16)))

    def _history_lines(self):
        """Lignes d'historique (texte, couleur, gras), ORDRE CHRONOLOGIQUE.
        - une ligne vide avant chaque nouveau tour
        - nom du tour et des phases en GRAS
        - chaque phrase liée à une équipe est dans la couleur de l'équipe."""
        # id de coureur -> (nom affiché, couleur équipe)
        names = {}
        for p in self.game.players:
            for r in p.get_runners():
                kind = "Sprinteur" if r.type.name == "SPRINTER" else "Rouleur"
                names[r.id] = (f"{kind} {r.id.split('_')[-1]}",
                               PLAYER_COLORS.get(p.color, TEXT_DIM))
        lines = []
        for entry in self.game.history:
            if lines:
                lines.append(("", None, False))  # ligne vide entre les tours
            lines.append((f"TOUR {entry['turn']}" if entry["turn"] else "Météo de la course",
                          (180, 140, 20), True))
            if entry["cards"]:
                lines.append(("Énergie", TEXT_DIM, True))
                for color, rid, val in entry["cards"]:
                    name, team = names.get(rid, (rid, PLAYER_COLORS.get(
                        color, TEXT_DIM)))
                    # la carte est face cachée : on n'affiche pas sa valeur
                    lines.append((f"  {name} pose une carte face cachée", team, False))
            if entry["moves"]:
                lines.append(("Mouvement", TEXT_DIM, True))
                for rid, color, fx, tx, val, eff, reason in entry["moves"]:
                    name, team = names.get(rid, (rid, PLAYER_COLORS.get(
                        color, (60, 140, 70))))
                    txt = f"  {name} avance de {tx - fx} case(s) : de {fx} à {tx}"
                    if reason:
                        txt += f" ({reason})"
                    lines.append((txt, team, False))
            if entry["slips"]:
                lines.append(("Aspiration", TEXT_DIM, True))
                for slip in entry["slips"]:
                    who = ", ".join(names.get(rid, (rid, BLACK))[0]
                                    for rid, fx, tx in slip)
                    desc = ", ".join(f"{fx}->{tx}" for rid, fx, tx in slip)
                    lines.append((f"  {who} glisse d'1 case ({desc})",
                                  (200, 110, 0), False))
            if entry.get("weather"):
                lines.append(("Météo", TEXT_DIM, True))
                wlabels = {"TAILWIND": "vent arrière (pioche 5)",
                           "HEADWIND": "vent de face (pioche 3)",
                           "CROSSWIND": "vent de travers (pas d'aspiration)",
                           "RAIN": "pluie (chute si bloqué)"}
                for tile_x, wname in entry["weather"]:
                    lines.append((f"  Tuile {tile_x} : {wlabels.get(wname, wname)}",
                                  (90, 130, 200), False))
        return lines

    def _draw_log_panel(self):
        """Petit écran à droite du panneau de cartes : ce qui se passe
        (dernières lignes de l'historique), toujours visible."""
        rect = self._log_panel_rect()
        self._draw_card(rect, PANEL, radius=10)
        # en-tête : pastille + titre + séparateur
        pygame.draw.circle(self.screen, ACCENT, (rect.x + 15, rect.y + 15), 5)
        hsurf = self.label_font.render("Historique", True, INK)
        self.screen.blit(hsurf, (rect.x + 26, rect.y + 7))
        pygame.draw.line(self.screen, BORDER,
                         (rect.x + 10, rect.y + 30), (rect.right - 10, rect.y + 30), 1)
        lines = self._history_lines()
        line_h = 15
        max_lines = (rect.bottom - rect.y - 38) // line_h  # -38 : en-tête réservé
        max_scroll = max(0, len(lines) - max_lines)
        self.log_scroll = max(0, min(max_scroll, self.log_scroll))
        # ancré en bas : les plus récentes en dernier (en bas), les nouvelles
        # poussent les autres vers le haut ; log_scroll = lignes cachées en haut
        start = max(0, len(lines) - max_lines - self.log_scroll)
        visible = lines[start:start + max_lines]
        self._log_line_rects = []  # (index_absolu, y, h) pour la sélection
        y = rect.bottom - 6 - line_h * len(visible)
        for i, (txt, color, bold) in enumerate(visible):
            self._log_line_rects.append((start + i, y, line_h))
            # surbrillance de la sélection (texte sélectionnable)
            if self.log_sel and self.log_sel[0] <= start + i <= self.log_sel[1]:
                pygame.draw.rect(self.screen, (70, 110, 170),
                                 (rect.x + 6, y - 1, rect.w - 12, line_h))
            if not txt:
                y += line_h
                continue  # ligne vide entre les tours
            font = self.bold_font if bold else self.small_font
            surf = font.render(txt, True, color if color else (200, 205, 215))
            self.screen.blit(surf, (rect.x + 10, y))
            y += line_h
        # indicateur de scroll (sans le mot « molette »)
        if max_scroll > 0:
            hint = self.small_font.render(f"▲ {self.log_scroll}/{max_scroll}",
                                          True, TEXT_DIM)
            self.screen.blit(hint, (rect.right - 10 - hint.get_width(), rect.y + 6))

    def _log_line_at(self, pos):
        """Index absolu de la ligne de log sous la position pos (ou None)."""
        rect = self._log_panel_rect()
        if not rect.collidepoint(pos):
            return None
        for idx, y, h in getattr(self, "_log_line_rects", []):
            if y - 2 <= pos[1] <= y + h:
                return idx
        return None

    def _log_copy_selection(self):
        """Copie la sélection du log dans le presse-papiers (Ctrl+C)."""
        if not self.log_sel:
            return
        a, b = sorted(self.log_sel)
        lines = self._history_lines()
        text = "\n".join(l[0] for l in lines[a:b + 1] if l[0])
        try:
            pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
            self.last_action = ("Texte copié dans le presse-papiers", (46, 125, 50))
        except Exception:
            pass

    def _draw_history(self):
        """Overlay historique complet (touche J) : toutes les lignes."""
        rect = pygame.Rect(self.width - 370, TOP_H + 8, 358,
                           self.height - TOP_H - 60)
        self._draw_card(rect, PANEL, radius=12)
        title = self.phase_font.render("Historique des coups", True, BLACK)
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
            color = PLAYER_COLORS.get(r.color, BLACK)
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
        # onglets des joueurs en contrôle segmenté : conteneur + pastille active
        tabs = self._player_tab_rects()
        if tabs:
            cont = tabs[0]
            for tb in tabs[1:]:
                cont = cont.union(tb)
            cont = cont.inflate(10, 8)
            pygame.draw.rect(self.screen, PANEL_ALT, cont, border_radius=CHIP_R)
            pygame.draw.rect(self.screen, BORDER, cont, width=1, border_radius=CHIP_R)
        for i, (player, tab) in enumerate(zip(self.game.players, tabs)):
            active = (i == self.current_player_idx)
            hovered = tab.collidepoint(mouse)
            color = PLAYER_COLORS.get(player.color, BLACK)
            if active:
                fill = color
                txt = WHITE
            elif hovered:
                fill = _mix(color, WHITE, 0.75)
                txt = INK
            else:
                fill = PANEL_ALT
                txt = TEXT_DIM
            pygame.draw.rect(self.screen, fill, tab, border_radius=CHIP_R)
            t = self.small_font.render(player.color[:4], True, txt)
            self.screen.blit(t, t.get_rect(center=tab.center))
        for player, panel, rows in self._hand_layout():
            color = PLAYER_COLORS.get(player.color, BLACK)

            # Panneau du joueur : carte avec ombre + liseré couleur d'équipe
            self._draw_card(panel, (250, 250, 248), radius=10)
            pygame.draw.rect(self.screen, color, panel, width=2, border_radius=10)

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
                    if hovered:
                        # lift au survol : petite ombre sous la carte
                        sh = pygame.Surface((rect.w + 6, rect.h + 8), pygame.SRCALPHA)
                        pygame.draw.rect(sh, (*SHADOW_RGB, 40), (3, 5, rect.w, rect.h),
                                         border_radius=R_SM)
                        self.screen.blit(sh, (rect.x - 3, rect.y - 2))
                    pygame.draw.rect(self.screen, fill, rect, border_radius=R_SM)
                    pygame.draw.rect(self.screen, border, rect, width=width, border_radius=R_SM)
                    value_text = str(card.value) + ("F" if card.type == CardType.FATIGUE else "")
                    if card.type == CardType.FATIGUE:
                        vcol = (180, 90, 0)
                    else:
                        # dégradé de couleur selon la valeur (2 = neutre, 8 = accent)
                        vcol = _mix(TEXT_DIM, ACCENT, min(1.0, max(0.0, (card.value - 2) / 6)))
                    val_surf = self.card_font.render(value_text, True, vcol if not is_played else text_color)
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
