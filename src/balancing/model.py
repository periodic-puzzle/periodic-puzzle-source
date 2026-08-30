import random
from dataclasses import dataclass
from src.chemistry.utils.utils import parse_formula


@dataclass
class ChemicalTerm:
    formula: str
    user_coefficient: int = 1

    @property
    def atom_counts(self) -> dict[str, int]:
        base_atoms = parse_formula(self.formula)
        return {atom: count * self.user_coefficient for atom, count in base_atoms.items()}


@dataclass
class Equation:
    reactants: list[ChemicalTerm]
    products: list[ChemicalTerm]
    points: int = 100

    def is_balanced(self) -> bool:
        left_counts: dict[str, int] = {}
        right_counts: dict[str, int] = {}

        for term in self.reactants:
            for atom, count in term.atom_counts.items():
                left_counts[atom] = left_counts.get(atom, 0) + count

        for term in self.products:
            for atom, count in term.atom_counts.items():
                right_counts[atom] = right_counts.get(atom, 0) + count

        return left_counts == right_counts


SAMPLE_EQUATIONS = [
    # Easy (Base: 100 pts)
    {"reactants": ["H2", "O2"], "products": ["H2O"], "difficulty": "easy", "points": 100},
    {"reactants": ["Na", "Cl2"], "products": ["NaCl"], "difficulty": "easy", "points": 100},
    {"reactants": ["N2", "H2"], "products": ["NH3"], "difficulty": "easy", "points": 100},
    {"reactants": ["Mg", "O2"], "products": ["MgO"], "difficulty": "easy", "points": 100},
    {"reactants": ["H2", "Cl2"], "products": ["HCl"], "difficulty": "easy", "points": 100},
    {"reactants": ["Fe", "O2"], "products": ["Fe2O3"], "difficulty": "easy", "points": 100},
    {"reactants": ["Al", "O2"], "products": ["Al2O3"], "difficulty": "easy", "points": 100},
    {"reactants": ["K", "Br2"], "products": ["KBr"], "difficulty": "easy", "points": 100},

    # Medium (Base: 250 pts)
    {"reactants": ["CH4", "O2"], "products": ["CO2", "H2O"], "difficulty": "medium", "points": 250},
    {"reactants": ["KClO3"], "products": ["KCl", "O2"], "difficulty": "medium", "points": 250},
    {"reactants": ["Zn", "HCl"], "products": ["ZnCl2", "H2"], "difficulty": "medium", "points": 250},
    {"reactants": ["CaCO3"], "products": ["CaO", "CO2"], "difficulty": "medium", "points": 250},
    {"reactants": ["Na", "H2O"], "products": ["NaOH", "H2"], "difficulty": "medium", "points": 250},
    {"reactants": ["P4", "O2"], "products": ["P4O10"], "difficulty": "medium", "points": 250},
    {"reactants": ["Fe2O3", "CO"], "products": ["Fe", "CO2"], "difficulty": "medium", "points": 250},

    # Hard (Base: 500 pts)
    {"reactants": ["C3H8", "O2"], "products": ["CO2", "H2O"], "difficulty": "hard", "points": 500},
    {"reactants": ["C2H6", "O2"], "products": ["CO2", "H2O"], "difficulty": "hard", "points": 500},
    {"reactants": ["AgNO3", "Cu"], "products": ["Cu(NO3)2", "Ag"], "difficulty": "hard", "points": 500},
    {"reactants": ["HCl", "NaOH"], "products": ["NaCl", "H2O"], "difficulty": "hard", "points": 500},
    {"reactants": ["Al", "HCl"], "products": ["AlCl3", "H2"], "difficulty": "hard", "points": 500},
]

def get_dynamic_equation(current_score: int, previous_eq: dict | None = None) -> dict:
    """Calculates weights and ensures the returned equation isn't identical to the previous one."""
    if current_score < 300:
        tier_weights = {"easy": 8.0, "medium": 1.5, "hard": 0.5}
    elif current_score < 800:
        tier_weights = {"easy": 2.0, "medium": 6.0, "hard": 2.0}
    else:
        tier_weights = {"easy": 0.5, "medium": 3.0, "hard": 6.5}

    weights = [tier_weights[eq["difficulty"]] for eq in SAMPLE_EQUATIONS]

    # If we have more than 1 total equation, filter/re-roll until it's different
    if len(SAMPLE_EQUATIONS) > 1 and previous_eq is not None:
        while True:
            chosen = random.choices(SAMPLE_EQUATIONS, weights=weights, k=1)[0]
            if chosen != previous_eq:
                return chosen

    return random.choices(SAMPLE_EQUATIONS, weights=weights, k=1)[0]