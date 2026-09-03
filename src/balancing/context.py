import pygame

from src.balancing.model import Equation, ChemicalTerm, get_dynamic_equation
from src.ui.ui import Button, TextBox, UIElement, UIManager
from src.ui.theme import (
    HoverableTheme,
    RestartButtonTheme,
    CardTheme,
    StepperTheme,
    CorrectTheme,
    IncorrectTheme,
    TitleTheme,
    HintTheme,
    PAGE_BACKGROUND,
)
from src.utils.save_manager import load_high_scores, save_high_score

GAME_WIDTH = 600
GAME_HEIGHT = 600

SUB_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

# Bigger, background-matching text for the static "+" / "→" signs between
# terms, so the equation reads as one line of math instead of a row of
# gray boxes with symbols crammed inside them.
SYMBOL_THEME = HoverableTheme(
    background_color=PAGE_BACKGROUND,
    hover_color=PAGE_BACKGROUND,
    text_color=(90, 85, 80),
    font_size=30,
)

HINT_TEXT = "Adjust the coefficients, then press Check."
# Short pause after a correct answer so the green "Correct!" banner is
# actually visible before the next equation replaces it.
ADVANCE_DELAY = 0.6


def format_subscripts(formula: str) -> str: 
    """Converts standard numbers in a chemical formula into Unicode subscripts.
    
    Example: 'H2O' -> 'H₂O', 'Fe2(SO4)3' -> 'Fe₂'SO₄'₃'
    """
    return formula.translate(SUB_MAP)

class BalancingCtx:
    def __init__(self, ctx_manager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        # Navigation
        self.back_btn = Button(pygame.Rect(10, 10, 60, 40), "Back")
        self.back_btn.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back_btn)

        self.title_ui = TextBox(
            pygame.Rect(75, 12, 340, 36), "Balance the Equation", theme=TitleTheme
        )
        self.ui.add(self.title_ui)

        # Streak Tracking
        self.streak = 0
        scores = load_high_scores()
        self.high_streak = scores.get("balancing_high_streak", 0)

        # UI Displays
        self.streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 10, 170, 35),
            f"Streak: {self.streak}"
        )
        self.ui.add(self.streak_ui)

        self.high_streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 50, 170, 35),
            f"Best Streak: {self.high_streak}",
        )
        self.ui.add(self.high_streak_ui)

        # Feedback banner: a passive hint until the player checks their
        # answer, then a colored verdict (green/red) so success and
        # failure are unmistakable at a glance.
        self.feedback_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 340) // 2, 100, 340, 35),
            HINT_TEXT,
            theme=HintTheme
        )
        self.ui.add(self.feedback_ui)

        self.equation: Equation | None = None
        self.coeff_controls: list[dict] = []
        self.symbol_labels: list[UIElement] = []
        self.last_eq_data: dict | None = None

        # Gates input and drives the pause between a correct answer and
        # the next equation loading, so the "Correct!" banner has time to
        # register instead of being replaced instantly.
        self.locked = False
        self.advance_timer = 0.0

        self.load_next_equation()

    def load_next_equation(self) -> None:
        """Clears existing UI elements and renders the equation with '+' and '→' signs."""
        # Clean up old UI elements
        for item in self.coeff_controls:
            self.ui.remove(item["plus"])
            self.ui.remove(item["minus"])
            self.ui.remove(item["box"])
        for label in getattr(self, "symbol_labels", []):
            self.ui.remove(label)
            
        if hasattr(self, "check_btn"):
            self.ui.remove(self.check_btn)

        self.coeff_controls.clear()
        self.symbol_labels = []

        self.locked = False
        self.feedback_ui.text = HINT_TEXT
        self.feedback_ui.theme = HintTheme

        # Get reaction data
        eq_data = get_dynamic_equation(self.streak * 100, self.last_eq_data)
        self.last_eq_data = eq_data

        self.equation = Equation(
            reactants=[ChemicalTerm(formula=f) for f in eq_data["reactants"]],
            products=[ChemicalTerm(formula=f) for f in eq_data["products"]]
        )

        card_width = 90
        symbol_width = 30
        spacing = 10
        y_pos = 250

        # Build layout tokens: [Term, "+", Term, "→", Term, "+", Term]
        tokens = []
        for i, term in enumerate(self.equation.reactants):
            if i > 0:
                tokens.append("+")
            tokens.append(term)

        tokens.append("->")

        for i, term in enumerate(self.equation.products):
            if i > 0:
                tokens.append("+")
            tokens.append(term)

        # Calculate total layout width for perfect screen centering
        total_width = 0
        for token in tokens:
            if isinstance(token, ChemicalTerm):
                total_width += card_width
            else:
                total_width += symbol_width
            total_width += spacing
        total_width -= spacing  # Remove final trailing spacing

        start_x = (GAME_WIDTH - total_width) // 2
        current_x = start_x

        # Render equation controls & mathematical symbols
        for token in tokens:
            if isinstance(token, ChemicalTerm):
                term = token

                # Plus button (+1 coefficient)
                btn_plus = Button(
                    pygame.Rect(current_x + (card_width - 40) // 2, y_pos - 40, 40, 30), "+",
                    theme=StepperTheme
                )
                btn_plus.on("click", lambda _, t=term: self.adjust_coeff(t, 1))
                self.ui.add(btn_plus)

                # Coefficient + Formula display, styled as a white tile so
                # it reads as the "value" the player is editing.
                txt_box = TextBox(
                    pygame.Rect(current_x, y_pos, card_width, 40),
                    f"{term.user_coefficient} {format_subscripts(term.formula)}",
                    theme=CardTheme
                )
                self.ui.add(txt_box)

                # Minus button (-1 coefficient)
                btn_minus = Button(
                    pygame.Rect(current_x + (card_width - 40) // 2, y_pos + 45, 40, 30), "-",
                    theme=StepperTheme
                )
                btn_minus.on("click", lambda _, t=term: self.adjust_coeff(t, -1))
                self.ui.add(btn_minus)

                self.coeff_controls.append(
                    {"plus": btn_plus, "box": txt_box, "minus": btn_minus, "term": term}
                )
                current_x += card_width + spacing

            else:
                # Render static '+' or '→' label, blended into the page
                # background so it reads as math rather than another box.
                symbol_box = TextBox(
                    pygame.Rect(current_x, y_pos, symbol_width, 40),
                    token,
                    theme=SYMBOL_THEME
                )
                self.ui.add(symbol_box)
                self.symbol_labels.append(symbol_box)
                current_x += symbol_width + spacing

        # Submit Button
        self.check_btn = Button(
            pygame.Rect((GAME_WIDTH - 120) // 2, 400, 120, 50), "Check", theme=RestartButtonTheme
        )
        self.check_btn.on("click", lambda: self.validate_solution())
        self.ui.add(self.check_btn)

    def adjust_coeff(self, term: ChemicalTerm, delta: int) -> None:
        if self.locked:
            return
        term.user_coefficient = max(1, term.user_coefficient + delta)
        for item in self.coeff_controls:
            if item["term"] == term:
                item["box"].text = f"{term.user_coefficient} {format_subscripts(term.formula)}"

    def _set_controls_enabled(self, enabled: bool) -> None:
        for item in self.coeff_controls:
            item["plus"].enabled = enabled
            item["minus"].enabled = enabled
        if hasattr(self, "check_btn"):
            self.check_btn.enabled = enabled

    def validate_solution(self) -> None:
        """Checks answer, increments streak on success, or resets on failure."""
        if self.locked:
            return

        if self.equation and self.equation.is_balanced():
            self.streak += 1

            if self.streak > self.high_streak:
                self.high_streak = self.streak
                save_high_score("balancing", self.high_streak)

            self.feedback_ui.text = "Correct!"
            self.feedback_ui.theme = CorrectTheme
            self.locked = True
            self.advance_timer = ADVANCE_DELAY
            self._set_controls_enabled(False)
        else:
            self.streak = 0
            self.feedback_ui.text = "Not balanced yet — streak reset. Try again."
            self.feedback_ui.theme = IncorrectTheme

    def update(self, dt: float) -> None:
        self.streak_ui.text = f"Streak: {self.streak}"
        self.high_streak_ui.text = f"Best: {self.high_streak}"

        if self.locked:
            self.advance_timer -= dt
            if self.advance_timer <= 0:
                self.load_next_equation()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

    def render(self, target_surface: pygame.Surface, dt: float) -> None:
        target_surface.fill(PAGE_BACKGROUND)
        self.ui.draw(target_surface)