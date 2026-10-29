from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
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
    """Représente une case sur la piste (avec 2 files: gauche/droite)."""
    left: Optional[Runner] = None
    right: Optional[Runner] = None
    x: int = 0  # Position X de la case

    def is_empty(self, lane: int) -> bool:
        """Vérifie si une file est vide (0=gauche, 1=droite)."""
        return (lane == 0 and self.left is None) or (lane == 1 and self.right is None)

    def is_full(self) -> bool:
        """Vérifie si la case est complètement occupée (2 coureurs)."""
        return self.left is not None and self.right is not None

    def get_runner(self, lane: int) -> Optional[Runner]:
        """Retourne le coureur dans une file (ou None)."""
        return self.left if lane == 0 else self.right

    def set_runner(self, runner: Runner, lane: int) -> None:
        """Place un coureur dans une file."""
        if lane == 0:
            self.left = runner
        else:
            self.right = runner
        runner.x, runner.y = self.x, lane  # Met à jour la position du coureur

    def remove_runner(self, lane: int) -> Optional[Runner]:
        """Retire un coureur d'une file."""
        runner = self.get_runner(lane)
        if lane == 0:
            self.left = None
        else:
            self.right = None
        return runner


@dataclass
class Tile:
    """Représente une tuile de piste (composée de 2 cases)."""
    type: TileType
    cells: List[Cell] = field(default_factory=lambda: [Cell(), Cell()])
    x: int = 0  # Position X de la tuile (pour le rendu)

    def __post_init__(self):
        for i, cell in enumerate(self.cells):
            cell.x = self.x * 2 + i  # Chaque tuile = 2 cases


@dataclass
class Track:
    """Représente la piste complète."""
    tiles: List[Tile] = field(default_factory=list)
    length: int = 0  # Nombre total de cases

    def __post_init__(self):
        self.length = len(self.tiles) * 2  # Chaque tuile = 2 cases

    def add_tile(self, tile_type: TileType) -> None:
        """Ajoute une tuile à la piste."""
        x = len(self.tiles)
        tile = Tile(tile_type, x=x)
        self.tiles.append(tile)
        self.length = len(self.tiles) * 2

    def get_cell(self, x: int, lane: int) -> Optional[Cell]:
        """Retourne la case à la position (x, lane)."""
        if x < 0 or x >= self.length:
            return None
        tile_index = x // 2
        cell_index = x % 2
        if tile_index < len(self.tiles):
            return self.tiles[tile_index].cells[cell_index]
        return None

    def is_cell_empty(self, x: int, lane: int) -> bool:
        """Vérifie si une case est vide dans une file."""
        cell = self.get_cell(x, lane)
        return cell is not None and cell.is_empty(lane)

    def move_runner(self, runner: Runner, steps: int) -> None:
        """
        Déplace un coureur de `steps` cases.
        Gère les collisions et les règles de placement.
        """
        new_x = runner.x + steps
        # Limite la position à la piste
        new_x = max(0, min(new_x, self.length - 1))

        # On avance case par case pour gérer les collisions
        current_x = runner.x
        current_y = runner.y

        # Retirer le coureur de sa position actuelle
        current_cell = self.get_cell(current_x, current_y)
        if current_cell:
            current_cell.remove_runner(current_y)

        for x in range(current_x + 1, new_x + 1):
            if x >= self.length:
                break

            cell = self.get_cell(x, current_y)
            if cell is None:
                break

            if cell.is_full():
                # Case pleine : on s'arrête avant
                prev_cell = self.get_cell(x - 1, current_y)
                if prev_cell:
                    prev_cell.set_runner(runner, current_y)
                return
            elif not cell.is_empty(current_y):
                # La file actuelle est occupée : on essaie l'autre file
                other_lane = 1 - current_y
                if cell.is_empty(other_lane):
                    current_y = other_lane
                else:
                    # Les 2 files sont occupées : on s'arrête
                    prev_cell = self.get_cell(x - 1, current_y)
                    if prev_cell:
                        prev_cell.set_runner(runner, current_y)
                    return

        # Si on a atteint la fin sans collision
        final_cell = self.get_cell(new_x, current_y)
        if final_cell and not final_cell.is_full():
            final_cell.set_runner(runner, current_y)
        else:
            # Si la case est pleine, on recule
            prev_cell = self.get_cell(new_x - 1, current_y)
            if prev_cell:
                prev_cell.set_runner(runner, current_y)

    def get_runners_in_cell(self, x: int) -> List[Runner]:
        """Retourne tous les coureurs dans une case (les 2 files)."""
        cell = self.get_cell(x, 0)
        if cell is None:
            return []
        runners = []
        if cell.left:
            runners.append(cell.left)
        if cell.right:
            runners.append(cell.right)
        return runners

    def get_groups(self) -> List[List[Runner]]:
        """
        Retourne les groupes de coureurs (collés sans case vide entre eux).
        Un groupe = 1 ou plusieurs coureurs avec 0 case vide entre eux.
        """
        groups = []
        current_group = []

        # Parcourir toutes les cases de la piste
        for x in range(self.length):
            runners = self.get_runners_in_cell(x)
            if runners:
                current_group.extend(runners)
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
        # Ajouter le dernier groupe si la piste se termine par des coureurs
        if current_group:
            groups.append(current_group)

        return groups

    def apply_aspiration(self) -> List:
        """
        Applique la règle d'aspiration :
        Si 1 case vide sépare 2 groupes, le groupe derrière avance de 1 case.
        Retourne la liste des mouvements effectués (runner, old_x, new_x).
        """
        movements = []
        groups = self.get_groups()
        if len(groups) < 2:
            return movements  # Pas d'aspiration possible

        # Parcourir les groupes de l'arrière vers l'avant
        for i in range(len(groups) - 1, 0, -1):
            group_behind = groups[i]
            group_ahead = groups[i - 1]

            # Trouver la position du groupe devant et derrière
            x_ahead = min(runner.x for runner in group_ahead)
            x_behind = max(runner.x for runner in group_behind)  # Position la plus avancée du groupe derrière

            # Vérifier s'il y a exactement 1 case vide entre les groupes
            if x_ahead - x_behind == 2:
                # Avancer le groupe derrière de 1 case
                for runner in group_behind:
                    if runner.x == x_behind:  # Seuls les coureurs à la position x_behind bougent
                        # Sauvegarder la position actuelle
                        old_x, old_y = runner.x, runner.y
                        # Retirer le coureur de sa position actuelle
                        old_cell = self.get_cell(old_x, old_y)
                        if old_cell:
                            old_cell.remove_runner(old_y)
                        # Déplacer le coureur
                        new_x = runner.x + 1
                        runner.x = new_x
                        new_cell = self.get_cell(new_x, old_y)
                        if new_cell:
                            new_cell.set_runner(runner, old_y)
                        
                        movements.append((runner, old_x, new_x))

                # Recalculer les groupes (car l'ordre a changé)
                groups = self.get_groups()
        
        return movements
