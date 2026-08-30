from src.chemistry.registry import ReactionsRegistry, SpeciesRegistry
from pathlib import Path

def load_reactions(path: str):
    folder_path = Path(path)
    for file_path in folder_path.glob("*.rct"):
        with open(file_path) as f:
            dsl = f.read()
        for line in dsl.splitlines():
            line = "".join(line.split())
            if not line:
                continue
            reactants, product = line.split("->")
            reactants = tuple([SpeciesRegistry.get(x) for x in sorted(reactants.split("+"))])
            product = SpeciesRegistry.get(product)
            if len(reactants) != 2:
                raise ValueError("Cannot have more than 2 reactants")
            ReactionsRegistry.register(reactants=reactants, result=product)