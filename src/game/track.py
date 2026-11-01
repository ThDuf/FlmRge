from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum, auto
import math
from .runner import Runner


class TileType(Enum):
    START = auto()      # Départ
    FINISH = auto()     # Arrivée
    STRAIGHT = auto()   # Ligne droite
    LIGHT_TURN = auto() # Virage léger
    SHARP_TURN = auto() # Virage serré
    UPHILL = auto()     # Montée (rouge)
    DOWNHILL = auto()   # Descente (bleue)


@dataclass
class Cell:
    """Représente une case sur la piste (avec 2 files: A et B)."""
    a: Optional[Runner] = None  # File A (prioritaire)
    b: Optional[Runner] = None  # File B
    x: int = 0  # Position X de la case

    def is_empty(self, lane: int) -> bool:
        """Vérifie si une file est vide (0=A, 1=B)."""
        return (lane == 0 and self.a is None) or (lane == 1 and self.b is None)

    def is_full(self) -> bool:
        """Vérifie si la case est complètement occupée (2 coureurs)."""
        return self.a is not None and self.b is not None

    def get_runner(self, lane: int) -> Optional[Runner]:
        """Retourne le coureur dans une file (ou None)."""
        return self.a if lane == 0 else self.b

    def set_runner(self, runner: Runner, lane: int) -> bool:
        """Place un coureur dans une file. Retourne True si succès."""
        if not self.is_empty(lane):
            return False
        if lane == 0:
            self.a = runner
        else:
            self.b = runner
        runner.x, runner.y = self.x, lane
        return True

    def remove_runner(self, lane: int) -> Optional[Runner]:
        """Retire un coureur d'une file."""
        runner = self.get_runner(lane)
        if lane == 0:
            self.a = None
        else:
            self.b = None
        return runner


@dataclass
class Tile:
    """Représente une tuile de piste (composée de 2 cases)."""
    type: TileType
    cells: List[Cell] = field(default_factory=lambda: [Cell(), Cell()])
    x: int = 0  # Position X de la tuile
    direction: int = 1  # Sens du virage (+1/-1) ; purement visuel (pas de règle)

    def __post_init__(self):
        for i, cell in enumerate(self.cells):
            cell.x = self.x * 2 + i


# Angles des virages (pièces officielles : 45° = léger, 90° = serré)
TURN_ANGLE = {
    TileType.LIGHT_TURN: math.radians(45),
    TileType.SHARP_TURN: math.radians(90),
}


def compute_track_path(track: 'Track', unit: float = 1.0) -> List[Tuple[float, float]]:
    """Polyligne du circuit selon la séquence réelle des tuiles.

    Chaque tuile avance de 2*unit le long du chemin ; une tuile de virage
    courbe le cap de son angle (45° léger, 90° serré) dans sa direction.
    Retourne la liste des points (en unités de cases), cap initial vers +x.
    """
    pts = [(0.0, 0.0)]
    x, y, heading = 0.0, 0.0, 0.0
    for tile in track.tiles:
        if tile.type in TURN_ANGLE:
            theta = TURN_ANGLE[tile.type] * getattr(tile, "direction", 1)
            arc = 2 * unit
            radius = arc / abs(theta)
            nx, ny = -math.sin(heading), math.cos(heading)  # normale au cap
            s = 1 if theta > 0 else -1
            cx = x + s * radius * nx
            cy = y + s * radius * ny
            vx, vy = -s * radius * nx, -s * radius * ny  # vecteur centre -> point
            steps = max(4, int(abs(theta) / (math.pi / 16)))
            for i in range(1, steps + 1):
                phi = theta * i / steps
                c, sn = math.cos(phi), math.sin(phi)
                pts.append((cx + vx * c - vy * sn, cy + vx * sn + vy * c))
            x, y = pts[-1]
            heading += theta
        else:
            x += 2 * unit * math.cos(heading)
            y += 2 * unit * math.sin(heading)
            pts.append((x, y))
    return pts


@dataclass
class Track:
    """Représente la piste complète."""
    tiles: List[Tile] = field(default_factory=list)
    length: int = 0

    def __post_init__(self):
        self.length = len(self.tiles) * 2

    def add_tile(self, tile_type: TileType, direction: int = 1) -> None:
        x = len(self.tiles)
        tile = Tile(tile_type, x=x, direction=direction)
        self.tiles.append(tile)
        self.length = len(self.tiles) * 2

    def get_cell(self, x: int, lane: int) -> Optional[Cell]:
        if x < 0 or x >= self.length:
            return None
        tile_index = x // 2
        cell_index = x % 2
        if tile_index < len(self.tiles):
            return self.tiles[tile_index].cells[cell_index]
        return None

    def tile_type_at(self, x: int) -> TileType:
        """Type de la tuile contenant la case x (STRAIGHT si hors piste)."""
        if x < 0 or x >= self.length:
            return TileType.STRAIGHT
        return self.tiles[x // 2].type

    def is_cell_empty(self, x: int, lane: int) -> bool:
        cell = self.get_cell(x, lane)
        return cell is not None and cell.is_empty(lane)

    def is_square_empty(self, x: int) -> bool:
        """Une CASE est vide si ses 2 files sont vides (règles officielles).

        Utilisée pour l'aspiration (écart entre packs) et la fatigue
        (« un coureur est fatigué si la CASE devant lui est vide » ;
        une simple file vide devant lui ne suffit pas).
        """
        cell = self.get_cell(x, 0)
        return cell is not None and cell.a is None and cell.b is None

    def get_all_runners(self) -> List[Tuple[int, int, Runner]]:
        """Retourne tous les coureurs avec leur position (x, lane, runner)."""
        runners = []
        for x in range(self.length):
            cell = self.get_cell(x, 0)
            if cell and cell.a:
                runners.append((x, 0, cell.a))
            if cell and cell.b:
                runners.append((x, 1, cell.b))
        return runners

    def effective_steps(self, x: int, card_value: int):
        """Déplacement effectif d'une carte selon les règles de montagne.

        Retourne (steps, raison) :
        - DESCENTE : le coureur qui PART d'une descente avance d'au
          minimum 5 -> raison "minimum 5 (descente)"
        - MONTÉE (règles officielles) :
          * le coureur qui PART d'une montée, ou dont la carte entre
            dans la montée dans ses 5 PREMIÈRES cases : énergie
            plafonnée à 5 (il peut traverser la montée)
            -> "plafonné à 5 (montée)"
          * si la carte entrerait dans la montée à la 6e case ou plus
            ("si un coureur se déplace d'au moins 5 cases avant
            d'entrer dans la montée, il stoppe son mouvement sur la
            dernière file libre avant la montée") : arrêt JUSTE AVANT
            la montée — le déplacement peut alors atteindre 6 ou 7
            cases, toutes sur la plaine -> "arrêt avant la montée"
        La raison est None si la carte s'applique telle quelle.
        """
        steps = card_value
        reason = None
        if self.tile_type_at(x) == TileType.DOWNHILL and steps < 5:
            steps = 5
            reason = "minimum 5 (descente)"
        target = min(x + steps, self.length - 1)
        for d, c in enumerate(range(x, target + 1)):
            if self.tile_type_at(c) != TileType.UPHILL:
                continue
            if d <= 5:
                # entre dans la montée dans les 5 premières cases : plafond 5
                if steps > 5:
                    steps = 5
                    reason = "plafonn\u00e9 \u00e0 5 (mont\u00e9e)"
            else:
                # entrerait à la 6e case ou plus : stoppe juste avant la montée
                steps = min(steps, d - 1)
                reason = "arr\u00eat avant la mont\u00e9e"
            break
        return steps, reason

    def move_runner(self, runner: Runner, steps: int) -> None:
        """
        Déplace un coureur de `steps` cases selon les règles officielles :
        - Il avance exactement `steps` cases et PEUT TRAVERSER les autres
          coureurs ; il ne peut juste pas FINIR son mouvement sur une case
          entièrement occupée.
        - Si la case d'arrivée est pleine, il s'arrête derrière, sur la
          première case offrant une file libre.
        - Case d'arrivée vide -> placé dans la file A (file de droite,
          marquée d'une double ligne) ; sinon il prend la file libre.

        Montagnes (règles officielles, cf. effective_steps) :
        - DESCENTE : minimum 5 en partant d'une descente.
        - MONTÉE : plafonné à 5 si le trajet (départ compris) touche une
          montée — la 6e case ou plus ne peut jamais y pénétrer, le
          coureur s'arrête juste avant (dernière file libre).
        """
        if steps <= 0:
            return

        steps, _reason = self.effective_steps(runner.x, steps)

        target = min(runner.x + steps, self.length - 1)
        x = target
        # Reculer tant que la case est pleine, jusqu'à trouver une file libre
        while x > runner.x and self.get_cell(x, 0).is_full():
            x -= 1
        if x == runner.x:
            return  # bloqué : toutes les cases devant sont pleines

        old_cell = self.get_cell(runner.x, runner.y)
        old_cell.remove_runner(runner.y)

        cell = self.get_cell(x, 0)
        if cell.is_empty(0):
            cell.set_runner(runner, 0)  # file A (droite) en priorité
        else:
            cell.set_runner(runner, 1)  # seule la file B est libre

    def get_groups(self) -> List[List[Runner]]:
        """
        Retourne les groupes de coureurs.
        Un groupe = coureurs dans des cases consécutives (même case ou case suivante).
        """
        all_runners = self.get_all_runners()
        # Trier par position x, puis par file (gauche avant droite pour même x)
        all_runners.sort(key=lambda r: (r[0], r[1]))

        groups = []
        current_group = []

        for x, y, runner in all_runners:
            if not current_group:
                current_group.append(runner)
            else:
                last_runner = current_group[-1]
                # Si le coureur est dans la même case ou la case suivante, il fait partie du groupe
                if x == last_runner.x or x == last_runner.x + 1:
                    current_group.append(runner)
                else:
                    groups.append(current_group)
                    current_group = [runner]

        if current_group:
            groups.append(current_group)
        return groups

    def _packs_from_positions(self, positions: dict) -> List[List[str]]:
        """Groupe des positions {runner_id: (x, lane)} en packs officiels :
        coureurs séparés par aucune case vide (cases consécutives)."""
        items = sorted(positions.items(), key=lambda kv: (kv[1][0], kv[1][1]))
        packs = []
        current = []
        last_x = None
        for rid, (x, _lane) in items:
            if last_x is None or x == last_x or x == last_x + 1:
                current.append(rid)
            else:
                packs.append(current)
                current = [rid]
            last_x = x
        if current:
            packs.append(current)
        return packs

    def compute_slipstream_steps(self) -> List[List[tuple]]:
        """
        Calcule TOUS les mouvements d'aspiration SANS les appliquer.

        Règles officielles :
        - "Pack" = un ou plusieurs coureurs sans case vide entre eux.
        - Si exactement UNE case vide (2 files vides) sépare deux packs,
          le pack arrière avance d'une case et FUSIONNE avec celui de devant.
        - On traite les packs de l'arrière vers l'avant ; un pack fusionné
          est IMMÉDIATEMENT revérifié (il peut aspirer plusieurs fois).
        - Chaque coureur garde sa file (le pack "glisse" d'une case).
        - MONTÉE : un coureur en montée ne donne ni ne reçoit l'aspiration.
          Le "donneur" est le coureur le plus en arrière du pack de devant ;
          dans un pack qui glisse, les coureurs en montée restent sur place
          (ils bloquent ceux derrière eux) et les coureurs hors montée
          partent quand même — le pack peut se séparer (exemple officiel
          Dized). Les descentes ne changent rien.

        Retourne une liste d'étapes : chaque étape est la liste des
        mouvements (runner, from_x, from_lane, to_x, to_lane) d'un pack.
        """
        all_runners = self.get_all_runners()
        pos = {r.id: (x, y) for x, y, r in all_runners}
        runners = {r.id: r for _, _, r in all_runners}

        steps = []
        packs = self._packs_from_positions(pos)
        i = 0
        while i < len(packs):
            if i + 1 >= len(packs):
                break  # pas de pack devant : terminé pour celui-ci
            rear_x = max(pos[rid][0] for rid in packs[i])
            ahead_x = min(pos[rid][0] for rid in packs[i + 1])
            if ahead_x - rear_x != 2:  # pas exactement une case vide
                i += 1
                continue
            # Montée : le donneur (le coureur le plus en arrière du pack de
            # devant) ne peut pas donner l'aspiration depuis une montée.
            giver = min(packs[i + 1], key=lambda r: pos[r][0])
            if self.tile_type_at(pos[giver][0]) == TileType.UPHILL:
                i += 1
                continue
            # Du coureur le plus en avant au plus en arrière : chacun doit
            # libérer sa case avant que celui derrière ne s'y place.
            # Règle officielle (exemple de la page Dized "Ascents") : un
            # coureur en montée ne participe PAS au glissement — il reste
            # sur place et bloque ceux derrière lui ; les coureurs devant
            # lui, hors montée, partent quand même ("left behind, even
            # though he is in the same pack") : le pack peut se séparer.
            step = []
            for rid in sorted(packs[i], key=lambda r: -pos[r][0]):
                if self.tile_type_at(pos[rid][0]) == TileType.UPHILL:
                    break  # reste sur place ; bloque ceux derrière lui
                fx, flane = pos[rid]
                step.append((runners[rid], fx, flane, fx + 1, flane))
                pos[rid] = (fx + 1, flane)
            if not step:
                i += 1  # personne ne peut glisser (tête du pack en montée)
                continue
            steps.append(step)
            # Le segment parti a fusionné avec le pack de devant :
            # recalculer et revérifier immédiatement le pack fusionné
            packs = self._packs_from_positions(pos)
        return steps

    def apply_slipstream_step(self, step: List[tuple]) -> None:
        """Applique une étape d'aspiration calculée par compute_slipstream_steps.

        Les mouvements sont appliqués du coureur le plus en avant au plus
        en arrière : chacun libère sa case avant que celui derrière ne
        s'y place.
        """
        for runner, from_x, from_lane, to_x, to_lane in sorted(step, key=lambda m: -m[1]):
            old_cell = self.get_cell(from_x, from_lane)
            if old_cell:
                old_cell.remove_runner(from_lane)
            new_cell = self.get_cell(to_x, to_lane)
            if new_cell and new_cell.is_empty(to_lane):
                new_cell.set_runner(runner, to_lane)
            else:
                # Ne devrait pas arriver (simulation fidèle) : remettre en place
                if old_cell:
                    old_cell.set_runner(runner, from_lane)

    def apply_aspiration(self) -> List[tuple]:
        """Calcule puis applique toutes les aspirations d'un coup (headless).

        Retourne la liste plate des mouvements (runner, from_x, from_lane, to_x, to_lane).
        """
        movements = []
        for step in self.compute_slipstream_steps():
            self.apply_slipstream_step(step)
            movements.extend(step)
        return movements
