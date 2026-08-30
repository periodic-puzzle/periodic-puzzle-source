import random
from dataclasses import dataclass
from src.chemistry.utils.utils import parse_formula

# Standard Atomic Weights (rounded to 1-2 decimal places for puzzle gameplay)
ATOMIC_WEIGHTS = {
    "H": 1.01,
    "He": 4.00,
    "Li": 6.94,
    "C": 12.01,
    "N": 14.01,
    "O": 16.00,
    "Na": 22.99,
    "Mg": 24.31,
    "Al": 26.98,
    "P": 30.97,
    "S": 32.06,
    "Cl": 35.45,
    "K": 39.10,
    "Ca": 40.08,
    "Fe": 55.85,
    "Cu": 63.55,
    "Zn": 65.38,
    "Ag": 107.87,
}

FORMULA_POOL = [
    "H2O", "CO2", "NaCl", "CH4", "O2", 
    "NH3", "HCl", "MgO", "CaCl2", "H2SO4", 
    "KNO3", "CaCO3", "NaOH", "Fe2O3"
]


@dataclass
class MolarMassQuestion:
    formula: str
    correct_mass: float
    options: list[float]


def calculate_molar_mass(formula: str) -> float:
    """Calculates molar mass using atom counts from parse_formula."""
    atoms = parse_formula(formula)
    total_mass = sum(ATOMIC_WEIGHTS.get(atom, 0.0) * count for atom, count in atoms.items())
    return round(total_mass, 2)


def get_random_molar_question(previous_formula: str | None = None) -> MolarMassQuestion:
    """Generates a question with 1 correct answer and 3 realistic distractors."""
    candidates = [f for f in FORMULA_POOL if f != previous_formula] if previous_formula else FORMULA_POOL
    formula = random.choice(candidates)
    
    correct_mass = calculate_molar_mass(formula)
    
    # Generate realistic distractors (e.g., forgot a subscript multiplier or misread an atomic mass)
    distractors = set()
    while len(distractors) < 3:
        # Offsets relative to the real mass
        offset = random.choice([-16.0, -2.0, 1.0, 2.0, 16.0, round(random.uniform(-10, 10), 2)])
        fake_mass = round(correct_mass + offset, 2)
        if fake_mass > 0 and fake_mass != correct_mass:
            distractors.add(fake_mass)

    options = list(distractors) + [correct_mass]
    random.shuffle(options)

    return MolarMassQuestion(
        formula=formula,
        correct_mass=correct_mass,
        options=options
    )