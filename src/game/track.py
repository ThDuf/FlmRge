from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum, auto
from .runner import Runner


class Lane(Enum):
    A = 0  # File A (prioritaire)
    B = 1  # File B


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

    def __post_init__(self):
        for i, cell in enumerate(self.cells):
            cell.x = self.x * 2 + i


@dataclass
class Track:
    """Représente la piste complète."""
    tiles: List[Tile] = field(default_factory=list)
    length: int = 0

    def __post_init__(self):
        self.length = len(self.tiles) * 2

    def add_tile(self, tile_type: TileType) -> None:
        x = len(self.tiles)
        tile = Tile(tile_type, x=x)
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

    def is_cell_empty(self, x: int, lane: int) -> bool:
        cell = self.get_cell(x, lane)
        return cell is not None and cell.is_empty(lane)

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

    def move_runner(self, runner: Runner, steps: int) -> None:
        """
        Déplace un coureur de `steps` cases.
        - Avance case par case
        - Priorité à la file A (lane 0) si la file actuelle est bloquée
        - Si les 2 files sont occupées, s'arrête
        """
        if steps <= 0:
            return

        old_x = runner.x
        old_y = runner.y
        old_cell = self.get_cell(old_x, old_y)
        if old_cell:
            old_cell.remove_runner(old_y)

        for _ in range(steps):
            new_x = runner.x + 1
            if new_x >= self.length:
                new_x = self.length - 1
                break

            new_cell = self.get_cell(new_x, runner.y)
            if new_cell is None:
                break

            if new_cell.is_empty(runner.y):
                runner.x = new_x
                continue
            else:
                # Priorité à la file A (lane 0) selon les règles
                other_y = 0  # Toujours essayer la file A en premier
                if runner.y == 0:
                    other_y = 1  # Si déjà en A, essayer B
                
                if new_cell.is_empty(other_y):
                    runner.y = other_y
                    runner.x = new_x
                    continue
                else:
                    break

        final_cell = self.get_cell(runner.x, runner.y)
        if final_cell:
            final_cell.set_runner(runner, runner.y)

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

    def apply_aspiration(self) -> List:
        """
        Applique la règle d'aspiration :
        "Si exactement une case vide sépare deux groupes, le groupe derrière avance d'une case."
        
        Retourne la liste des mouvements effectués (runner, old_x, new_x).
        """
        movements = []
        
        while True:
            groups = self.get_groups()
            if len(groups) < 2:
                break
            
            moved = False
            
            # Parcourir les groupes de l'arrière vers l'avant
            # groups[0] = coureurs les plus en arrière (positions les plus basses)
            # groups[-1] = coureurs les plus en avant (positions les plus hautes)
            for i in range(len(groups) - 1):
                group_behind = groups[i]
                group_ahead = groups[i + 1]

                # Position la plus avancée du groupe derrière
                x_behind = max(runner.x for runner in group_behind)
                # Position la moins avancée du groupe devant
                x_ahead = min(runner.x for runner in group_ahead)

                # Vérifier s'il y a EXACTEMENT 1 case vide entre les groupes
                if x_ahead - x_behind == 2:
                    print(f"DEBUG: Aspiration détectée - groupe arrière à {x_behind}, groupe avant à {x_ahead}")
                    
                    # Déplacer TOUS les coureurs du groupe derrière de 1 case
                    # Priorité à la file A (lane 0) pour le déplacement
                    for runner in sorted(group_behind, key=lambda r: (r.x, r.y)):
                        old_x = runner.x
                        old_y = runner.y
                        
                        # Retirer le coureur
                        old_cell = self.get_cell(old_x, old_y)
                        if old_cell:
                            old_cell.remove_runner(old_y)
                        
                        # Avancer de 1 case
                        new_x = old_x + 1
                        
                        # Priorité à la file A (lane 0)
                        preferred_y = 0
                        if old_y == 0:
                            preferred_y = 1
                        
                        new_cell = self.get_cell(new_x, preferred_y)
                        if new_cell and new_cell.is_empty(preferred_y):
                            new_cell.set_runner(runner, preferred_y)
                            runner.x = new_x
                            runner.y = preferred_y
                        else:
                            # Essayer l'autre file
                            other_y = 1 - preferred_y
                            if new_cell and new_cell.is_empty(other_y):
                                new_cell.set_runner(runner, other_y)
                                runner.x = new_x
                                runner.y = other_y
                            else:
                                # Remettre à l'ancienne position
                                runner.x = old_x
                                runner.y = old_y
                                if old_cell:
                                    old_cell.set_runner(runner, old_y)
                                continue
                        
                        movements.append((runner, old_x, new_x))
                        moved = True
                        print(f"DEBUG: {runner.id} déplacé de {old_x} à {new_x}, lane {old_y}->{runner.y}")

                    # Recalculer les groupes après ce mouvement
                    break
            
            if not moved:
                break

        print(f"DEBUG: Aspiration terminée - {len(movements)} mouvements")
        return movements
