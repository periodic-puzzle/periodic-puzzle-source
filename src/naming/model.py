import random
from dataclasses import dataclass


@dataclass
class Compound:
    formula: str
    name: str
    options: list[str]  # 4 choices for multiple choice


# src/naming/model.py

COMPOUND_POOL = [
    # --- Binary Ionic Compounds ---
    Compound("NaCl", "Sodium chloride", ["Sodium chloride", "Sodium chlorite", "Sodium monochloride", "Natrium chloride"]),
    Compound("MgO", "Magnesium oxide", ["Magnesium oxide", "Magnesium monoxide", "Magnesium oxygen", "Manganous oxide"]),
    Compound("CaCl2", "Calcium chloride", ["Calcium chloride", "Calcium dichloride", "Monocalcium chloride", "Calcium chlorite"]),
    Compound("KBr", "Potassium bromide", ["Potassium bromide", "Potassium monobromide", "Potassium bromate", "Potassium bromine"]),
    Compound("Li2O", "Lithium oxide", ["Lithium oxide", "Dilithium oxide", "Lithium monoxide", "Lithium dioxide"]),
    Compound("Al2O3", "Aluminum oxide", ["Aluminum oxide", "Dialuminum trioxide", "Aluminum trioxide", "Aluminum hydroxide"]),
    Compound("Na2S", "Sodium sulfide", ["Sodium sulfide", "Sodium sulfite", "Sodium sulfate", "Disodium sulfide"]),
    Compound("Mg3N2", "Magnesium nitride", ["Magnesium nitride", "Trimagnesium dinitride", "Magnesium nitrate", "Magnesium nitrite"]),

    # --- Polyatomic & Transition Metal Compounds ---
    Compound("Fe2O3", "Iron(III) oxide", ["Iron(III) oxide", "Iron(II) oxide", "Diiron trioxide", "Iron oxide"]),
    Compound("FeO", "Iron(II) oxide", ["Iron(II) oxide", "Iron(III) oxide", "Iron monoxide", "Ferric oxide"]),
    Compound("CuSO4", "Copper(II) sulfate", ["Copper(II) sulfate", "Copper(I) sulfate", "Copper sulfite", "Copper sulfide"]),
    Compound("KNO3", "Potassium nitrate", ["Potassium nitrate", "Potassium nitrite", "Potassium mononitrate", "Potassium nitrogen oxide"]),
    Compound("CaCO3", "Calcium carbonate", ["Calcium carbonate", "Calcium carbonite", "Calcium oxide", "Calcium carbide"]),
    Compound("NaHCO3", "Sodium bicarbonate", ["Sodium bicarbonate", "Sodium carbonate", "Sodium hydride", "Sodium hydroxide"]),
    Compound("NaOH", "Sodium hydroxide", ["Sodium hydroxide", "Sodium oxide", "Sodium hydride", "Sodium monoxide"]),
    Compound("NH4Cl", "Ammonium chloride", ["Ammonium chloride", "Ammonia chloride", "Ammonium chlorate", "Nitrogen hydrogen chloride"]),
    Compound("AgNO3", "Silver nitrate", ["Silver nitrate", "Silver nitrite", "Silver mononitrate", "Silver nitrogen oxide"]),
    Compound("ZnSO4", "Zinc sulfate", ["Zinc sulfate", "Zinc sulfite", "Zinc sulfide", "Zinc oxide"]),

    # --- Covalent Compounds ---
    Compound("CO2", "Carbon dioxide", ["Carbon dioxide", "Carbon monoxide", "Monocarbon dioxide", "Carbon oxide"]),
    Compound("CO", "Carbon monoxide", ["Carbon monoxide", "Carbon dioxide", "Monocarbon oxide", "Carbon oxide"]),
    Compound("N2O4", "Dinitrogen tetroxide", ["Dinitrogen tetroxide", "Nitrogen oxide", "Dinitrogen oxide", "Nitrogen tetroxide"]),
    Compound("H2O", "Dihydrogen monoxide", ["Dihydrogen monoxide", "Hydrogen monoxide", "Dihydrogen oxide", "Hydrogen oxide"]),
    Compound("SF6", "Sulfur hexafluoride", ["Sulfur hexafluoride", "Monosulfur hexafluoride", "Sulfur fluoride", "Sulfur pentafluoride"]),
    Compound("PCl5", "Phosphorus pentachloride", ["Phosphorus pentachloride", "Phosphorus chloride", "Monophosphorus pentachloride", "Phosphorus trichloride"]),
    Compound("SO3", "Sulfur trioxide", ["Sulfur trioxide", "Sulfur dioxide", "Monosulfur trioxide", "Sulfur oxide"]),
    Compound("NH3", "Ammonia", ["Ammonia", "Nitrogen trihydride", "Ammonium", "Nitrogen hydride"]),

    # --- Acids ---
    Compound("HCl", "Hydrochloric acid", ["Hydrochloric acid", "Hydrogen chloride", "Chloric acid", "Hydrogen monochloride"]),
    Compound("H2SO4", "Sulfuric acid", ["Sulfuric acid", "Sulfurous acid", "Hydrosulfuric acid", "Hydrogen sulfate"]),
    Compound("HNO3", "Nitric acid", ["Nitric acid", "Nitrous acid", "Hydronitric acid", "Hydrogen nitrate"]),
    Compound("CH3COOH", "Acetic acid", ["Acetic acid", "Ethanoic acid", "Carbonic acid", "Formic acid"]),
]


def get_random_compound() -> Compound:
    compound = random.choice(COMPOUND_POOL)
    # Shuffle options so the correct answer isn't always first
    random.shuffle(compound.options)
    return compound