from dataclasses import dataclass
RGB_Tuple = tuple[int, int, int]
RGBA_Tuple = tuple[int, int, int, int]
@dataclass()
class Theme:
    background_color: RGB_Tuple | RGBA_Tuple = (255, 255, 255)
    text_color: RGB_Tuple | RGBA_Tuple = (0, 0, 0)
    font_size: int = 24
    border_radius: int = 0

@dataclass()
class HoverableTheme(Theme):
    hover_color: RGB_Tuple | RGBA_Tuple = (200, 200, 200)

@dataclass()
class ClickableTheme(HoverableTheme):
    pressed_color: RGB_Tuple | RGBA_Tuple = (180, 180, 180)
    
DefaultButtonTheme = ClickableTheme(
    background_color=(145, 145, 145),
    text_color=(255,255,255),
    hover_color=(170, 170, 170),
    pressed_color=(120, 120, 120),
    font_size=24,
    border_radius=8
)

DefaultTextboxTheme = HoverableTheme(
    background_color=(140,140,140),
    hover_color=(140,140,140),
    text_color=(255,255,255)
)