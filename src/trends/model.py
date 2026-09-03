import random
from dataclasses import dataclass

@dataclass
class ElementData:
    symbol: str
    name: str
    atomic_number: int
    group: int
    period: int
    atomic_radius_pm: int       # Picometers
    electronegativity: float    # Pauling scale
    category: str               # "Metal", "Non-Metal", "Metalloid"


# Sample Element Database
ELEMENT_DB = [
    ElementData("H", "Hydrogen", 1, 1, 1, 53, 2.20, "Non-Metal"),
    ElementData("He", "Helium", 2, 18, 1, 31, 0.0, "Non-Metal"),
    ElementData("Li", "Lithium", 3, 1, 2, 167, 0.98, "Metal"),
    ElementData("Be", "Beryllium", 4, 2, 2, 112, 1.57, "Metal"),
    ElementData("B", "Boron", 5, 13, 2, 87, 2.04, "Metalloid"),
    ElementData("C", "Carbon", 6, 14, 2, 67, 2.55, "Non-Metal"),
    ElementData("N", "Nitrogen", 7, 15, 2, 56, 3.04, "Non-Metal"),
    ElementData("O", "Oxygen", 8, 16, 2, 48, 3.44, "Non-Metal"),
    ElementData("F", "Fluorine", 9, 17, 2, 42, 3.98, "Non-Metal"),
    ElementData("Na", "Sodium", 11, 1, 3, 190, 0.93, "Metal"),
    ElementData("Mg", "Magnesium", 12, 2, 3, 145, 1.31, "Metal"),
    ElementData("Al", "Aluminum", 13, 13, 3, 118, 1.61, "Metal"),
    ElementData("Si", "Silicon", 14, 14, 3, 111, 1.90, "Metalloid"),
    ElementData("Cl", "Chlorine", 17, 17, 3, 79, 3.16, "Non-Metal"),
    ElementData("K", "Potassium", 19, 1, 4, 243, 0.82, "Metal"),
    ElementData("Ca", "Calcium", 20, 2, 4, 194, 1.00, "Metal"),
    ElementData("Fr", "Francium", 87, 1, 7, 298, 0.70, "Metal"),
    ElementData("Y", "Yttrium", 39, 3, 5, 180, 1.22, "Metal"),
]


@dataclass
class SortingChallenge:
    mode: str  # "category" or "trend"
    prompt: str
    elements: list[ElementData]
    target_trend: str | None = None  # "atomic_radius" or "electronegativity"


def get_random_challenge() -> SortingChallenge:
    """Generates a random sorting prompt for the conveyor belt."""
    modes = ["category", "atomic_radius", "electronegativity"]
    chosen_mode = random.choice(modes)

    if chosen_mode == "category":
        sample = random.sample(ELEMENT_DB, 1)[0]
        return SortingChallenge(
            mode="category",
            prompt=f"Classify {sample.name} ({sample.symbol})",
            elements=[sample],
        )
    elif chosen_mode == "atomic_radius":
        sample = random.sample(ELEMENT_DB, 3)
        return SortingChallenge(
            mode="trend",
            prompt="Sort by INCREASING Atomic Radius (Smallest -> Largest)",
            elements=sample,
            target_trend="atomic_radius_pm",
        )
    else:
        sample = random.sample(ELEMENT_DB, 3)
        return SortingChallenge(
            mode="trend",
            prompt="Sort by INCREASING Electronegativity (Lowest -> Highest)",
            elements=sample,
            target_trend="electronegativity",
        )