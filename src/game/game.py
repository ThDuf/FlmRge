import random
import math
from typing import List, Optional, Dict
from enum import Enum, auto
from .player import Player
from .runner import Runner, RunnerType
from .card import Card, CardType
from .track import Track, make_tile, CellGeographyType, CellRunType


# ------------------------------------------------------------------
# Étapes officielles (rulebook Lautapelit.fi / Dized)
# ------------------------------------------------------------------
# Chaque étape officielle est codée par les lettres de ses 21 tuiles
# (espaces ignorés). Face minuscule = côté normal, majuscule = montagne.
OFFICIAL_STAGES = {
    "Avenue Corso Paseo": "abcdefghijklmnopqrstu",          # plate (tutoriel)
    "Firenze - Milano": "abcgi D H qntm K O L rep J sfu",
    "Ronde van Wevelgem": "abcmgfteqon L P jk I D H r S u",
    "La Haut Montagne": "abcfimet K G L H J sdop R Q N U",  # très montagneuse
    "La Classicissima": "A eb Q R N H P cgik D F s L ojmtu",
    "Col du Ballon": "AnLHgceqtrMBoipjDFkSu",               # 6e carte de la boîte de base
}

# ------------------------------------------------------------------
# Catalogue complet des 21 tuiles officielles (a-u), une entrée par lettre.
# Chaque tuile = (virage, largeur, cases) :
# - virage = (angle en radians, sens +1/-1), None = ligne droite
#   (45° = virage léger, 90° = virage serré ; sens relevés sur la carte
#    imprimée Avenue Corso Paseo : e=G g=G h=G i=G j=D k=D o=D p=D
#    q=G r=D s=D t=G, avec G=+1, D=-1)
# - largeur = nombre de files de la tuile (2 en jeu de base)
# - cases = alphabet CELL_CHARS de track.py (f=plat, u=montée, d=descente,
#   s=ligne de départ, e=ligne d'arrivée) ; une droite fait 6 cases,
#   un virage 2, le départ 6 (ligne sur les 5 premières), l'arrivée 6
#   (ligne sur les 5 dernières)
# ------------------------------------------------------------------
TILE_DEFS = {
    'a': (None, 2, "sssssf"),   'u': (None, 2, "feeeee"),
    'b': (None, 2, "ffffff"),   'c': (None, 2, "ffffff"),
    'd': (None, 2, "ffffff"),   'f': (None, 2, "ffffff"),
    'l': (None, 2, "ffffff"),   'm': (None, 2, "ffffff"),
    'n': (None, 2, "ffffff"),
    'h': ((math.pi / 4, 1), 2, "ff"),   'k': ((math.pi / 4, -1), 2, "ff"),
    'q': ((math.pi / 4, 1), 2, "ff"),   'r': ((math.pi / 4, -1), 2, "ff"),
    's': ((math.pi / 4, -1), 2, "ff"),  't': ((math.pi / 4, 1), 2, "ff"),
    'e': ((math.pi / 2, 1), 2, "ff"),   'g': ((math.pi / 2, 1), 2, "ff"),
    'i': ((math.pi / 2, 1), 2, "ff"),   'j': ((math.pi / 2, -1), 2, "ff"),
    'o': ((math.pi / 2, -1), 2, "ff"),  'p': ((math.pi / 2, -1), 2, "ff"),
}

# Faces montagne (majuscules) : définition COMPLÈTE relevée sur les tuiles
# physiques (virage, largeur, cases case par case). Attention : le virage de
# la face montagne n'est PAS toujours le miroir de la face plate (ex. K
# tourne à droite, comme k). droite = sens -1, gauche = sens +1.
MOUNTAIN_DEFS = {
    'A': (None, 2, "ssssff"),            # départ
    'B': (None, 2, "ddddff"),            # descente sur les 4 premières cases
    'C': (None, 2, "fffuuu"),
    'D': (None, 2, "uuuuud"),
    'E': ((math.pi / 2, -1), 2, "uu"),   # virage 90° droite
    'F': (None, 2, "dddfff"),
    'G': ((math.pi / 2, -1), 2, "uu"),   # virage 90° droite
    'H': ((math.pi / 4, -1), 2, "dd"),   # virage 45° droite
    'I': ((math.pi / 2, -1), 2, "ff"),   # virage 90° droite
    'J': ((math.pi / 2, 1), 2, "ff"),    # virage 90° gauche
    'K': ((math.pi / 4, 1), 2, "uu"),    # virage 45° gauche
    'L': (None, 2, "uuuddd"),
    'M': (None, 2, "ffuuuu"),
    'N': (None, 2, "uuuuuu"),
    'O': ((math.pi / 2, 1), 2, "uu"),    # virage 90° gauche
    'P': ((math.pi / 2, 1), 2, "dd"),    # virage 90° gauche
    'Q': ((math.pi / 4, -1), 2, "uu"),   # virage 45° droite
    'R': ((math.pi / 4, 1), 2, "uu"),    # virage 45° gauche
    'S': ((math.pi / 4, 1), 2, "ff"),    # virage 45° gauche
    'T': ((math.pi / 4, -1), 2, "ff"),   # virage 45° droite
    'U': (None, 2, "uueeee"),            # arrivée : 2 cases de montée puis la ligne
}


def tile_def_for_letter(ch: str):
    """(virage, largeur, cases) pour une lettre de code de stage (a-u / A-U)."""
    if ch.isupper():
        return MOUNTAIN_DEFS[ch]
    return TILE_DEFS[ch]


def build_tile(ch: str) -> 'Tile':
    """Construit la tuile d'une lettre de code de stage (a-u / A-U)."""
    from .track import Tile
    turn, width, chars = tile_def_for_letter(ch)
    return make_tile(chars, turn=turn, width=width, letter=ch)


def build_track_from_code(code: str) -> Track:
    """Construit une piste en mettant les tuiles bout à bout, dans l'ordre
    du code de stage (lettres a-u / A-U, espaces ignorés)."""
    track = Track()
    for ch in code:
        if ch.strip():
            track.add_tile(build_tile(ch))
    return track


def build_stage_track(name: str) -> Track:
    """Construit la piste d'une étape nommée (officielle, ou 'test')."""
    if name in OFFICIAL_STAGES:
        return build_track_from_code(OFFICIAL_STAGES[name])
    if name == "test":
        track = Track()
        track.add_tile(make_tile("sssssf"))
        for _ in range(4):
            track.add_tile(make_tile("ffffff"))
        track.add_tile(make_tile("feeeee"))
        return track
    # Inconnu -> étape tutorielle par défaut
    return build_track_from_code(OFFICIAL_STAGES["Avenue Corso Paseo"])


def available_stages() -> List[tuple]:
    """Étapes jouables : [(nom, description, code), ...] — les étapes
    officielles du rulebook."""
    result = []
    for name in OFFICIAL_STAGES:
        track = build_stage_track(name)
        cells = [c for t in track.tiles for c in t.cells]
        n_up = sum(1 for c in cells if c.geography == CellGeographyType.UPHILL)
        n_down = sum(1 for c in cells if c.geography == CellGeographyType.DOWNHILL)
        n_sharp = sum(1 for t in track.tiles
                      if t.turn is not None and abs(t.turn[0]) >= math.pi / 2)
        parts = [f"{track.length} cases"]
        if n_sharp:
            parts.append(f"{n_sharp} virage(s) serré(s)")
        if n_up:
            parts.append(f"{n_up} montée(s)")
        if n_down:
            parts.append(f"{n_down} descente(s)")
        if not (n_sharp or n_up or n_down):
            parts.append("plat")
        result.append((name, " · ".join(parts), OFFICIAL_STAGES.get(name, "")))
    return result


class Phase(Enum):
    ENERGY = auto()    # Phase d'Énergie
    MOVEMENT = auto()  # Phase de Mouvement
    ASPIRATION = auto()  # Phase d'Aspiration
    TERMINAL = auto()  # Phase Terminale


class Game:
    """Moteur principal du jeu Flamme Rouge."""

    def __init__(self, stage: str = "Avenue Corso Paseo", player_count: int = 2):
        player_count = max(2, min(4, player_count))  # 2 à 4 joueurs
        self.stage = stage
        self.players: List[Player] = []
        self.track = self._build_track(stage)
        self.current_phase: Phase = Phase.ENERGY
        self.turn_count: int = 0
        self.game_over: bool = False
        self.winner: Optional[Player] = None
        self.cards_played_this_turn = 0
        self.total_cards_to_play = 0
        self.cards_played_per_runner = {}

        # Initialiser les joueurs
        self._initialize_players(player_count)
        
        # Initialiser le compteur de cartes par coureur
        for player in self.players:
            for runner in player.get_runners():
                self.cards_played_per_runner[runner.id] = 0

        # Démarrer le premier tour
        self.start_turn()

    def _initialize_players(self, count: int) -> None:
        """Initialise les joueurs et leurs coureurs."""
        colors = ["red", "blue", "green", "yellow"][:count]
        for i, color in enumerate(colors):
            sprinter = Runner(
                id=f"sprinter_{i}",
                type=RunnerType.SPRINTER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.SPRINTER),
            )
            roller = Runner(
                id=f"roller_{i}",
                type=RunnerType.ROLLER,
                color=color,
                energy_deck=self._generate_energy_deck(RunnerType.ROLLER),
            )
            player = Player(id=f"player_{i}", color=color, sprinter=sprinter, roller=roller)
            self.players.append(player)

        # Placement au départ en round-robin pour l'équité : tous les
        # sprinteurs d'abord (à la première file libre), puis tous les
        # rouleurs. Les équipes démarrent ainsi sur des cases équivalentes.
        for player in self.players:
            self._place_runner_at_start(player.sprinter)
        for player in self.players:
            self._place_runner_at_start(player.roller)

    def _generate_energy_deck(self, runner_type: RunnerType) -> List[Card]:
        """Génère un deck Énergie de 15 cartes pour un coureur.
        
        Règles officielles :
        - Sprinteur : 15 cartes (2,2,3,3,4,4,5,5,6,6,6,7,7,7,8)
        - Rouleur : 15 cartes (2,2,2,3,3,3,4,4,4,5,5,5,6,6,7)
        """
        if runner_type == RunnerType.SPRINTER:
            # Deck officiel Sprinteur : 15 cartes
            values = [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 6, 7, 7, 7, 8]
            runner_str = "S"
        else:
            # Deck officiel Rouleur : 15 cartes
            values = [2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 7]
            runner_str = "R"

        random.shuffle(values)
        return [Card(value, CardType.ENERGY, runner_str) for value in values]

    def _build_track(self, stage: str) -> Track:
        """Construit la piste de l'étape choisie (officielle ou 'test')."""
        return build_stage_track(stage)

    def _place_runner_at_start(self, runner: Runner) -> None:
        """Place un coureur au départ dans la première file libre.

        Règle officielle : les coureurs sont placés DERNIÈRE la ligne de
        départ (cases x < start_line_x()), AU PLUS PROCHE de la ligne, dans
        n'importe quelle file libre ; une case vide se remplit toujours par
        la file de droite (A) d'abord. On remplit donc depuis la case
        limit-1 (la plus proche de la ligne) vers l'arrière, file A puis B.

        IMPORTANT : ne jamais laisser un coureur hors piste — un coureur
        non placé devient un « fantôme » dont le premier mouvement retirerait
        un autre coureur de sa case.
        """
        limit = self.track.start_line_x()  # la ligne est après les cases START
        for x in range(limit - 1, -1, -1):
            for lane in (0, 1):
                cell = self.track.get_cell(x, lane)
                if cell and cell.is_empty(lane):
                    cell.set_runner(runner, lane)
                    return
        raise RuntimeError(f"Placement impossible : {runner.id} (zone de départ pleine)")

    def start_turn(self) -> None:
        """Démarre un nouveau tour."""
        self.turn_count += 1
        self.current_phase = Phase.ENERGY
        self.cards_played_this_turn = 0
        self.total_cards_to_play = 0

        for player in self.players:
            player.draw_cards_for_all(4)
            for runner in player.get_runners():
                if runner.hand:
                    self.cards_played_per_runner[runner.id] = 0
                    self.total_cards_to_play += 1
                else:
                    # Cas limite : plus aucune carte nulle part (deck et
                    # défausse vides). Le coureur est marqué comme ayant
                    # déjà joué (il n'avance pas ce tour), sinon la partie
                    # se bloquerait sans jamais être "prête".
                    self.cards_played_per_runner[runner.id] = 1

    def play_card(self, player: Player, runner: Runner, card: Card) -> bool:
        """Joue une carte pour un coureur."""
        if self.current_phase != Phase.ENERGY:
            return False
        if card not in runner.hand:
            return False
        if self.cards_played_per_runner[runner.id] >= 1:
            print(f"[ATTENTION] {runner.id} a deja joue sa carte ce tour !")
            return False

        runner.play_card(card)
        self.cards_played_per_runner[runner.id] = 1
        self.cards_played_this_turn += 1
        return True

    def all_players_ready(self) -> bool:
        """Vérifie si chaque joueur a joué 2 cartes (1 par coureur)."""
        return self.cards_played_this_turn >= self.total_cards_to_play

    def resolve_movement_phase(self) -> List:
        """
        Calcule l'ordre des mouvements de la phase de mouvement SANS les
        appliquer.

        Règle officielle : on déplace d'abord le coureur le plus en
        avant ; à égalité de position, la file A (file de droite,
        double ligne) est considérée en tête et bouge en premier.

        Retourne la liste [(runner, valeur_de_carte), ...], à appliquer
        un par un via apply_movement_step(). La destination de chaque
        coureur n'est calculée qu'au moment de SON déplacement, pour
        tenir compte des coureurs déplacés avant lui (arrêts derrière
        une case pleine, etc.).
        """
        if self.current_phase != Phase.ENERGY:
            return []

        self.current_phase = Phase.MOVEMENT
        print("\n--- PHASE DE MOUVEMENT ---")

        all_runners = []
        for player in self.players:
            all_runners.extend(player.get_runners())
        all_runners.sort(key=lambda r: (-r.x, r.y))

        moves = [(runner, runner.played_card.value)
                 for runner in all_runners if runner.played_card is not None]

        print(f"Ordre de déplacement (du plus proche au plus loin) : "
              f"{[r.id for r, _v in moves]}")
        print(f"--- Fin du calcul du mouvement ({len(moves)} coureurs) ---\n")
        return moves

    def apply_movement_step(self, move) -> None:
        """Applique UN mouvement de coureur (pour le pas-à-pas UI)."""
        runner, value = move
        print(f"  {runner.id} (pos {runner.x}) joue carte {value}")
        self.track.move_runner(runner, value)
        print(f"    -> Déplacé à {runner.x}, file {runner.y}")

    def apply_movement_steps(self, moves: List) -> None:
        """Applique tous les mouvements (usage headless)."""
        for move in moves:
            self.apply_movement_step(move)

    def resolve_aspiration_phase(self) -> List:
        """
        Calcule les mouvements d'aspiration SANS les appliquer.

        Règle officielle : "Si exactement une case vide sépare deux packs,
        le pack arrière avance d'une case pour fusionner avec celui de
        devant. Puis on revérifie le pack fusionné (un coureur peut aspirer
        plusieurs fois dans le même tour)."

        Retourne la liste des étapes (une étape = les mouvements d'un pack),
        à appliquer via Game.apply_slipstream_step() ou
        Game.apply_aspiration_steps().
        """
        if self.current_phase != Phase.MOVEMENT:
            return []

        self.current_phase = Phase.ASPIRATION
        print("\n--- PHASE D'ASPIRATION ---")

        groups = self.track.get_groups()
        print(f"Packs avant aspiration : {len(groups)} packs")
        for i, group in enumerate(groups):
            positions = [r.x for r in group]
            print(f"  Pack {i}: coureurs à positions {positions}")

        steps = self.track.compute_slipstream_steps()

        for i, step in enumerate(steps):
            desc = ", ".join(f"{r.id} {fx},{fl}->{tx},{tl}" for r, fx, fl, tx, tl in step)
            print(f"  Etape {i + 1}: {desc}")

        print(f"--- Fin du calcul d'aspiration ({len(steps)} étapes) ---\n")
        return steps

    def apply_slipstream_step(self, step) -> None:
        """Applique UNE étape d'aspiration sur le plateau (pour le pas-à-pas UI)."""
        self.track.apply_slipstream_step(step)

    def apply_aspiration_steps(self, steps: List) -> None:
        """Applique toutes les étapes d'aspiration (usage headless)."""
        for step in steps:
            self.track.apply_slipstream_step(step)

    def _assign_fatigue_cards(self) -> list:
        """
        Attribue les cartes Fatigue selon les règles officielles.

        Règle : "Un coureur est fatigué si la CASE devant lui est vide"
        (les 2 files vides). Une simple file libre devant lui ne suffit
        PAS — dans une vraie course, le pack roule au milieu de la route.
        Chaque coureur dans cette situation reçoit une carte Fatigue
        (valeur 2), recyclée dans son deck.

        Retourne la liste des coureurs ayant reçu une carte Fatigue.
        """
        tired = []
        for player in self.players:
            for runner in player.get_runners():
                if self.track.is_square_empty(runner.x + 1):
                    fatigue_card = Card(2, CardType.FATIGUE,
                                        "S" if runner.type == RunnerType.SPRINTER else "R")
                    runner.discard_pile.append(fatigue_card)
                    tired.append(runner)
                    print(f"  {runner.id} est fatigué (case devant vide) -> carte Fatigue (valeur 2)")
        return tired

    def _cleanup_hands(self) -> None:
        """Nettoie les mains des coureurs pour le prochain tour.

        Règles officielles : les cartes non jouées sont recyclées, la
        carte jouée est RETIRÉE DU JEU (le deck s'épuise au fil de la
        course). Le remélange des cartes recyclées se fait à la pioche
        quand le deck est vide (cf. Runner.draw_cards).
        """
        for player in self.players:
            for runner in player.get_runners():
                runner.reset_hand()

    def _check_win_condition(self) -> bool:
        """Vérifie si un coureur a franchi la ligne d'arrivée.

        Règle officielle : la course se termine quand un coureur franchit la
        ligne d'arrivée (début de la tuile d'arrivée, qui offre 5 cases au-delà
        de la ligne) ; si plusieurs franchissent dans le même tour, le plus
        loin devant gagne ; à égalité, la file A (file de droite) est en tête.
        """
        track = self.track
        finish_x = track.end_line_x()  # case de la ligne d'arrivée
        best = None
        for player in self.players:
            for runner in player.get_runners():
                if runner.x >= finish_x:
                    key = (runner.x, -runner.y)  # plus loin devant, puis file A
                    if best is None or key > best[0]:
                        best = (key, player, runner)
        if best is not None:
            self.winner = best[1]
            return True
        return False

    def get_current_phase_name(self) -> str:
        """Retourne le nom de la phase actuelle."""
        return self.current_phase.name

    def get_state(self) -> Dict:
        """Retourne l'état actuel du jeu."""
        return {
            "turn": self.turn_count,
            "phase": self.current_phase.name,
            "players": [
                {
                    "id": player.id,
                    "color": player.color,
                    "sprinter": {
                        "x": player.sprinter.x,
                        "y": player.sprinter.y,
                        "hand": [card.value for card in player.sprinter.hand],
                        "discard": [card.value for card in player.sprinter.discard_pile],
                    },
                    "roller": {
                        "x": player.roller.x,
                        "y": player.roller.y,
                        "hand": [card.value for card in player.roller.hand],
                        "discard": [card.value for card in player.roller.discard_pile],
                    },
                }
                for player in self.players
            ],
            "track_length": self.track.length,
            "game_over": self.game_over,
            "winner": self.winner.id if self.winner else None,
        }
