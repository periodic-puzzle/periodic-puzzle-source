from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
import inspect
from src.ui.theme import ClickableTheme, DefaultButtonTheme, DefaultTextboxTheme, HoverableTheme

import pygame
from src.utils.utils import get_fitted_text_surface
from src.constants.constants import ASSETS

EventCallback = Callable[..., None]


@dataclass(slots=True)
class Viewport:
    offset: pygame.Vector2 = field(default_factory=pygame.Vector2)
    scale: float = 1.0

    def to_virtual(self, pos: tuple[int, int]) -> tuple[int, int]:
        # Simple identity mapping when using pygame.SCALED
        return (
            int((pos[0] - self.offset.x) / self.scale),
            int((pos[1] - self.offset.y) / self.scale),
        )


class UIElement:
    def __init__(self, rect: pygame.Rect, id_: str | None = None):
        self.rect: pygame.Rect = rect

        self.visible: bool = True
        self.enabled: bool = True

        self.hovered: bool = False
        self.pressed: bool = False

        self._events: dict[str, list[EventCallback]] = {}
        self.id_ = id_

    def on(self, event_name: str, callback: EventCallback) -> None:
        self._events.setdefault(event_name, []).append(callback)
    
    def remove_callback(self, event_name: str):
        self._events[event_name] = []

    def emit(self, event_name: str, *args):
        for callback in self._events.get(event_name, []):
            params = inspect.signature(callback).parameters

            if len(params) == 0:
                callback()
            else:
                callback(self, *args)

    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError


class Button(UIElement):
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        theme: ClickableTheme = DefaultButtonTheme,
        padding: int = 0,
        id_: str | None  = None
    ):
        super().__init__(rect, id_)
        self.text: str = text
        self.font_path: str = str(ASSETS / "fonts" / "Roboto" / "static" / "Roboto-SemiBold.ttf")
        self.theme: ClickableTheme = theme
        self.padding = padding

    def draw(self, surface: pygame.Surface) -> None:
        if self.pressed:
            color = self.theme.pressed_color
        elif self.hovered:
            color = self.theme.hover_color
        else:
            color = self.theme.background_color

        pygame.draw.rect(
            surface,
            color,
            self.rect,
            border_radius=self.theme.border_radius,
        )

        if self.text:
            text_surf = get_fitted_text_surface(
                text=self.text,
                font_path=self.font_path,
                max_w=max(3, self.rect.width - self.padding),
                max_h=max(3, self.rect.height - self.padding),
                color=self.theme.text_color,
                max_font_size=self.theme.font_size
            )
            surface.blit(
                text_surf,
                text_surf.get_rect(center=self.rect.center),
            )


class TextBox(UIElement):
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        theme: HoverableTheme = DefaultTextboxTheme,
        padding: int = 0,
        id_: str | None  = None
    ):
        super().__init__(rect, id_)
        self.text: str = text
        self.font_path: str = str(ASSETS / "fonts" / "Roboto" / "static" / "Roboto-SemiBold.ttf")
        self.theme = theme
        self.padding = padding

    def draw(self, surface: pygame.Surface) -> None:
        if self.hovered:
            color = self.theme.hover_color
        else:
            color = self.theme.background_color

        pygame.draw.rect(
            surface,
            color,
            self.rect,
            border_radius=self.theme.border_radius,
        )

        if self.text:
            text_surf = get_fitted_text_surface(
                text=self.text,
                font_path=self.font_path,
                max_w=max(3, self.rect.width),
                max_h=max(3, self.rect.height),
                color=self.theme.text_color,
                max_font_size=self.theme.font_size
            )
            surface.blit(
                text_surf,
                text_surf.get_rect(center=self.rect.center),
            )


class UIManager:
    def __init__(self):
        self.elements: list[UIElement] = []
        self._id_map: dict[str, UIElement] = {}  # Fast dictionary lookup

        self.hovered: UIElement | None = None
        self.pressed: UIElement | None = None

        self.viewport = Viewport()

    def set_viewport(
        self,
        offset: tuple[float, float] | pygame.Vector2,
        scale: float,
    ) -> None:
        self.viewport.offset = pygame.Vector2(offset)
        self.viewport.scale = scale

    def add(self, element: UIElement) -> UIElement:
        self.elements.append(element)
        if element.id_:
            if element.id_ in self._id_map:
                raise ValueError(f"UI Element with ID '{element.id_}' already exists.")
            self._id_map[element.id_] = element
        return element  # Returning the element allows inline assignment

    def remove(self, element: UIElement) -> None:
        if element in self.elements:
            self.elements.remove(element)
        if element.id_ and element.id_ in self._id_map:
            del self._id_map[element.id_]

    def get_by_id(self, id_: str) -> UIElement | None:
        # Fast O(1) dictionary access
        return self._id_map.get(id_)

    def __getattr__(self, name: str) -> UIElement:
        """
        Allows convenient direct attribute access:
        e.g., ui_manager.my_button instead of ui_manager.get_by_id("my_button")
        """
        if name in self._id_map:
            return self._id_map[name]
        raise AttributeError(f"'UIManager' object has no attribute or ID '{name}'")
    def process_event(self, event: pygame.event.Event) -> None:
        if event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            # Fetch current window/canvas dimensions dynamically
            display_surf = pygame.display.get_surface()
            if display_surf:
                win_w, win_h = display_surf.get_size()
                # Scale mouse position from window size back to 600x600 virtual space
                scale_x = 600 / win_w
                scale_y = 600 / win_h
                
                raw_pos = event.pos
                virtual_pos = (
                    int(raw_pos[0] * scale_x),
                    int(raw_pos[1] * scale_y)
                )
            else:
                virtual_pos = event.pos

            event = pygame.event.Event(
                event.type,
                {
                    **event.dict,
                    "pos": virtual_pos,
                },
            )

        if event.type == pygame.MOUSEMOTION:
            new_hover: UIElement | None = None

            for element in reversed(self.elements):
                if (
                    element.visible
                    and element.enabled
                    and element.rect.collidepoint(event.pos)
                ):
                    new_hover = element
                    break

            if new_hover is not self.hovered:
                if self.hovered is not None:
                    self.hovered.hovered = False
                    self.hovered.emit("leave")

                self.hovered = new_hover

                if self.hovered is not None:
                    self.hovered.hovered = True
                    self.hovered.emit("hover")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hovered is not None:
                self.pressed = self.hovered
                self.pressed.pressed = True
                self.pressed.emit("press")

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.pressed is not None:
                self.pressed.pressed = False
                self.pressed.emit("release")

                if self.pressed is self.hovered:
                    self.pressed.emit("click")

                self.pressed = None

    def draw(self, surface: pygame.Surface) -> None:
        for element in self.elements:
            if element.visible:
                element.draw(surface)