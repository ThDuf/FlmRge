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
        Gère les collisions : si une case est occupée, on s'arrête avant.
        """
        if steps <= 0:
            return

        new_x = runner.x
        current_y = runner.y

        # Retirer le coureur de sa position actuelle
        old_cell = self.get_cell(runner.x, current_y)
        if old_cell:
            old_cell.remove_runner(current_y)

        # Avancer case par case
        for step in range(steps):
            new_x += 1
            if new_x >= self.length:
                new_x = self.length - 1
                break

            new_cell = self.get_cell(new_x, current_y)
            if new_cell is None:
                break

            # Si la case est libre dans la file actuelle, on y va
            if new_cell.is_empty(current_y):
                continue
            # Sinon, essayer l'autre file
            else:
                other_y = 1 - current_y
                if new_cell.is_empty(other_y):
                    current_y = other_y
                    continue
                # Si les deux files sont occupées, on s'arrête
                else:
                    new_x -= 1
                    break

        # Placer le coureur à sa nouvelle position
        runner.x = new_x
        runner.y = current_y
        final_cell = self.get_cell(new_x, current_y)
        if final_cell:
            final_cell.set_runner(runner, current_y)

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
        Un groupe = coureurs consécutifs dans les mêmes cases ou cases adjacentes.
        """
        # Collecter tous les coureurs avec leur position
        all_runners = []
        for x in range(self.length):
            cell = self.get_cell(x, 0)
            if cell and cell.left:
                all_runners.append((x, 0, cell.left))
            if cell and cell.right:
                all_runners.append((x, 1, cell.right))

        # Trier par position x, puis par file
        all_runners.sort(key=lambda r: (r[0], r[1]))

        groups = []
        current_group = []

        for x, y, runner in all_runners:
            if not current_group:
                current_group.append(runner)
            else:
                # Vérifier si ce coureur est adjacent au dernier du groupe
                last_runner = current_group[-1]
                last_x = last_runner.x
                last_y = last_runner.y

                # Même case ou case suivante adjacente
                if x == last_x or (x == last_x + 1 and abs(y - last_y) <= 1):
                    current_group.append(runner)
                else:
                    # Vérifier s'il y a une case vide entre les groupes
                    if x > last_x + 1:
                        groups.append(current_group)
                        current_group = [runner]
                    else:
                        current_group.append(runner)

        if current_group:
            groups.append(current_group)

        return groups

    def apply_aspiration(self) -> List:
        """
        Applique la règle d'aspiration :
        Si exactement 1 case vide sépare 2 groupes, le groupe derrière avance de 1 case.
        Retourne la liste des mouvements effectués (runner, old_x, new_x).
        """
        movements = []
        
        # Continuer jusqu'à ce qu'aucun mouvement ne soit plus possible
        while True:
            groups = self.get_groups()
            if len(groups) < 2:
                break
            
            moved = False
            
            # Parcourir les groupes de l'arrière vers l'avant
            for i in range(len(groups) - 1, 0, -1):
                group_behind = groups[i]
                group_ahead = groups[i - 1]

                # Position du groupe devant (la plus proche de l'arrivée)
                x_ahead = min(runner.x for runner in group_ahead)
                # Position du groupe derrière (la plus éloignée de l'arrivée)
                x_behind = max(runner.x for runner in group_behind)

                # Vérifier s'il y a exactement 1 case vide entre les groupes
                if x_ahead - x_behind == 2:
                    # Déplacer TOUS les coureurs du groupe derrière de 1 case
                    for runner in group_behind:
                        old_x = runner.x
                        old_y = runner.y

                        # Retirer le coureur
                        old_cell = self.get_cell(old_x, old_y)
                        if old_cell:
                            old_cell.remove_runner(old_y)

                        # Avancer de 1 case
                        new_x = old_x + 1
                        runner.x = new_x

                        # Placer dans la même file si possible, sinon l'autre file
                        new_cell = self.get_cell(new_x, old_y)
                        if new_cell and new_cell.is_empty(old_y):
                            new_cell.set_runner(runner, old_y)
                        else:
                            # Essayer l'autre file
                            new_y = 1 - old_y
                            if new_cell and new_cell.is_empty(new_y):
                                runner.y = new_y
                                new_cell.set_runner(runner, new_y)
                            else:
                                # Remettre à l'ancienne position
                                runner.x = old_x
                                if old_cell:
                                    old_cell.set_runner(runner, old_y)
                                continue

                        movements.append((runner, old_x, new_x))
                        moved = True

                    # Recalculer les groupes après ce mouvement
                    break
            
            if not moved:
                break

        return movements
