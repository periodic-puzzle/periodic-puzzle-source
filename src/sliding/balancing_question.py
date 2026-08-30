# Model representing a balancing question
class BalancingQuestion:
    def __init__(self, reactants: list[str], products: list[str], coefficients: list[int]):
        # e.g., 2 Na + Cl2 -> 2 NaCl
        self.reactants = reactants       # ["Na", "Cl2"]
        self.products = products         # ["NaCl"]
        self.correct_coefficients = coefficients # [2, 1, 2]
        
    def check_answer(self, user_inputs: list[int]) -> bool:
        return user_inputs == self.correct_coefficients