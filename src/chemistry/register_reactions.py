from src.chemistry.loaders.reaction import load_reactions
from src.constants.constants import ASSETS

def register_reactions():
    load_reactions(str(ASSETS / "chem" / "reactions"))

"""def register_reactions():
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("Cl")),
        SpeciesRegistry.get("NaCl")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Cl"), SpeciesRegistry.get("Cl")),
        SpeciesRegistry.get("Cl2")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("NaO")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("NaO"), SpeciesRegistry.get("Cl")),
        SpeciesRegistry.get("NaClO")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("ClO")),
        SpeciesRegistry.get("NaClO")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("NaO"), SpeciesRegistry.get("Na")),
        SpeciesRegistry.get("Na2O")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("ClO2")),
        SpeciesRegistry.get("NaClO2")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("ClO3")),
        SpeciesRegistry.get("NaClO3")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Na"), SpeciesRegistry.get("ClO4")),
        SpeciesRegistry.get("NaClO4")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("O"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("O2")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("Cl"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("ClO")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("ClO"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("ClO2")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("ClO2"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("ClO3")
    )
    ReactionsRegistry.register(
        (SpeciesRegistry.get("ClO3"), SpeciesRegistry.get("O")),
        SpeciesRegistry.get("ClO4")
    )"""