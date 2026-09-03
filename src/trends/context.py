import pygame
from src.trends.model import get_random_challenge, ElementData
from src.ui.ui import Button, TextBox, UIManager
from src.ui.theme import ClickableTheme, HoverableTheme
from src.utils.save_manager import load_high_scores, save_high_score

GAME_WIDTH = 600
GAME_HEIGHT = 600

# Muted, Balanced Palette
BG_COLOR = (248, 249, 250)
BELT_COLOR = (220, 225, 230)
CARD_BG = (255, 255, 255)
CARD_BORDER = (200, 205, 215)
TEXT_PRIMARY = (40, 45, 55)

# Clean, uniform neutral bin theme
NEUTRAL_BIN_THEME = ClickableTheme(
    background_color=(235, 238, 242), text_color=(60, 65, 75),
    hover_color=(225, 228, 235), pressed_color=(210, 215, 222),
    font_size=16, border_radius=8
)


class SimpleCard:
    """Minimalist, flat card representation."""
    def __init__(self, element: ElementData, start_x: float, start_y: float):
        self.element = element
        self.width = 90
        self.height = 90
        self.rect = pygame.Rect(int(start_x), int(start_y), self.width, self.height)
        
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

    def update_position(self, speed: float) -> None:
        if not self.is_dragging:
            self.rect.x += int(speed)

    def draw(self, surface: pygame.Surface, font_lg: pygame.font.Font, font_sm: pygame.font.Font) -> None:
        # Flat white background with subtle border
        pygame.draw.rect(surface, CARD_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=2, border_radius=8)

        # Atomic number top-left
        num_surf = font_sm.render(str(self.element.atomic_number), True, (120, 125, 135))
        surface.blit(num_surf, (self.rect.x + 8, self.rect.y + 6))

        # Main symbol center
        sym_surf = font_lg.render(self.element.symbol, True, TEXT_PRIMARY)
        sym_rect = sym_surf.get_rect(center=(self.rect.centerx, self.rect.centery - 2))
        surface.blit(sym_surf, sym_rect)

        # Element name bottom
        name_surf = font_sm.render(self.element.name, True, (100, 105, 115))
        name_rect = name_surf.get_rect(center=(self.rect.centerx, self.rect.bottom - 12))
        surface.blit(name_surf, name_rect)


class PeriodicTrendsCtx:
    """Gameplay loop: Clean Periodic Trends Categorization."""

    def __init__(self, ctx_manager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        # Navigation & Streak
        self.back_btn = Button(pygame.Rect(10, 10, 60, 40), "Back")
        self.back_btn.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back_btn)

        self.streak = 0
        scores = load_high_scores()
        self.high_streak = scores.get("periodic_trends_high_streak", 0)

        self.streak_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 180, 10, 170, 35),
            f"Streak: {self.streak}"
        )
        self.ui.add(self.streak_ui)

        # Fonts
        self.font_lg = pygame.font.SysFont("arial", 26, bold=True)
        self.font_sm = pygame.font.SysFont("arial", 12)

        # Conveyor Belt Parameters
        self.belt_rect = pygame.Rect(0, 240, GAME_WIDTH, 100)
        self.belt_speed = 2.0

        # Spawning Parameters (Time-based spawning)
        self.cards: list[SimpleCard] = []
        self.spawn_interval = 1.5  # Spawns a new element every 2 seconds
        self.spawn_timer = 0.0

        # Drop Bins Setup
        self.bins: dict[str, pygame.Rect] = {
            "Metal": pygame.Rect(40, 420, 150, 90),
            "Metalloid": pygame.Rect(225, 420, 150, 90),
            "Non-Metal": pygame.Rect(410, 420, 150, 90),
        }
        for label, rect in self.bins.items():
            self.ui.add(Button(rect, label, theme=NEUTRAL_BIN_THEME))

        # Header Prompt
        self.prompt_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 440) // 2, 70, 440, 40),
            "Classify elements into their chemical group"
        )
        self.ui.add(self.prompt_ui)

        self.feedback_ui: TextBox | None = None
        self.spawn_next_element()

    def spawn_next_element(self) -> None:
        challenge = get_random_challenge()
        element = challenge.elements[0]
        card = SimpleCard(element, start_x=-100, start_y=245)
        self.cards.append(card)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check cards in reverse order so top/front card gets grabbed first
            for card in reversed(self.cards):
                if card.rect.collidepoint(event.pos):
                    card.is_dragging = True
                    card.drag_offset_x = card.rect.x - event.pos[0]
                    card.drag_offset_y = card.rect.y - event.pos[1]
                    # Move grabbed card to top of render list
                    self.cards.remove(card)
                    self.cards.append(card)
                    break

        elif event.type == pygame.MOUSEMOTION:
            for card in self.cards:
                if card.is_dragging:
                    card.rect.x = event.pos[0] + card.drag_offset_x
                    card.rect.y = event.pos[1] + card.drag_offset_y

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for card in self.cards:
                if card.is_dragging:
                    card.is_dragging = False
                    self._check_drop_collision(card)

    def _check_drop_collision(self, card: SimpleCard) -> None:
        dropped_in_bin = False
        for category, bin_rect in self.bins.items():
            if bin_rect.colliderect(card.rect):
                dropped_in_bin = True
                if category == card.element.category:
                    self._on_correct(card)
                else:
                    self._on_incorrect(card, f"{card.element.symbol} is a {card.element.category}")
                break

        if not dropped_in_bin:
            card.rect.y = 245

    def _on_correct(self, card: SimpleCard) -> None:
        self.streak += 1
        if self.streak > self.high_streak:
            self.high_streak = self.streak
            save_high_score("periodic_trends", self.high_streak)

        if self.feedback_ui:
            self.ui.remove(self.feedback_ui)
            self.feedback_ui = None

        if card in self.cards:
            self.cards.remove(card)

    def _on_incorrect(self, card: SimpleCard, message: str) -> None:
        self.streak = 0
        if self.feedback_ui:
            self.ui.remove(self.feedback_ui)

        self.feedback_ui = TextBox(
            pygame.Rect((GAME_WIDTH - 400) // 2, 170, 400, 35),
            message
        )
        self.ui.add(self.feedback_ui)

        if card in self.cards:
            self.cards.remove(card)

    def update(self, dt: float) -> None:
        self.streak_ui.text = f"Streak: {self.streak}"

        # Continuously spawn new elements over time
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_next_element()

        # Update card positions and check for missed cards
        for card in list(self.cards):
            card.update_position(self.belt_speed)
            if card.rect.x > GAME_WIDTH:
                self._on_incorrect(card, f"Missed {card.element.symbol}!")

    def render(self, target_surface: pygame.Surface, dt: float) -> None:
        target_surface.fill(BG_COLOR)

        # Minimal belt line
        pygame.draw.rect(target_surface, BELT_COLOR, self.belt_rect)

        self.ui.draw(target_surface)

        # Render cards
        for card in self.cards:
            card.draw(target_surface, self.font_lg, self.font_sm)