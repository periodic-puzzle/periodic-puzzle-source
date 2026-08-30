from __future__ import annotations
import pygame
from src.chemistry.species import ChemicalSpecies, FinishedCompound
from src.sliding.sliding import GameGrid, MoveEvent
from src.ui.animated_tile import AnimMode, AnimatedTile
from src.ui import UIManager, Button
from src.ui.group_theme import group_themes
from src.ui.theme import DefaultButtonTheme

def draw_lewis_dots_overlay(surface: pygame.Surface, rect: pygame.Rect, open_dots: int, color: tuple[int, int, int] | tuple[int, int, int, int]):
    """Draws up to 8 valence dots in pairs directly onto a target screen rect."""
    if open_dots <= 0:
        return

    dot_radius = max(2, rect.width // 22)
    margin = max(6, rect.width // 10)
    offset = max(5, rect.width // 12)

    cx, cy = rect.centerx, rect.centery

    positions = [
        # Top pair
        (cx - offset, rect.top + margin),
        (cx + offset, rect.top + margin),
        # Right pair
        (rect.right - margin, cy - offset),
        (rect.right - margin, cy + offset),
        # Bottom pair
        (cx - offset, rect.bottom - margin),
        (cx + offset, rect.bottom - margin),
        # Left pair
        (rect.left + margin, cy - offset),
        (rect.left + margin, cy + offset),
    ]

    for i in range(min(open_dots, len(positions))):
        pygame.draw.circle(surface, color, positions[i], dot_radius)

class GridView:
    def __init__(self, ui_manager: UIManager, grid_size: int = 4):
        self.manager = ui_manager
        self.grid_size = grid_size
        
        self.sliding_tiles: list[AnimatedTile] = []
        self.pop_spawn_tiles: list[AnimatedTile] = []
        self.wiggle_tiles: list[AnimatedTile] = []
        self.static_buttons: list[Button] = []
        
        self.active_slide_targets: set[tuple[int, int]] = set()
        self.pending_pop_positions: list[tuple[int, int]] = []
        self.pending_spawn: tuple[tuple[int, int], ChemicalSpecies] | None = None
        
        if not pygame.font.get_init():
            pygame.font.init()

    @property
    def is_animating(self) -> bool:
        """Lock user inputs during slides or pop/spawn animations (ignores ongoing wiggles)."""
        return len(self.sliding_tiles) > 0 or len(self.pop_spawn_tiles) > 0

    def cleanup(self) -> None:
        """Removes registered static grid buttons from the UIManager."""
        for btn in self.static_buttons:
            self.manager.remove(btn)
        self.static_buttons.clear()

    def trigger_move(
        self,
        move_events: list[MoveEvent],
        cell_size: tuple[int, int],
        offset: tuple[int, int],
        spawn_pos: tuple[int, int] | None = None,
        spawn_species: ChemicalSpecies | None = None
    ):
        cell_w, cell_h = cell_size
        offset_x, offset_y = offset
        
        self.sliding_tiles.clear()
        self.pop_spawn_tiles.clear()
        self.wiggle_tiles.clear()  # Temporarily stop wiggling during active board movements
        self.active_slide_targets.clear()
        self.pending_pop_positions.clear()

        for event in move_events:
            start_px = (event.from_pos[0] * cell_w + offset_x, event.from_pos[1] * cell_h + offset_y)
            target_px = (event.to_pos[0] * cell_w + offset_x, event.to_pos[1] * cell_h + offset_y)

            tile = AnimatedTile(
                species=event.species,
                start_px=start_px,
                target_px=target_px,
                size=cell_size,
                duration=0.12,
                mode=AnimMode.SLIDE
            )
            self.sliding_tiles.append(tile)
            self.active_slide_targets.add(event.to_pos)

            if event.merged and event.to_pos not in self.pending_pop_positions:
                self.pending_pop_positions.append(event.to_pos)

        if spawn_pos and spawn_species:
            self.pending_spawn = (spawn_pos, spawn_species)

    def update_and_render(self, grid: GameGrid, surface: pygame.Surface, dt: float, cell_size: tuple[int, int], offset: tuple[int, int]):
        # 1. Update Animations
        if len(self.sliding_tiles) > 0:
            for tile in self.sliding_tiles:
                tile.update(dt)
            self.sliding_tiles = [t for t in self.sliding_tiles if not t.is_finished]

            if len(self.sliding_tiles) == 0:
                self.active_slide_targets.clear()
                self._start_pop_and_spawn_phase(grid, cell_size, offset)

        if len(self.sliding_tiles) == 0 and len(self.pop_spawn_tiles) > 0:
            for tile in self.pop_spawn_tiles:
                tile.update(dt)
            self.pop_spawn_tiles = [t for t in self.pop_spawn_tiles if not t.is_finished]

        # Sync wiggle animations when grid is idle
        if not self.is_animating:
            self._update_wiggle_tiles(grid, cell_size, offset)
            for tile in self.wiggle_tiles:
                tile.update(dt)

        # 2. Render Base Static Grid
        self._render_static_grid(grid, surface, cell_size, offset)

        # 3. Render Overlay Animations
        if self.is_animating:
            for tile in self.sliding_tiles:
                tile.draw(surface)
            for tile in self.pop_spawn_tiles:
                tile.draw(surface)
        else:
            for tile in self.wiggle_tiles:
                tile.draw(surface)

    def _update_wiggle_tiles(self, grid: GameGrid, cell_size: tuple[int, int], offset: tuple[int, int]):
        """Ensures active wiggle tiles exist for all finished clickable compounds."""
        cell_w, cell_h = cell_size
        offset_x, offset_y = offset

        wiggle_positions = {}
        for r, row in enumerate(grid.grid):
            for c, species in enumerate(row):
                if species is not None and species.can_keep and isinstance(species, FinishedCompound):
                    wiggle_positions[(c, r)] = species

        if len(self.wiggle_tiles) == len(wiggle_positions):
            return

        self.wiggle_tiles.clear()
        for (col, row), species in wiggle_positions.items():
            px = (col * cell_w + offset_x, row * cell_h + offset_y)
            w_tile = AnimatedTile(
                species=species,
                start_px=px,
                target_px=px,
                size=cell_size,
                duration=0.6,
                mode=AnimMode.WIGGLE,
                loop=True
            )
            self.wiggle_tiles.append(w_tile)

    def _start_pop_and_spawn_phase(self, grid: GameGrid, cell_size: tuple[int, int], offset: tuple[int, int]):
        cell_w, cell_h = cell_size
        offset_x, offset_y = offset

        for col, row in self.pending_pop_positions:
            product_species = grid.grid[row][col]
            if product_species is not None:
                px = (col * cell_w + offset_x, row * cell_h + offset_y)
                pop_tile = AnimatedTile(
                    species=product_species,
                    start_px=px,
                    target_px=px,
                    size=cell_size,
                    duration=0.20,
                    mode=AnimMode.POP
                )
                self.pop_spawn_tiles.append(pop_tile)

        self.pending_pop_positions.clear()
        grid.clear_temporary_compounds()

        if self.pending_spawn:
            pos, species = self.pending_spawn
            px = (pos[0] * cell_w + offset_x, pos[1] * cell_h + offset_y)
            spawn_tile = AnimatedTile(
                species=species,
                start_px=px,
                target_px=px,
                size=cell_size,
                duration=0.10,
                mode=AnimMode.SPAWN
            )
            self.pop_spawn_tiles.append(spawn_tile)
            self.pending_spawn = None

    def _render_static_grid(self, grid: GameGrid, surface: pygame.Surface, cell_size: tuple[int, int], offset: tuple[int, int]) -> None:
        cell_w, cell_h = cell_size
        offset_x, offset_y = offset
        actual_grid_size = len(grid.grid)

        # Dynamic resizing fix: recreate static buttons if dimensions don't match grid
        expected_button_count = actual_grid_size * actual_grid_size
        if len(self.static_buttons) != expected_button_count:
            self.cleanup()
            for row_idx in range(actual_grid_size):
                for col_idx in range(actual_grid_size):
                    rect = pygame.Rect(
                        col_idx * cell_w + offset_x,
                        row_idx * cell_h + offset_y,
                        cell_w,
                        cell_h
                    )
                    btn = Button(rect=rect, text="", padding=int(cell_h * 0.2))
                    self.static_buttons.append(btn)
                    self.manager.add(btn)

        active_anim_positions: set[tuple[int, int]] = set()
        
        for tile in self.pop_spawn_tiles:
            col = int((tile.target_x - offset_x) // cell_w)
            row = int((tile.target_y - offset_y) // cell_h)
            active_anim_positions.add((col, row))

        if not self.is_animating:
            for tile in self.wiggle_tiles:
                col = int((tile.start_x - offset_x) // cell_w)
                row = int((tile.start_y - offset_y) // cell_h)
                active_anim_positions.add((col, row))

        masked_positions = active_anim_positions | self.active_slide_targets

        idx = 0
        for row_idx, row in enumerate(grid.grid):
            for col_idx, species in enumerate(row):
                btn = self.static_buttons[idx]
                btn.remove_callback("click")
                idx += 1

                btn.rect.x = col_idx * cell_w + offset_x
                btn.rect.y = row_idx * cell_h + offset_y
                btn.rect.width = cell_w
                btn.rect.height = cell_h

                if (col_idx, row_idx) in masked_positions:
                    btn.text = ""
                    btn.theme = DefaultButtonTheme
                elif species is not None:
                    btn.text = species.formula
                    btn.theme = group_themes.get(species.category, DefaultButtonTheme)
                else:
                    btn.text = ""
                    btn.theme = DefaultButtonTheme

                if species is not None and species.can_keep and isinstance(species, FinishedCompound):
                    def make_callback(r: int, c: int, spec: ChemicalSpecies, rect_pos: tuple[int, int]):
                        def cb():
                            if grid.grid[r][c] == spec:
                                self.wiggle_tiles.clear()
                                pop_tile = AnimatedTile(
                                    species=spec,
                                    start_px=rect_pos,
                                    target_px=rect_pos,
                                    size=cell_size,
                                    duration=0.10,
                                    mode=AnimMode.POP
                                )
                                self.pop_spawn_tiles.append(pop_tile)
                                grid.pop((c, r))
                        return cb

                    btn.on("click", callback=make_callback(row_idx, col_idx, species, btn.rect.topleft))

                btn.draw(surface)
                if (col_idx, row_idx) not in masked_positions and species is not None:
                    open_dots = getattr(species, "open_dots", 0)
                    if open_dots > 0:
                        draw_lewis_dots_overlay(
                            surface,
                            btn.rect,
                            open_dots,
                            btn.theme.text_color
                        )