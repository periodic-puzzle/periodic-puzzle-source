import pygame
from src.naming.model import Compound, get_random_compound
from src.ui.ui import Button, TextBox, UIManager
from src.ui.theme import (
    HoverableTheme,
    CardTheme,
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

def format_subscripts(formula: str) -> str:
    return formula.translate(SUB_MAP)

# The formula itself is the star of the question, so it gets a large,
# clearly-separate white tile instead of blending in with the same gray
# used for every other box on screen.
FORMULA_THEME = HoverableTheme(
    background_color=(255, 255, 255),
    hover_color=(255, 255, 255),
    text_color=(35, 35, 45),
    font_size=34,
    border_radius=14,
)

HINT_TEXT = "Pick the correct name for the formula above."
# How long the correct/incorrect highlight stays on screen before the
# next question loads.
ADVANCE_DELAY_CORRECT = 0.5
ADVANCE_DELAY_WRONG = 1.2


class NamingCtx:
    def __init__(self, ctx_manager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        # Navigation
        self.back_btn = Button(pygame.Rect(10, 10, 60, 40), "Back")
        self.back_btn.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back_btn)

        self.title_ui = TextBox(
            pygame.Rect(75, 12, 340, 36), "Name the Compound", theme=TitleTheme
        )
        self.ui.add(self.title_ui)

        # Streak Tracking
        self.streak = 0
        scores = load_high_scores()
        self.high_streak = scores.get("naming_high_streak", 0)

        self.streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 10, 170, 35),
            f"Streak: {self.streak}"
        )
        self.ui.add(self.streak_ui)

        self.high_streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 50, 170, 35),
            f"Best: {self.high_streak}",
        )
        self.ui.add(self.high_streak_ui)

        # Feedback banner: a passive hint before an answer is picked, then
        # a colored verdict, mirroring the button highlight so the result
        # is clear even at a glance.
        self.feedback_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 380) // 2, 380, 380, 35),
            HINT_TEXT,
            theme=HintTheme
        )
        self.ui.add(self.feedback_ui)

        # Active Compound
        self.compound: Compound | None = None
        self.option_buttons: list[Button] = []
        self.formula_ui: TextBox | None = None

        # Gates input and drives the pause between an answer and the next
        # question, so the correct/incorrect highlight is actually
        # visible instead of instantly being replaced.
        self.locked = False
        self.advance_timer = 0.0

        self.load_next_question()

    def load_next_question(self) -> None:
        """Clears old UI buttons and sets up the next compound question."""
        # Clean up old buttons
        for btn in self.option_buttons:
            self.ui.remove(btn)
        self.option_buttons.clear()

        if self.formula_ui:
            self.ui.remove(self.formula_ui)

        self.locked = False
        self.feedback_ui.text = HINT_TEXT
        self.feedback_ui.theme = HintTheme

        # Load new compound
        self.compound = get_random_compound()

        # Display Formula
        self.formula_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 280) // 2, 110, 280, 70),
            format_subscripts(self.compound.formula),
            theme=FORMULA_THEME
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
            btn = Button(pygame.Rect(x, y, btn_width, btn_height), choice_text, theme=CardTheme)
            # Bind both the answer text and the button itself as default
            # params (avoids the classic lambda-in-a-loop scope bug), so
            # check_answer can highlight exactly the tile that was clicked.
            btn.on("click", lambda _, c=choice_text, b=btn: self.check_answer(c, b))
            self.ui.add(btn)
            self.option_buttons.append(btn)

    def check_answer(self, selected_name: str, selected_btn: Button) -> None:
        """Highlights correct/incorrect tiles, updates streak, and queues the next question."""
        if self.compound is None or self.locked:
            return

        self.locked = True
        correct_name = self.compound.name

        # Reveal the right answer and flag the wrong pick, then freeze the
        # board so the player can see the result before it moves on.
        for btn in self.option_buttons:
            btn.enabled = False
            if btn.text == correct_name:
                btn.theme = CorrectTheme
            elif btn is selected_btn:
                btn.theme = IncorrectTheme

        if selected_name == correct_name:
            self.streak += 1
            if self.streak > self.high_streak:
                self.high_streak = self.streak
                save_high_score("naming", self.high_streak)
            self.feedback_ui.text = "Correct!"
            self.feedback_ui.theme = CorrectTheme
            self.advance_timer = ADVANCE_DELAY_CORRECT
        else:
            self.streak = 0
            self.feedback_ui.text = f"Not quite — it's {correct_name}."
            self.feedback_ui.theme = IncorrectTheme
            self.advance_timer = ADVANCE_DELAY_WRONG

    def update(self, dt: float) -> None:
        self.streak_ui.text = f"Streak: {self.streak}"
        self.high_streak_ui.text = f"Best: {self.high_streak}"

        if self.locked:
            self.advance_timer -= dt
            if self.advance_timer <= 0:
                self.load_next_question()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

    def render(self, target_surface: pygame.Surface, dt: float) -> None:
        target_surface.fill(PAGE_BACKGROUND)
        self.ui.draw(target_surface)