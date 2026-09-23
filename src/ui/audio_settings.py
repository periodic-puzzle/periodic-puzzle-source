"""A small audio settings control: a speaker icon that toggles mute, and
(in "full" mode) a draggable volume slider next to it.

This does NOT go through UIManager. UIManager's click/hover system never
hands an element the actual mouse position (Button only needs to know
"was I clicked", not "where exactly"), which is fine for buttons but not
enough to drag a slider knob. So this widget gets raw pygame events
directly from its owning context, the same way SlidingCtx already
handles swipe gestures manually alongside self.ui.

Usage:
    self.audio_widget = AudioSettingsWidget((GAME_WIDTH - 40, 10))       # compact
    self.audio_widget = AudioSettingsWidget((GAME_WIDTH - 200, 10), compact=False)  # full

    # in handle_event, BEFORE other event handling that might also
    # react to a click in the same screen area:
    if self.audio_widget.handle_event(event):
        return

    # in render, after everything else:
    self.audio_widget.draw(target_surface)
"""
from __future__ import annotations

import pygame

from src.audio.sfx import sfx

# Virtual game resolution: matches GAME_WIDTH/GAME_HEIGHT used everywhere
# else, needed here to replicate UIManager's mouse-position scaling since
# this widget reads raw events instead of going through UIManager.
_VIRTUAL_W, _VIRTUAL_H = 600, 600

_ICON_COLOR = (90, 90, 100)
_ICON_HOVER = (50, 50, 60)
_TRACK_COLOR = (215, 218, 224)
_FILL_COLOR = (120, 180, 245)
_KNOB_COLOR = (255, 255, 255)
_KNOB_BORDER = (120, 180, 245)


def _virtual_mouse_pos(pos: tuple[int, int]) -> tuple[int, int]:
    """Mirrors UIManager.process_event's window->virtual-space scaling
    so this widget lines up with the rest of the UI on any window size."""
    display_surf = pygame.display.get_surface()
    if not display_surf:
        return pos
    win_w, win_h = display_surf.get_size()
    if win_w == 0 or win_h == 0:
        return pos
    return (
        int(pos[0] * _VIRTUAL_W / win_w),
        int(pos[1] * _VIRTUAL_H / win_h),
    )


class AudioSettingsWidget:
    def __init__(self, topleft: tuple[int, int], compact: bool = True) -> None:
        self.compact = compact
        icon_size = 28
        x, y = topleft

        self.icon_rect = pygame.Rect(x, y, icon_size, icon_size)

        if compact:
            self.slider_rect: pygame.Rect | None = None
        else:
            slider_x = self.icon_rect.right + 12
            slider_w = 110
            self.slider_rect = pygame.Rect(slider_x, y + icon_size // 2 - 3, slider_w, 6)

        self._dragging_slider = False
        self._icon_hovered = False

    # -- geometry ------------------------------------------------------
    @property
    def bounding_rect(self) -> pygame.Rect:
        if self.slider_rect is None:
            return self.icon_rect
        return self.icon_rect.union(self.slider_rect.inflate(0, 20))

    def _knob_x(self) -> float:
        assert self.slider_rect is not None
        vol = 0.0 if sfx.muted else sfx.master_volume
        return self.slider_rect.x + vol * self.slider_rect.width

    def _set_volume_from_x(self, x: float) -> None:
        assert self.slider_rect is not None
        ratio = (x - self.slider_rect.x) / max(1, self.slider_rect.width)
        ratio = max(0.0, min(1.0, ratio))
        if sfx.muted and ratio > 0:
            sfx.set_muted(False)
        sfx.set_master_volume(ratio)

    # -- events ----------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if this widget consumed the event, so the caller
        can skip feeding it to anything else underneath."""
        if event.type == pygame.MOUSEMOTION:
            pos = _virtual_mouse_pos(event.pos)
            self._icon_hovered = self.icon_rect.collidepoint(pos)
            if self._dragging_slider and self.slider_rect is not None:
                self._set_volume_from_x(pos[0])
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = _virtual_mouse_pos(event.pos)
            if self.icon_rect.collidepoint(pos):
                sfx.toggle_mute()
                if not sfx.muted:
                    sfx.play("ui_click")
                return True
            if self.slider_rect is not None:
                grab_zone = self.slider_rect.inflate(6, 14)
                if grab_zone.collidepoint(pos):
                    self._dragging_slider = True
                    self._set_volume_from_x(pos[0])
                    return True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_slider:
                self._dragging_slider = False
                return True
            return False

        return False

    # -- drawing ---------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_speaker_icon(surface)
        if self.slider_rect is not None:
            self._draw_slider(surface)

    def _draw_speaker_icon(self, surface: pygame.Surface) -> None:
        r = self.icon_rect
        color = _ICON_HOVER if self._icon_hovered else _ICON_COLOR

        # Speaker body: a small rectangle (the driver) + a triangle (the
        # cone), drawn as one polygon so there's no seam between them.
        cx, cy = r.centerx - 4, r.centery
        body_w, body_h = 7, 10
        points = [
            (cx - body_w, cy - body_h // 2),
            (cx - 2, cy - body_h // 2),
            (cx + 8, cy - r.height // 2 + 2),
            (cx + 8, cy + r.height // 2 - 2),
            (cx - 2, cy + body_h // 2),
            (cx - body_w, cy + body_h // 2),
        ]
        pygame.draw.polygon(surface, color, points)

        muted = sfx.muted or sfx.master_volume <= 0.001

        if muted:
            # Slash through the icon rather than sound-wave arcs.
            pygame.draw.line(
                surface, color,
                (r.left + 3, r.top + 3), (r.right - 3, r.bottom - 3), width=3,
            )
        else:
            # One or two small arcs to the right of the cone, sized by
            # how loud the volume currently is.
            n_waves = 1 if sfx.master_volume < 0.5 else 2
            for i in range(n_waves):
                radius = 6 + i * 5
                arc_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
                arc_rect.center = (cx + 6, cy)
                pygame.draw.arc(
                    surface, color, arc_rect,
                    -0.6, 0.6, width=2,
                )

    def _draw_slider(self, surface: pygame.Surface) -> None:
        assert self.slider_rect is not None
        track = self.slider_rect

        pygame.draw.rect(surface, _TRACK_COLOR, track, border_radius=3)

        vol = 0.0 if sfx.muted else sfx.master_volume
        fill_w = int(track.width * vol)
        if fill_w > 0:
            fill_rect = pygame.Rect(track.x, track.y, fill_w, track.height)
            pygame.draw.rect(surface, _FILL_COLOR, fill_rect, border_radius=3)

        knob_x = int(self._knob_x())
        knob_radius = 8 if self._dragging_slider else 7
        pygame.draw.circle(surface, _KNOB_COLOR, (knob_x, track.centery), knob_radius)
        pygame.draw.circle(surface, _KNOB_BORDER, (knob_x, track.centery), knob_radius, width=2)
