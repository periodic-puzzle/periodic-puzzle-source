# src/ui/animated_tile.py
import pygame
import math
from enum import Enum
from src.chemistry.species import ChemicalSpecies
from src.ui.group_theme import group_themes
from src.utils.utils import get_fitted_text_surface
from src.constants.constants import ASSETS

class AnimMode(Enum):
    SLIDE = 1
    POP = 2      # Scale up then down (1.0 -> 1.25 -> 1.0)
    SPAWN = 3    # Scale up from zero (0.0 -> 1.0)
    WIGGLE = 4

def draw_lewis_dots_on_surface(surface: pygame.Surface, width: int, height: int, open_dots: int, color: tuple[int, int, int] | tuple[int, int, int, int]):
    """Draws up to 8 valence dots in pairs directly onto an unrotated tile surface."""
    if open_dots <= 0:
        return

    dot_radius = max(2, width // 22)
    margin = max(6, width // 10)
    offset = max(5, width // 12)  # Distance between paired dots

    cx, cy = width // 2, height // 2

    # Coordinates for up to 8 dots (paired along top, right, bottom, left)
    positions = [
        # Top pair
        (cx - offset, margin),
        (cx + offset, margin),
        # Right pair
        (width - margin, cy - offset),
        (width - margin, cy + offset),
        # Bottom pair
        (cx - offset, height - margin),
        (cx + offset, height - margin),
        # Left pair
        (margin, cy - offset),
        (margin, cy + offset),
    ]

    for i in range(min(open_dots, len(positions))):
        pygame.draw.circle(surface, color, positions[i], dot_radius)

class AnimatedTile:
    def __init__(
        self,
        species: ChemicalSpecies,
        start_px: tuple[float, float],
        target_px: tuple[float, float],
        size: tuple[int, int],
        duration: float = 0.5,  # Slightly longer duration for smoother wiggle
        mode: AnimMode = AnimMode.SLIDE,
        loop: bool = False
    ):
        self.species = species
        self.theme = group_themes[species.category]
        self.start_x, self.start_y = start_px
        self.target_x, self.target_y = target_px
        
        self.current_x = float(start_px[0])
        self.current_y = float(start_px[1])
        
        self.width, self.height = size
        self.duration = duration
        self.mode = mode
        self.progress = 0.0
        self.scale = 1.0 if mode != AnimMode.SPAWN else 0.0
        self.angle = 0.0
        self.font_path = str(ASSETS / "fonts" / "Roboto" / "static" / "Roboto-SemiBold.ttf")
        self.loop = loop

        # Cache of the unrotated tile surface, keyed by the scale it was
        # built at. WIGGLE and SLIDE tiles hold scale == 1.0 for their
        # entire lifetime (only position/angle changes), so this lets a
        # continuously-looping wiggle skip re-rendering text/background
        # every frame and just rotate the same cached surface. POP/SPAWN
        # tiles change scale every frame, so they still rebuild, but they
        # only live for ~0.1-0.2s rather than looping indefinitely.
        self._cached_scale_key: float | None = None
        self._cached_tile_surf: pygame.Surface | None = None

    def update(self, dt: float) -> None:
        self.progress += dt / self.duration

        if self.progress >= 1.0:
            if self.loop:
                # Wrap progress back around for seamless looping
                self.progress %= 1.0
            else: 
                self.progress = 1.0
                self.current_x = float(self.target_x)
                self.current_y = float(self.target_y)
                self.scale = 1.0
                self.angle = 0.0
                return
            
        if self.mode == AnimMode.WIGGLE:
            # Keep tile centered at start position without moving current_x
            self.current_x = self.start_x
            self.current_y = self.start_y
            
            # Pure angular rotation around center (e.g. ±6 degrees)
            self.angle = math.sin(self.progress * math.pi * 2) * 6.0
            return

        # 1. Update Position
        self.current_x = self.start_x + (self.target_x - self.start_x) * self.progress
        self.current_y = self.start_y + (self.target_y - self.start_y) * self.progress

        # 2. Update Scale based on Animation Mode
        if self.mode == AnimMode.POP:
            self.scale = 1.0 + 0.25 * math.sin(self.progress * math.pi)

        elif self.mode == AnimMode.SPAWN:
            self.scale = self.progress

    @property
    def is_finished(self) -> bool:
        return not self.loop and self.progress >= 1.0

    def _build_tile_surf(self, w: int, h: int) -> pygame.Surface:
        """Renders the unrotated tile (background + text + dots) at the
        given pixel size. This is the expensive part (surface alloc, a
        rect draw, a cached-but-still-blitted text surface, and possibly
        a smoothscale) so callers should cache the result whenever scale
        hasn't changed since the last frame."""
        tile_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        bg_color = self.theme.background_color
        scaled_radius = int(self.theme.border_radius * self.scale)
        pygame.draw.rect(tile_surf, bg_color, (0, 0, w, h), border_radius=scaled_radius)

        if self.scale > 0.3:
            padded_max_w = int(self.width * 0.8)
            padded_max_h = int(self.height * 0.8)
            fitted_surf = get_fitted_text_surface(
                text=self.species.formula,
                font_path=self.font_path,
                max_w=padded_max_w,
                max_h=padded_max_h,
                color=self.theme.text_color,
                max_font_size=24
            )

            if self.scale != 1.0:
                scaled_w = max(1, int(fitted_surf.get_width() * self.scale))
                scaled_h = max(1, int(fitted_surf.get_height() * self.scale))
                fitted_surf = pygame.transform.smoothscale(fitted_surf, (scaled_w, scaled_h))

            text_rect = fitted_surf.get_rect(center=(w // 2, h // 2))
            tile_surf.blit(fitted_surf, text_rect)

            open_dots = getattr(self.species, "open_dots", 0)
            if open_dots > 0:
                draw_lewis_dots_on_surface(tile_surf, w, h, open_dots, self.theme.text_color)

        return tile_surf

    def draw(self, surface: pygame.Surface) -> None:
            w = int(self.width * self.scale)
            h = int(self.height * self.scale)

            if w <= 0 or h <= 0:
                return

            # 1. Reuse the unrotated tile surface when scale hasn't moved
            # since last frame (always true for WIGGLE/SLIDE, which hold
            # scale == 1.0 for their whole life). Only POP/SPAWN, whose
            # scale changes every frame, pay for a rebuild each time -
            # and those only run for ~0.1-0.2s.
            scale_key = round(self.scale, 3)
            if self._cached_tile_surf is not None and self._cached_scale_key == scale_key:
                tile_surf = self._cached_tile_surf
            else:
                tile_surf = self._build_tile_surf(w, h)
                self._cached_tile_surf = tile_surf
                self._cached_scale_key = scale_key

            # 2. Lock center to current animated position on screen (enables slide movement)
            center_x = int(self.current_x + self.width / 2)
            center_y = int(self.current_y + self.height / 2)

            # 3. Rotate surface (Pygame expands tile_surf bounding box).
            # Skip entirely when angle is 0 (the common case outside of
            # wiggling) since rotate() would just allocate an identical copy.
            if self.angle != 0.0:
                blit_surf = pygame.transform.rotate(tile_surf, self.angle)
            else:
                blit_surf = tile_surf

            # 4. Re-center onto current_x/current_y center
            rect = blit_surf.get_rect(center=(center_x, center_y))

            surface.blit(blit_surf, rect)