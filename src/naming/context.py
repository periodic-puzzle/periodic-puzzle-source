import pygame
from src.naming.model import Compound, get_random_compound
from src.ui.ui import Button, TextBox, UIManager
from src.utils.save_manager import load_high_scores, save_high_score

GAME_WIDTH = 600
GAME_HEIGHT = 600

SUB_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def format_subscripts(formula: str) -> str:
    return formula.translate(SUB_MAP)


class NamingCtx:
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
        self.high_streak = scores.get("naming_high_streak", 0)

        self.streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 10, 170, 35),
            f"Streak: {self.streak}"
        )
        self.ui.add(self.streak_ui)

        # Active Compound
        self.compound: Compound | None = None
        self.option_buttons: list[Button] = []
        self.formula_ui: TextBox | None = None
        self.feedback_ui: TextBox | None = None

        self.load_next_question()

    def load_next_question(self) -> None:
        """Clears old UI buttons and sets up the next compound question."""
        # Clean up old buttons
        for btn in self.option_buttons:
            self.ui.remove(btn)
        self.option_buttons.clear()

        if self.formula_ui:
            self.ui.remove(self.formula_ui)
        if self.feedback_ui:
            self.ui.remove(self.feedback_ui)
            self.feedback_ui = None

        # Load new compound
        self.compound = get_random_compound()

        # Display Formula
        self.formula_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 240) // 2, 120, 240, 60),
            format_subscripts(self.compound.formula)
        )
        self.ui.add(self.formula_ui)

        # Display 4 Option Buttons (2x2 Grid)
        btn_width, btn_height = 220, 50
        positions = [
            ((GAME_WIDTH - 460) // 2, 240),
            ((GAME_WIDTH - 460) // 2 + 240, 240),
            ((GAME_WIDTH - 460) // 2, 310),
            ((GAME_WIDTH - 460) // 2 + 240, 310),
        ]

        for i, choice_text in enumerate(self.compound.options):
            x, y = positions[i]
            btn = Button(pygame.Rect(x, y, btn_width, btn_height), choice_text)
            # Use default parameter `c=choice_text` to avoid lambda scope bugs
            btn.on("click", lambda _, c=choice_text: self.check_answer(c))
            self.ui.add(btn)
            self.option_buttons.append(btn)

    def check_answer(self, selected_name: str) -> None:
        """Increments streak on correct choice or resets on mistake."""
        if self.compound is None:
            return
        
        if selected_name == self.compound.name:
            self.streak += 1
            if self.streak > self.high_streak:
                self.high_streak = self.streak
                save_high_score("naming", self.high_streak)
            self.load_next_question()
        else:
            self.streak = 0
            if not self.feedback_ui:
                self.feedback_ui = TextBox(
                    pygame.Rect((GAME_WIDTH - 340) // 2, 380, 340, 35),
                    f"Wrong! Answer: {self.compound.name}"
                )
                self.ui.add(self.feedback_ui)

    def update(self, dt: float) -> None:
        self.streak_ui.text = f"Streak: {self.streak}"

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

    def render(self, target_surface: pygame.Surface, dt: float) -> None:
        target_surface.fill((245, 241, 232))
        self.ui.draw(target_surface)