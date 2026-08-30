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

def _wrap_lines(text: str, font: pygame.font.Font, max_line_w: int) -> list[str]:
    """Greedily wraps text on word boundaries so each line fits within max_line_w."""
    words = text.split(" ")
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_line_w or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

def get_fitted_text_surface(
    text: str,
    font_path: str,
    max_w: int,
    max_h: int,
    color: tuple[int, int, int] | tuple[int, int, int, int],
    max_font_size: int = 24,
    min_font_size: int = 8
) -> pygame.Surface:
    """Returns a pre-rendered text surface, cached by parameters, wrapped and
    scaled to fit within max_w and max_h at the largest font size that fits."""
    cache_key = (text, font_path, max_w, max_h, color)
    if cache_key in _TEXT_SURFACE_CACHE:
        return _TEXT_SURFACE_CACHE[cache_key]

    padding = 8  # Safe padding inside cell
    target_w = max(1, max_w - padding)
    target_h = max(1, max_h - padding)

    best_surf = None
    for size in range(max_font_size, min_font_size - 1, -1):
        font = pygame.font.Font(font_path, size)
        lines = _wrap_lines(text, font, target_w)
        line_h = font.get_linesize()
        total_h = line_h * len(lines)
        widest_line = max((font.size(line)[0] for line in lines), default=0)

        if widest_line <= target_w and total_h <= target_h:
            surf = pygame.Surface((target_w, total_h), pygame.SRCALPHA)
            for i, line in enumerate(lines):
                line_surf = font.render(line, True, color)
                surf.blit(line_surf, line_surf.get_rect(centerx=target_w // 2, top=i * line_h))
            best_surf = surf
            break

    # Fallback: render at minimum size (wrapped) and scale the whole block
    # down further if it's still too big — keeps extremely long text legible
    # rather than clipped, at the cost of going below min_font_size.
    if best_surf is None:
        font = pygame.font.Font(font_path, min_font_size)
        lines = _wrap_lines(text, font, target_w)
        line_h = font.get_linesize()
        total_h = line_h * len(lines)
        widest_line = max((font.size(line)[0] for line in lines), default=1)

        raw_surf = pygame.Surface((widest_line, total_h), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, color)
            raw_surf.blit(line_surf, line_surf.get_rect(centerx=widest_line // 2, top=i * line_h))

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