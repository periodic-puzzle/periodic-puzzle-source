from dataclasses import dataclass
from enum import Enum, auto
from src.chemistry.utils.utils import parse_formula


class Category(Enum):
    ALKALI_METAL = auto()
    ALKALINE_EARTH_METAL = auto()
    TRANSITION_METAL = auto()
    POST_TRANSITION_METAL = auto()
    METALLOID = auto()
    CARBON_GROUP = auto()
    PNICTOGEN = auto() # or nitrogen group
    CHALCOGEN = auto() # or oxygen group
    HALOGEN = auto()
    NOBLE_GAS = auto()
    LANTHANIDE = auto()
    ACTINIDE = auto()
    NEUTRAL_COMPOUND = auto()
    SALT = auto()
    POLYATOMIC_ANION = auto()
    POLYATOMIC_CATION = auto()
    INTERMEDIATE = auto()
    BASE = auto()
    ACID = auto()
    HYDROCARBON = auto()
    HYDROGEN = auto()
    OXOACID = auto()
    ORGANIC_RADICAL = auto()
    PEROXIDE = auto()
    HYDRIDE = auto()
    ACID_ANHYDRIDE = auto()
    ALCOHOL = auto()
    ALDEHYDE = auto()
    
@dataclass(slots=True, frozen=True)
class Species:
    id: str
    formula: str
    name: str
    tier: int
    category: Category
    
    @property
    def atoms(self):
        return parse_formula(self.formula)


@dataclass(slots=True, frozen=True)
class ReactiveSpecies(Species):
    charge: int
    oxidation_states: tuple[int, ...]
    can_spawn: bool
    spawn_weight: float
    can_keep: bool = True
    unlock_tier: int = 1
    open_dots: int = 0


@dataclass(slots=True, frozen=True)
class Intermediate(Species):
    charge: int | None
    can_spawn: bool = False
    can_keep: bool = True
    open_dots: int = 0


@dataclass(slots=True, frozen=True)
class FinishedCompound(Species):
    coefficients: list[int]
    charge: int = 0
    points: int = 0
    can_spawn: bool = False
    can_keep: bool = False
    open_dots: int = 8

ChemicalSpecies = ReactiveSpecies | Intermediate | FinishedCompound