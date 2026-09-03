from __future__ import annotations
from typing import Protocol
import pygame
import asyncio

from src.trends.context import PeriodicTrendsCtx
from src.naming.context import NamingCtx
from src.ui import UIManager
from src.chemistry.register_species import register_species
from src.chemistry.register_reactions import register_reactions
from src.sliding.sliding import GameGrid, Directions, TIER_UNLOCK_MESSAGES
from src.ui.grid_view import GridView
from src.ui.theme import ClickableTheme, HoverableTheme, ToastTheme, RestartButtonTheme
from src.ui.ui import Button, TextBox
from src.chemistry.registry import SpeciesRegistry
from src.utils.save_manager import load_high_scores, save_high_score
from src.balancing.context import BalancingCtx
from src.sliding.tutorial.manager import SlidingTutorialManager
from src.constants.constants import ASSETS
# Initialize Game Subsystems
register_species()
register_reactions()
pygame.init()
pygame.display.set_caption("Periodic Puzzle")
icon = pygame.image.load(ASSETS / "images" / "window_icon.png")
pygame.display.set_icon(icon)

GAME_WIDTH = 600
GAME_HEIGHT = 600

def to_top_left(center: tuple[int, int], size: tuple[int, int]) -> tuple[int, int]:
    cx, cy = center
    sx, sy = size
    return (cx - sx // 2, cy - sy // 2)

class Context(Protocol):
    ui: UIManager
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def render(self, target_surface: pygame.Surface, dt: float) -> None: ...


class SlidingCtx:
    def __init__(self, ctx_manager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()
        
        grid_size = 4
        self.grid_offset = to_top_left((GAME_WIDTH // 2, GAME_HEIGHT // 2), (300, 300))
        self.cell_size = (300 // grid_size, 300 // grid_size)

        # Swipe-gesture tracking (covers touch on mobile web and
        # click-drag on desktop, on top of the existing keyboard controls).
        self.is_touch_input = False
        self._gesture_start: tuple[float, float] | None = None
        self.SWIPE_THRESHOLD = 40  # pixels a drag must cover to count as a swipe


        # Standard Score UI
        self.score = TextBox(pygame.Rect(GAME_WIDTH - 100, 0, 100, 50), "Score: 0")
        self.ui.add(self.score)
        
        scores = load_high_scores()
        self.high_score = scores.get("sliding_high_score", 0)
        self.high_score_ui = TextBox(
            pygame.Rect(GAME_WIDTH - 100, 50, 100, 50),
            f"High Score: {self.high_score}"
        )
        self.ui.add(self.high_score_ui)

        # Navigation UI
        self.back = Button(pygame.Rect(10, 10, 80, 40), "Back")
        self.back.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back)

        # --- Toast banner (tier unlocks, reaction chains) -------------------
        # Hidden by default; update() drives visibility/text and pops the
        # next queued message once the current one's timer expires.
        self.toast_queue: list[str] = []
        self.toast_timer: float = 0.0
        self.toast_box = TextBox(
            rect=pygame.Rect(GAME_WIDTH // 2 - 160, 102, 320, 44),
            text="",
            theme=ToastTheme,
        )
        self.toast_box.visible = False
        self.ui.add(self.toast_box)

        # --- Game Over panel --------------------------------------------
        # A small opaque card drawn manually in render() (see below), with
        # these as real UI elements layered on top so the restart button
        # stays clickable. All hidden until the grid reports game_over.
        panel_left = GAME_WIDTH // 2 - 170
        panel_top = GAME_HEIGHT // 2 - 120
        self.gameover_title = TextBox(
            rect=pygame.Rect(panel_left + 10, panel_top + 12, 320, 40),
            text="Game Over",
        )
        self.gameover_score_line = TextBox(
            rect=pygame.Rect(panel_left + 30, panel_top + 60, 280, 30),
            text="",
        )
        self.gameover_highscore_line = TextBox(
            rect=pygame.Rect(panel_left + 30, panel_top + 95, 280, 30),
            text="",
        )
        self.gameover_compounds_line = TextBox(
            rect=pygame.Rect(panel_left + 30, panel_top + 130, 280, 30),
            text="",
        )
        self.gameover_restart_btn = Button(
            rect=pygame.Rect(panel_left + 60, panel_top + 172, 220, 48),
            text="Restart",
            theme=RestartButtonTheme,
        )
        self.gameover_restart_btn.on("click", lambda: self.ctx_manager.switch_to("sliding"))

        self.gameover_elements = [
            self.gameover_title,
            self.gameover_score_line,
            self.gameover_highscore_line,
            self.gameover_compounds_line,
            self.gameover_restart_btn,
        ]
        for el in self.gameover_elements:
            el.visible = False
            self.ui.add(el)
        # Panel card geometry, reused by render() for the backdrop rect.
        self.gameover_panel_rect = pygame.Rect(panel_left - 20, panel_top - 15, 380, 260)
        self._gameover_panel_built = False

        # Determine if tutorial should run
        self.in_tutorial = self.high_score == 0

        # Tutorial UI Components & Manager
        self.tutorial_banner = TextBox(
            rect=pygame.Rect(GAME_WIDTH // 2 - 200, 70, 400, 70),
            text=""
        )
        self.skip_button = Button(pygame.Rect(10, 60, 80, 30), "Skip")
        self.skip_button.on("click", self.finish_tutorial)

        if self.in_tutorial:
            self.tutorial_mgr = SlidingTutorialManager(grid_size=grid_size)
            self.grid = self.tutorial_mgr.game_grid
            self.ui.add(self.tutorial_banner)
            self.ui.add(self.skip_button)
        else:
            self.tutorial_mgr = None
            self.grid = GameGrid(grid_size=grid_size)
            self.grid.spawn()
            self.grid.spawn()

        # GridView owns/draws its own tile buttons directly (so it can
        # layer static tiles under slide/pop/wiggle animations). It must
        # NOT share `self.ui`, or those buttons get registered there too
        # and `self.ui.draw()` will redraw them a second time on top of
        # the animation layer, blanking it out. It still needs its own
        # manager for click/hover handling, so we feed it events manually.
        self.grid_ui = UIManager()
        self.grid_view = GridView(self.grid_ui, self.grid.grid_size)

        # Track the tier the player was on last frame so a toast can fire
        # exactly once, the moment a new tier is actually reached. Must
        # come after self.grid is assigned above (tutorial or not).
        self.previous_tier = self.grid.get_current_tier_config()["tier"]

    def push_toast(self, text: str) -> None:
        """Queues a short-lived banner message. Multiple toasts queued in
        the same frame are shown one after another rather than clobbering
        each other."""
        self.toast_queue.append(text)

    def finish_tutorial(self) -> None:
        """Transitions from tutorial mode into live gameplay."""
        self.in_tutorial = False
        self.ui.remove(self.tutorial_banner)
        self.ui.remove(self.skip_button)

        # Clean static buttons before recreating standard GameGrid
        self.grid_view.cleanup()

        self.grid = GameGrid(grid_size=4)
        self.grid.spawn()
        self.grid.spawn()
        self.previous_tier = self.grid.get_current_tier_config()["tier"]

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)
        self.grid_ui.process_event(event)

        # --- Touch / mouse-drag swipe & tap detection -----------------------
        if event.type == pygame.FINGERDOWN:
            self.is_touch_input = True
            self._gesture_start = (event.x * GAME_WIDTH, event.y * GAME_HEIGHT)
            return

        elif event.type == pygame.FINGERUP:
            self.is_touch_input = True
            if self._gesture_start is not None:
                end_pos = (event.x * GAME_WIDTH, event.y * GAME_HEIGHT)
                
                # Check if game is over; any tap on screen will restart.
                # Guarded by `active_context is self` because a tap landing
                # on the Restart button will have already triggered a
                # switch_to via self.ui.process_event() a few lines above -
                # without this check we'd spin up a second, immediately
                # discarded SlidingCtx on top of that.
                if self.grid.game_over and self.ctx_manager.active_context is self:
                    self.ctx_manager.switch_to("sliding")
                    self._gesture_start = None
                    return

                self._handle_gesture_end(end_pos)
                self._gesture_start = None
            return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._gesture_start = event.pos
            return

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._gesture_start is not None:
                # Handle reset for mouse clicks as well if game over
                if self.grid.game_over and self.ctx_manager.active_context is self:
                    self.ctx_manager.switch_to("sliding")
                    self._gesture_start = None
                    return

                self._handle_gesture_end(event.pos)
                self._gesture_start = None
            return

        if event.type != pygame.KEYDOWN:
            return

        dir_map = {
            pygame.K_w: Directions.Up,
            pygame.K_a: Directions.Left,
            pygame.K_s: Directions.Down,
            pygame.K_d: Directions.Right,
            pygame.K_UP: Directions.Up,
            pygame.K_LEFT: Directions.Left,
            pygame.K_DOWN: Directions.Down,
            pygame.K_RIGHT: Directions.Right,
        }

        if self.grid.game_over:
            if event.key == pygame.K_r:
                self.ctx_manager.switch_to("sliding")
            return

        if event.key in dir_map:
            self._dispatch_direction(dir_map[event.key])

    def _handle_gesture_end(self, end_pos: tuple[float, float]) -> None:
        """Turns a drag/swipe gesture into a Directions, if it was long
        enough and roughly axis-aligned. Short drags (taps, button clicks)
        fall below SWIPE_THRESHOLD and are ignored here."""
        start_x, start_y = self._gesture_start # type: ignore
        end_x, end_y = end_pos
        dx, dy = end_x - start_x, end_y - start_y

        if max(abs(dx), abs(dy)) < self.SWIPE_THRESHOLD:
            return

        if abs(dx) > abs(dy):
            direction = Directions.Right if dx > 0 else Directions.Left
        else:
            direction = Directions.Down if dy > 0 else Directions.Up

        if self.grid.game_over:
            return

        self._dispatch_direction(direction)

    def _dispatch_direction(self, direction: Directions) -> None:
        if self.grid.game_over or self.grid_view.is_animating:
            return

        # 1. Tutorial Movement Branch
        if self.in_tutorial and self.tutorial_mgr:
            # NOTE: self.grid is intentionally left pointing at the grid
            # that was just swiped. If a reaction occurred, the manager
            # queues the step transition instead of applying it right
            # away, so the pop/spawn animation below still plays out
            # against the grid that actually reacted. The swap to the
            # next step's grid happens later in update(), once the
            # animation has finished (see advance_if_pending()).
            move_events = self.tutorial_mgr.handle_swipe(direction)

            if move_events:
                self.grid_view.trigger_move(
                    move_events=move_events,
                    cell_size=self.cell_size,
                    offset=self.grid_offset,
                    spawn_pos=None,
                    spawn_species=None,
                )

        # 2. Regular Gameplay Branch
        else:
            try:
                move_events = self.grid.swipe(direction)
                spawn_pos, spawn_species = self.grid.spawn()

                self.grid_view.trigger_move(
                    move_events=move_events,
                    cell_size=self.cell_size,
                    offset=self.grid_offset,
                    spawn_pos=spawn_pos,
                    spawn_species=spawn_species,
                )

                chain_count = self.grid_view.consume_last_chain_count()
                if chain_count >= 2:
                    self.push_toast(f"Chain x{chain_count}!")
            except IndexError:
                self.grid.game_over = True

    def update(self, dt: float) -> None:
        # --- Toast banner timing (runs in both tutorial & normal play) -----
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast_box.visible = False

        if self.toast_timer <= 0 and self.toast_queue:
            self.toast_box.text = self.toast_queue.pop(0)
            self.toast_box.visible = True
            self.toast_timer = 2.2

        if self.in_tutorial and self.tutorial_mgr:
            self.tutorial_banner.text = self.tutorial_mgr.get_instruction_text(
                is_touch=self.is_touch_input
            )

            # Only apply a queued step transition once the slide/pop/spawn
            # animation for the reaction that triggered it has fully played.
            if not self.grid_view.is_animating:
                self.tutorial_mgr.advance_if_pending()
                self.grid = self.tutorial_mgr.game_grid

                if self.tutorial_mgr.is_completed:
                    self.finish_tutorial()
        else:
            self.score.text = f"Score: {self.grid.score}"
            if self.grid.score > self.high_score:
                self.high_score = self.grid.score
                self.high_score_ui.text = f"High Score: {self.high_score}"
                save_high_score("sliding", self.high_score)

            # Tier progression toast: fires once, the frame the player's
            # score actually crosses into a new tier.
            current_tier = self.grid.get_current_tier_config()["tier"]
            if current_tier > self.previous_tier:
                message = TIER_UNLOCK_MESSAGES.get(current_tier)
                if message:
                    self.push_toast(message)
                self.previous_tier = current_tier

            # Game Over panel: populate stats once, the frame it appears.
            if self.grid.game_over and not self._gameover_panel_built:
                self._gameover_panel_built = True
                beat_high_score = self.grid.score >= self.high_score and self.grid.score > 0
                self.gameover_score_line.text = f"Score: {self.grid.score}"
                self.gameover_highscore_line.text = (
                    "New High Score!" if beat_high_score else f"High Score: {self.high_score}"
                )
                self.gameover_compounds_line.text = f"Compounds Formed: {self.grid.compounds_formed}"
                for el in self.gameover_elements:
                    el.visible = True
            elif not self.grid.game_over:
                self._gameover_panel_built = False

    def render(self, target_surface: pygame.Surface, dt: float = 0.016) -> None:
        target_surface.fill((245, 241, 232))

        # Pass active dynamic delta time
        self.grid_view.update_and_render(
            grid=self.grid,
            surface=target_surface,
            dt=dt,
            cell_size=self.cell_size,
            offset=self.grid_offset,
        )

        if self.grid.game_over:
            # Dim the board slightly so the card reads as a modal, then
            # draw the opaque card itself. Both happen before self.ui.draw()
            # below, so the score/back button and the panel's own text/
            # restart button (all real UI elements) render crisply on top.
            dim = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 110))
            target_surface.blit(dim, (0, 0))

            pygame.draw.rect(
                target_surface, (250, 247, 240), self.gameover_panel_rect, border_radius=16
            )
            pygame.draw.rect(
                target_surface, (60, 60, 60), self.gameover_panel_rect, width=3, border_radius=16
            )

        self.ui.draw(target_surface)

MODE_BUTTON_THEMES = {
    "Sliding": ClickableTheme(
        background_color=(120, 180, 245), text_color=(255, 255, 255),
        hover_color=(145, 200, 255), pressed_color=(95, 155, 220),
        font_size=24, border_radius=10,
    ),
    "Balancing": ClickableTheme(
        background_color=(185, 140, 245), text_color=(255, 255, 255),
        hover_color=(205, 165, 255), pressed_color=(160, 115, 220),
        font_size=24, border_radius=10,
    ),
    "Naming": ClickableTheme(
        background_color=(110, 205, 185), text_color=(255, 255, 255),
        hover_color=(135, 220, 200), pressed_color=(90, 180, 160),
        font_size=24, border_radius=10,
    ),
    "Molar Mass": ClickableTheme(
        background_color=(255, 175, 95), text_color=(255, 255, 255),
        hover_color=(255, 195, 130), pressed_color=(230, 150, 70),
        font_size=22, border_radius=10,
    ),
}


class MenuCtx:
    def __init__(self, ctx_manager: CtxManager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        title_center = (GAME_WIDTH // 2, GAME_HEIGHT // 8)
        title_size = (400, 60)
        offset = to_top_left(title_center, title_size)

        menu_text = TextBox(
            rect=pygame.Rect(offset, title_size), 
            text="Periodic Puzzle", 
            theme=HoverableTheme(
                background_color=(245, 241, 232), hover_color=(245, 241, 232),
                text_color=(50, 50, 50), font_size=36,
            )
        )
        self.ui.add(menu_text)

        subtitle = TextBox(
            rect=pygame.Rect(offset[0], offset[1] + 44, title_size[0], 24),
            text="Merge elements. Master chemistry.",
            theme=HoverableTheme(
                background_color=(245, 241, 232), hover_color=(245, 241, 232),
                text_color=(120, 115, 105), font_size=16,
            )
        )
        self.ui.add(subtitle)

        button_offset = to_top_left((GAME_WIDTH // 2, GAME_HEIGHT // 8), (300, 100))

        play_btn = Button(
            rect=pygame.Rect((button_offset[0] + 75, button_offset[1] + 100), (150, 60)),
            text="Sliding", theme=MODE_BUTTON_THEMES["Sliding"],
        )
        play_btn.on("click", lambda: self.ctx_manager.switch_to("sliding"))
        self.ui.add(play_btn)

        balancing_btn = Button(
            rect=pygame.Rect((button_offset[0] + 75, button_offset[1] + 175), (150, 60)),
            text="Balancing", theme=MODE_BUTTON_THEMES["Balancing"],
        )
        balancing_btn.on("click", lambda: self.ctx_manager.switch_to("balancing"))
        self.ui.add(balancing_btn)

        naming_btn = Button(
            rect=pygame.Rect((button_offset[0] + 75, button_offset[1] + 250), (150, 60)),
            text="Naming", theme=MODE_BUTTON_THEMES["Naming"],
        )
        naming_btn.on("click", lambda: self.ctx_manager.switch_to("naming"))
        self.ui.add(naming_btn)

        mm_btn = Button(
            rect=pygame.Rect((button_offset[0] + 75, button_offset[1] + 325), (150, 60)),
            text="Periodic Trends", theme=MODE_BUTTON_THEMES["Molar Mass"],
        )
        mm_btn.on("click", lambda: self.ctx_manager.switch_to("periodic_trends"))
        self.ui.add(mm_btn)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui.process_event(event)

    def update(self, dt: float) -> None:
        pass

    def render(self, target_surface: pygame.Surface, dt: float = 0.016) -> None:
        target_surface.fill((245, 241, 232))
        self.ui.draw(target_surface)


class CtxManager:
    def __init__(self) -> None:
        self.active_context: Context | None = None
        self.active_name: str | None = None

    def switch_to(self, name: str) -> None:
        if name == "menu":
            self.active_context = MenuCtx(self)
        elif name == "sliding":
            self.active_context = SlidingCtx(self)
        elif name == "balancing":
            self.active_context = BalancingCtx(self)
        elif name == "naming":
            self.active_context = NamingCtx(self)
        elif name == "periodic_trends":
            self.active_context = PeriodicTrendsCtx(self)
        self.active_name = name


# Main Loop
async def main():
    screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
    clock = pygame.time.Clock()

    ctx_manager = CtxManager()
    ctx_manager.switch_to("menu")

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if ctx_manager.active_context:
                ctx_manager.active_context.handle_event(event)

        if ctx_manager.active_context:
            ctx_manager.active_context.update(dt)
            ctx_manager.active_context.render(screen, dt)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())