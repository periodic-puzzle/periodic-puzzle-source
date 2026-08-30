import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.chemistry.species import ChemicalSpecies
def parse_rgb(rgb: str) -> tuple[int, int, int]:
    if not rgb.startswith("rgb(") or not rgb.endswith(")"):
        raise ValueError("Expected format: rgb(r, g, b)")

    values = tuple(int(v.strip()) for v in rgb[4:-1].split(","))

    if len(values) != 3:
        raise ValueError("RGB must have exactly 3 values")

    if not all(0 <= v <= 255 for v in values):
        raise ValueError("RGB values must be between 0 and 255")

    return values

_TEXT_SURFACE_CACHE: dict[tuple[str, str, int, int, tuple[int, int, int] | tuple[int, int, int, int]], pygame.Surface] = {}

def get_fitted_text_surface(
    text: str,
    font_path: str,
    max_w: int,
    max_h: int,
    color: tuple[int, int, int] | tuple[int, int, int, int],
    max_font_size: int = 24,
    min_font_size: int = 8
) -> pygame.Surface:
    """Returns a pre-rendered text surface cached by parameters, scaled to fit within max_w and max_h."""
    cache_key = (text, font_path, max_w, max_h, color)
    if cache_key in _TEXT_SURFACE_CACHE:
        return _TEXT_SURFACE_CACHE[cache_key]

    padding = 8  # Safe padding inside cell
    target_w = max(1, max_w - padding)
    target_h = max(1, max_h - padding)

    best_surf = None
    for size in range(max_font_size, min_font_size - 1, -1):
        font = pygame.font.Font(font_path, size)
        w, h = font.size(text)
        if w <= target_w and h <= target_h:
            best_surf = font.render(text, True, color)
            break

    # Fallback to minimum size scaled down if text is extremely long
    if best_surf is None:
        font = pygame.font.Font(font_path, min_font_size)
        raw_surf = font.render(text, True, color)
        scale = min(target_w / raw_surf.get_width(), target_h / raw_surf.get_height())
        new_size = (max(1, int(raw_surf.get_width() * scale)), max(1, int(raw_surf.get_height() * scale)))
        best_surf = pygame.transform.smoothscale(raw_surf, new_size)

    _TEXT_SURFACE_CACHE[cache_key] = best_surf
    return best_surf

from random import choices

def weighted_choice(species: list["ChemicalSpecies"]):
    return choices(
        species,
        weights=[getattr(x, "spawn_weight", 0) for x in species],
        k=1
    )[0]

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def render_symbol(symbol: str, font_size: int = 24, color=(0, 0, 0)) -> pygame.Surface:
    """Renders arrows or special symbols using system fonts that support Unicode."""
    # SysFont falls back to default system fonts like Arial/Segoe UI
    sys_font = pygame.font.SysFont("arial", font_size)
    return sys_font.render(symbol, True, color)