import tomllib
from pathlib import Path
from src.chemistry.registry import SpeciesRegistry
from src.chemistry.species import Intermediate, ReactiveSpecies, FinishedCompound, Category


def load_species(path: str):
    folder_path = Path(path)
    for file_path in folder_path.glob("*.toml"):
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        reactive_defaults = data.get("defaults", {}).get("reactive", {})
        compound_defaults = data.get("defaults", {}).get("compound", {})
        intermediate_defaults = data.get("defaults", {}).get("intermediate", {})

        for species in data.get("reactive", []):
            values = reactive_defaults | species
            values["category"] = Category[values["category"]]
            if values.get("open_dots", None) is None:
                values["open_dots"] = (values["charge"] + 8) % 8
            SpeciesRegistry.register(ReactiveSpecies(**values))

        for species in data.get("compound", []):
            values = compound_defaults | species
            values["category"] = Category[values["category"]]
            SpeciesRegistry.register(FinishedCompound(**values))
            
        for species in data.get("intermediate", []):
            values = intermediate_defaults | species
            values["category"] = Category[values["category"]]
            if values.get("open_dots", None) is None:
                values["open_dots"] = (values["charge"] + 8) % 8
            SpeciesRegistry.register(Intermediate(**values))