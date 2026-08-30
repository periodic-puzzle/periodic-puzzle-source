from math import gcd
from collections import defaultdict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.chemistry.registry import ChemicalSpecies

SUBSCRIPTS = "₀₁₂₃₄₅₆₇₈₉"
SUBSCRIPT_MAP = str.maketrans(SUBSCRIPTS, "0123456789")


def parse_formula(formula: str) -> dict[str, int]:
    formula = formula.translate(SUBSCRIPT_MAP)

    def parse_segment(index: int):
        atoms = defaultdict(int)

        while index < len(formula):
            char = formula[index]

            # End of a parenthesis group
            if char == ")":
                return atoms, index + 1

            # Start of a group
            if char == "(":
                inner, index = parse_segment(index + 1)

                # Read multiplier after )
                multiplier = 1
                digits = ""

                while index < len(formula) and formula[index].isdigit():
                    digits += formula[index]
                    index += 1

                if digits:
                    multiplier = int(digits)

                for element, count in inner.items():
                    atoms[element] += count * multiplier

                continue

            # Element symbol
            if char.isupper():
                element = char
                index += 1

                # Add lowercase letters (Na, Cl, Mg...)
                while index < len(formula) and formula[index].islower():
                    element += formula[index]
                    index += 1

                # Read subscript
                digits = ""

                while index < len(formula) and formula[index].isdigit():
                    digits += formula[index]
                    index += 1

                count = int(digits) if digits else 1

                atoms[element] += count
                continue

            raise ValueError(f"Invalid character {char}")

        return atoms, index

    atoms, _ = parse_segment(0)
    return dict(atoms)