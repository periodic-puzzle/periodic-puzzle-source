from typing import Final
from src.chemistry.species import ChemicalSpecies

SpeciesId = str
"""Id of a Chemical Species"""

class SpeciesRegistry:
    _species: Final[dict[str, ChemicalSpecies]] = {}

    @classmethod
    def register(cls, species: ChemicalSpecies) -> None:
        if species.id in cls._species:
            raise ValueError(f"{species.id} already registered.")

        cls._species[species.id] = species

    @classmethod
    def get(cls, id: SpeciesId) -> ChemicalSpecies:
        return cls._species[id]
    
    @classmethod
    def has(cls, id: SpeciesId) -> bool:
        return id in cls._species

    @classmethod
    def all(cls) -> list[ChemicalSpecies]:
        return list(cls._species.values())
    
Reactants = tuple[SpeciesId, SpeciesId]
ReactionType = dict[Reactants, ChemicalSpecies]

def _species_tuple_to_id(tuple: tuple[ChemicalSpecies, ChemicalSpecies]) -> tuple[SpeciesId, SpeciesId]:
    return (tuple[0].id, tuple[1].id)

class ReactionsRegistry:
    _reactions: Final[ReactionType] = {}
        

    @classmethod
    def register(cls, reactants: tuple[ChemicalSpecies, ChemicalSpecies], result: ChemicalSpecies) -> None:
        for reactant in reactants:
            if reactant not in SpeciesRegistry.all():
                raise ValueError(f"{reactant.id} not registered")
        id_list = sorted((reactants[0].id, reactants[1].id))
        reaction_tuple = (SpeciesRegistry.get(id_list[0]), SpeciesRegistry.get(id_list[1]))
        cls._reactions[_species_tuple_to_id(reaction_tuple)] = result

    @classmethod
    def get(cls, reactants: tuple[ChemicalSpecies, ChemicalSpecies]) -> ChemicalSpecies:
        return cls._reactions[_species_tuple_to_id(reactants)]
    
    @classmethod
    def has(cls, reactants: tuple[ChemicalSpecies, ChemicalSpecies]) -> bool:
        return _species_tuple_to_id(reactants) in cls._reactions
    
    @classmethod
    def all(cls) -> list[ChemicalSpecies]:
        return list(cls._reactions.values())