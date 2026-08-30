import pygame
from src.molarmass.model import MolarMassQuestion, get_random_molar_question
from src.ui.ui import Button, TextBox, UIManager
from src.utils.save_manager import load_high_scores, save_high_score

GAME_WIDTH = 600
GAME_HEIGHT = 600

SUB_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def format_subscripts(formula: str) -> str:
    return formula.translate(SUB_MAP)


class MolarMassCtx:
    def __init__(self, ctx_manager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        # Navigation
        self.back_btn = Button(pygame.Rect(10, 10, 60, 40), "Back")
        self.back_btn.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back_btn)

        # Streak Tracking
        self.streak = 0
        scores = load_high_scores()
        self.high_streak = scores.get("molar_mass_high_streak", 0)

        self.streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 10, 170, 35),
            f"Streak: {self.streak}"
        )
        self.ui.add(self.streak_ui)

        # Active State
        self.question: MolarMassQuestion | None = None
        self.option_buttons: list[Button] = []
        self.formula_ui: TextBox | None = None
        self.feedback_ui: TextBox | None = None

        self.load_next_question()

    def load_next_question(self) -> None:
        """Clears old UI elements and loads a new molar mass question."""
        for btn in self.option_buttons:
            self.ui.remove(btn)
        self.option_buttons.clear()

        if self.formula_ui:
            self.ui.remove(self.formula_ui)
        if self.feedback_ui:
            self.ui.remove(self.feedback_ui)
            self.feedback_ui = None

        prev_formula = self.question.formula if self.question else None
        self.question = get_random_molar_question(previous_formula=prev_formula)

        # Formula Display
        self.formula_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 240) // 2, 110, 240, 50),
            f"Find Mass: {format_subscripts(self.question.formula)}"
        )
        self.ui.add(self.formula_ui)

        # Render 4 Choices
        btn_width, btn_height = 200, 50
        positions = [
            ((GAME_WIDTH - 420) // 2, 220),
            ((GAME_WIDTH - 420) // 2 + 220, 220),
            ((GAME_WIDTH - 420) // 2, 290),
            ((GAME_WIDTH - 420) // 2 + 220, 290),
        ]

        for i, val in enumerate(self.question.options):
            x, y = positions[i]
            btn = Button(pygame.Rect(x, y, btn_width, btn_height), f"{val:.2f} g/mol")
            btn.on("click", lambda _, selected=val: self.check_answer(selected))
            self.ui.add(btn)
            self.option_buttons.append(btn)

    def check_answer(self, selected_mass: float) -> None:
        if self.question is None:
            return

        if selected_mass == self.question.correct_mass:
            self.streak += 1
            if self.streak > self.high_streak:
                self.high_streak = self.streak
                save_high_score("molar_mass", self.high_streak)
            self.load_next_question()
        else:
            self.streak = 0
            if not self.feedback_ui:
                self.feedback_ui = TextBox(
                    pygame.Rect((GAME_WIDTH - 360) // 2, 370, 360, 35),
                    f"Wrong! Answer: {self.question.correct_mass:.2f} g/mol"
                )
                self.ui.add(self.feedback_ui)

    def update(self, dt: float) -> None:
        self.streak_ui.text = f"Streak: {self.streak}"

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

    def render(self, target_surface: pygame.Surface, dt: float) -> None:
        target_surface.fill((245, 241, 232))
        self.ui.draw(target_surface)