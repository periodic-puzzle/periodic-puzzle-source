from __future__ import annotations
from typing import Protocol
import pygame
import asyncio

from src.molarmass.context import MolarMassCtx
from src.naming.context import NamingCtx
from src.ui import UIManager
from src.chemistry.register_species import register_species
from src.chemistry.register_reactions import register_reactions
from src.sliding.sliding import GameGrid, Directions
from src.ui.grid_view import GridView
from src.ui.theme import ClickableTheme, HoverableTheme
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

        # Static Game Over UI
        self.gameover_text = TextBox(
            rect=pygame.Rect(GAME_WIDTH // 2 - 200, GAME_HEIGHT // 2 - 100, 400, 200),
            text="GAME OVER: press R to restart"
        )

        # Navigation UI
        self.back = Button(pygame.Rect(10, 10, 80, 40), "Back")
        self.back.on("click", lambda: self.ctx_manager.switch_to("menu"))
        self.ui.add(self.back)

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
                
                # Check if game is over; any tap on screen will restart
                if self.grid.game_over:
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
                if self.grid.game_over:
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
            except IndexError:
                self.grid.game_over = True

    def update(self, dt: float) -> None:
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

        self.ui.draw(target_surface)

        if self.grid.game_over:
            self.gameover_text.draw(target_surface)

class MenuCtx:
    def __init__(self, ctx_manager: CtxManager) -> None:
        self.ctx_manager = ctx_manager
        self.ui = UIManager()

        title_center = (GAME_WIDTH // 2, GAME_HEIGHT // 8)
        title_size = (300, 100)
        offset = to_top_left(title_center, title_size)

        menu_text = TextBox(
            rect=pygame.Rect(offset, title_size), 
            text="Periodic Puzzle", 
            theme=HoverableTheme(background_color=(245, 241, 232), hover_color=(245, 241, 232))
        )
        self.ui.add(menu_text)

        play_btn = Button(rect=pygame.Rect((offset[0] + 75, offset[1] + 100), (150, 60)), text="Sliding")
        play_btn.on("click", lambda: self.ctx_manager.switch_to("sliding"))
        self.ui.add(play_btn)
        
        balancing_btn = Button(rect=pygame.Rect((offset[0] + 75, offset[1] + 175), (150, 60)), text="Balancing")
        balancing_btn.on("click", lambda: self.ctx_manager.switch_to("balancing"))
        self.ui.add(balancing_btn)
        
        naming_btn = Button(rect=pygame.Rect((offset[0] + 75, offset[1] + 250), (150, 60)), text="Naming")
        naming_btn.on("click", lambda: self.ctx_manager.switch_to("naming"))
        self.ui.add(naming_btn)
        
        mm_btn = Button(rect=pygame.Rect((offset[0] + 75, offset[1] + 325), (150, 60)), text="Molar Mass")
        mm_btn.on("click", lambda: self.ctx_manager.switch_to("molarmass"))
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
        elif name == "molarmass":
            self.active_context = MolarMassCtx(self)
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