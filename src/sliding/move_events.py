from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.chemistry.species import ChemicalSpecies
@dataclass
class MoveEvent:
    from_pos: tuple[int, int]  # (col, row)
    to_pos: tuple[int, int]    # (col, row)
    species: "ChemicalSpecies"
    merged: bool = False
    
@dataclass
class LineMoveEvent:
    from_idx: int
    to_idx: int
    species: "ChemicalSpecies"
    merged: bool = False