from src.ui.theme import ClickableTheme
from src.utils.utils import parse_rgb
from typing import Literal, TYPE_CHECKING
from src.chemistry.species import Category

themes: dict[Category, dict[Literal["color", "text_color"], str]] = {
    Category.ALKALI_METAL: {
        "color": "rgb(255, 110, 108)"
    },
    Category.ALKALINE_EARTH_METAL: {
        "color": "rgb(255, 175, 95)"
    },
    Category.TRANSITION_METAL: {
        "color": "rgb(120, 180, 245)"
    },
    Category.POST_TRANSITION_METAL: {
        "color": "rgb(110, 205, 185)"
    },
    Category.METALLOID: {
        "color": "rgb(130, 200, 140)"
    },
    Category.CARBON_GROUP: {
        "color": "rgb(160, 210, 130)"
    },
    Category.PNICTOGEN: {
        "color": "rgb(190, 215, 110)"
    },
    Category.CHALCOGEN: {
        "color": "rgb(235, 215, 95)"
    },
    Category.HALOGEN: {
        "color": "rgb(185, 140, 245)"
    },
    Category.NOBLE_GAS: {
        "color": "rgb(95, 215, 235)"
    },
    Category.LANTHANIDE: {
        "color": "rgb(245, 140, 195)"
    },
    Category.ACTINIDE: {
        "color": "rgb(215, 120, 175)"
    },
    Category.NEUTRAL_COMPOUND: {
        "color": "rgb(180, 190, 200)"
    },
    Category.POLYATOMIC_ANION: {
        "color": "rgb(170, 110, 220)"
    },
    Category.INTERMEDIATE: {
        "color": "rgb(150, 90, 200)"
    },
    Category.POLYATOMIC_CATION: {
        "color": "rgb(235, 130, 80)"
    },
    Category.ACID: {
        "color": "rgb(220, 50, 60)"     # Vibrant Crimson Red
    },
    Category.SALT: {
        "color": "rgb(230, 235, 240)",   # Golden Mineral / Sand
        "text_color": "rgb(0, 0, 0)"     # Dark text for light tile
    },
    Category.BASE : {
        "color": "rgb(83, 80, 235)"
    },
    Category.HYDROCARBON : {
        "color": "rgb(50, 50, 50)"
    },
    Category.HYDROGEN : {
        "color": "rgb(175, 225, 245)"
    },
    Category.OXOACID: {
        "color": "rgb(225, 90, 120)"
    },
    Category.ORGANIC_RADICAL: {
        "color": "rgb(170, 90, 180)"
    },
    Category.PEROXIDE: {
        "color": "rgb(245, 160, 90)"
    },
    Category.HYDRIDE: {
        "color": "rgb(80, 200, 220)"
    },
    Category.ACID_ANHYDRIDE: {
        "color": "rgb(240, 140, 100)"
    },
    Category.ALCOHOL: {
        "color": "rgb(230, 110, 150)"
    },
    Category.ALDEHYDE: {
        "color": "rgb(240, 120, 90)"  # Warm Coral / Terracotta
    },
}

def clamp(x: int, min_: int, max_: int):
    return max(min_, min(x, max_))

group_themes: dict[Category, ClickableTheme] = {}
for key, obj in themes.items():
    rgb_tuple = parse_rgb(obj["color"])
    text_color = parse_rgb(obj.get("text_color", "rgb(255, 255, 255)"))
    group_themes[key] = ClickableTheme(
        background_color=rgb_tuple,
        text_color=text_color,
        font_size=24,
        hover_color=(
            clamp(rgb_tuple[0] + 25, 0, 255),
            clamp(rgb_tuple[1] + 25, 0, 255),
            clamp(rgb_tuple[2] + 25, 0, 255)
        ),
        border_radius=8
    )