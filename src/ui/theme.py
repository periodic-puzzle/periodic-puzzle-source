from dataclasses import dataclass
RGB_Tuple = tuple[int, int, int]
RGBA_Tuple = tuple[int, int, int, int]
@dataclass()
class Theme:
    background_color: RGB_Tuple | RGBA_Tuple = (255, 255, 255)
    text_color: RGB_Tuple | RGBA_Tuple = (0, 0, 0)
    font_size: int = 24
    border_radius: int = 0
    # Optional outline, drawn on top of the fill. Needed for light tiles
    # (e.g. white cards) sitting on a similarly light page background,
    # where the fill color alone doesn't give enough contrast to read as
    # a distinct, tappable shape.
    border_color: RGB_Tuple | RGBA_Tuple | None = None
    border_width: int = 0

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

# Warm, high-contrast banner used for transient announcements (tier
# unlocks, reaction chains, etc.) so they read as "news" rather than
# blending in with the rest of the neutral-gray UI.
ToastTheme = HoverableTheme(
    background_color=(255, 214, 64),
    hover_color=(255, 214, 64),
    text_color=(60, 45, 0),
    font_size=20,
    border_radius=12,
)

# Accent theme for the restart button on the game-over panel, so it reads
# as the clear "next action" rather than another gray button.
RestartButtonTheme = ClickableTheme(
    background_color=(110, 205, 185),
    text_color=(255, 255, 255),
    hover_color=(135, 220, 200),
    pressed_color=(90, 180, 160),
    font_size=22,
    border_radius=10,
)

# Warm page background shared by the quiz-style gamemodes (naming,
# balancing) so text elements can blend into the page instead of sitting
# in a flat gray box.
PAGE_BACKGROUND: RGB_Tuple = (245, 241, 232)

# Soft white "card" used for tappable tiles (equation terms, multiple
# choice options) so they read as distinct pieces against the warm page
# background, instead of the same flat gray as everything else. White on
# the warm cream background alone is too close in tone to read as a
# separate shape, so it gets a visible border rather than relying on
# fill color contrast.
CardTheme = ClickableTheme(
    background_color=(255, 255, 255),
    text_color=(45, 45, 55),
    hover_color=(232, 240, 250),
    pressed_color=(210, 222, 238),
    font_size=22,
    border_radius=12,
    border_color=(205, 210, 220),
    border_width=2,
)

# Muted stepper buttons (+/-) that sit next to a CardTheme value without
# competing with it for attention. Like CardTheme, the light fill alone
# is too close in tone to the warm page background to read as a button,
# so it gets the same visible border.
StepperTheme = ClickableTheme(
    background_color=(225, 229, 236),
    text_color=(70, 75, 90),
    hover_color=(210, 216, 226),
    pressed_color=(190, 197, 210),
    font_size=20,
    border_radius=8,
    border_color=(190, 196, 208),
    border_width=2,
)

# Positive/negative verdict banners, shared by any quiz-style gamemode to
# report whether the player's answer was correct. These are assigned to
# both TextBox.theme (HoverableTheme) and Button.theme (ClickableTheme,
# e.g. highlighting an answer tile) — defined as ClickableTheme so both
# assignments type-check, even though the pressed_color is never actually
# reached in practice (the elements are disabled while these are shown).
CorrectTheme = ClickableTheme(
    background_color=(150, 215, 165),
    hover_color=(150, 215, 165),
    pressed_color=(150, 215, 165),
    text_color=(20, 90, 45),
    font_size=20,
    border_radius=10,
)

IncorrectTheme = ClickableTheme(
    background_color=(240, 170, 170),
    hover_color=(240, 170, 170),
    pressed_color=(240, 170, 170),
    text_color=(120, 25, 25),
    font_size=20,
    border_radius=10,
)

# Plain text sitting directly on the page background (no visible box),
# used for titles and passive hints.
TitleTheme = HoverableTheme(
    background_color=PAGE_BACKGROUND,
    hover_color=PAGE_BACKGROUND,
    text_color=(40, 40, 45),
    font_size=24,
)

HintTheme = HoverableTheme(
    background_color=PAGE_BACKGROUND,
    hover_color=PAGE_BACKGROUND,
    text_color=(120, 115, 105),
    font_size=18,
)