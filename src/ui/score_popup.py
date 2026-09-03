"""A small floating "+N" text that rises and fades out. Purely visual
feedback triggered whenever the player actually earns points (tapping a
finished compound, or a temporary compound auto-clearing)."""
import pygame
from src.constants.constants import ASSETS

_FONT_PATH = str(ASSETS / "fonts" / "Roboto" / "static" / "Roboto-SemiBold.ttf")
_RISE_PX = 36  # total distance the text drifts upward over its lifetime
_COLOR = (255, 214, 64)  # warm gold, reads clearly over any tile color


class ScorePopup:
    def __init__(self, points: int, center_px: tuple[float, float], duration: float = 0.8):
        self.points = points
        self.start_x, self.start_y = center_px
        self.duration = duration
        self.progress = 0.0
        self._font = pygame.font.Font(_FONT_PATH, 20)
        self._base_surf = self._font.render(f"+{points}", True, _COLOR)

    def update(self, dt: float) -> None:
        self.progress = min(1.0, self.progress + dt / self.duration)

    @property
    def is_finished(self) -> bool:
        return self.progress >= 1.0

    def draw(self, surface: pygame.Surface) -> None:
        # Ease-out rise: fast at first, settling near the top of its arc.
        eased = 1 - (1 - self.progress) ** 2
        y = self.start_y - _RISE_PX * eased

        # Fade out over the back half of the animation.
        alpha = 255 if self.progress < 0.5 else int(255 * (1 - (self.progress - 0.5) / 0.5))
        alpha = max(0, min(255, alpha))

        frame = self._base_surf.copy()
        frame.set_alpha(alpha)
        surface.blit(frame, frame.get_rect(center=(self.start_x, y)))
