import json
import os
import hashlib
import uuid
import sys
from typing import TypedDict, TYPE_CHECKING, Any, Literal
from pathlib import Path

if TYPE_CHECKING:
    # Pylance will read this section, but Python will skip it at runtime
    localStorage: Any
    IS_WEB: Literal[False]
else:
    try:
        from js import localStorage
        IS_WEB = True
    except ImportError:
        localStorage = None
        IS_WEB = False


save_dir = Path(os.environ["APPDATA"]) / "Periodic Puzzle"
save_dir.mkdir(parents=True, exist_ok=True)
SAVE_KEY = "highscores_data"
SAVE_FILE = "highscores.json"
SECRET_SALT = "PeriodicPuzzleSecretSalt10910(!)#*"


class SaveJson(TypedDict):
    sliding_high_score: int
    balancing_high_streak: int
    naming_high_streak: int
    molar_mass_high_streak: int
    checksum: str


def get_machine_id() -> str:
    """Returns persistent browser UUID on Web, or hardware MAC on EXE."""
    if IS_WEB and localStorage:
        web_id = localStorage.getItem("user_client_id")
        if not web_id:
            web_id = str(uuid.uuid4())
            localStorage.setItem("user_client_id", web_id)
        return str(web_id)
    
    return str(uuid.getnode())

def _read_save_raw() -> str | None:
    """Reads save data from localStorage on Web, or highscores.json on Desktop."""
    if IS_WEB and localStorage:
        return localStorage.getItem("highscores_data")
    
    if not os.path.exists(save_dir / SAVE_FILE):
        return None
    try:
        with open(save_dir / SAVE_FILE, "r") as f:
            return f.read()
    except OSError:
        return None
    
def _write_to_disk(data: SaveJson) -> None:
    """Writes JSON save string to disk (EXE) or localStorage (Web)."""
    json_str = json.dumps(data, indent=4)
    if IS_WEB:
        localStorage.setItem(SAVE_KEY, json_str)
    else:
        try:
            with open(save_dir / SAVE_FILE, "w") as f:
                f.write(json_str)
        except OSError as e:
            print(f"Failed to save high scores: {e}")


def calculate_checksum(sliding: int, balancing: int, naming: int, molar_mass: int) -> str:
    """Calculates SHA-256 checksum across all modes combined with the local Machine ID."""
    machine_id = get_machine_id()
    raw_str = f"{sliding}-{balancing}-{naming}-{molar_mass}-{SECRET_SALT}-{machine_id}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


def load_high_scores() -> SaveJson:
    """Loads high scores from disk (EXE) or localStorage (Web). Upgrades older formats automatically."""
    default_data: SaveJson = {
        "sliding_high_score": 0,
        "balancing_high_streak": 0,
        "naming_high_streak": 0,
        "molar_mass_high_streak": 0,
        "checksum": calculate_checksum(0, 0, 0, 0),
    }

    # Fetch raw JSON string from web or disk
    raw_save = _read_save_raw()
    if not raw_save:
        return default_data

    try:
        data = json.loads(raw_save)

        sliding = data.get("sliding_high_score", 0)
        balancing = data.get("balancing_high_streak", 0)
        naming = data.get("naming_high_streak", 0)
        molar_mass = data.get("molar_mass_high_streak", 0)

        # Validate against the current machine/browser checksum
        expected_checksum = calculate_checksum(sliding, balancing, naming, molar_mass)
        if data.get("checksum") != expected_checksum:
            print("Warning: Save file invalid, corrupted, or transferred from another device! Resetting.")
            return default_data

        return {
            "sliding_high_score": sliding,
            "balancing_high_streak": balancing,
            "naming_high_streak": naming,
            "molar_mass_high_streak": molar_mass,
            "checksum": expected_checksum,
        }

    except (json.JSONDecodeError, OSError):
        return default_data


def save_high_score(mode: str, new_score: int) -> None:
    """Saves a score for 'sliding', 'balancing', 'naming', or 'molar_mass' mode."""
    data = load_high_scores()

    if mode == "sliding":
        if new_score > data["sliding_high_score"]:
            data["sliding_high_score"] = new_score
    elif mode == "balancing":
        if new_score > data["balancing_high_streak"]:
            data["balancing_high_streak"] = new_score
    elif mode == "naming":
        if new_score > data["naming_high_streak"]:
            data["naming_high_streak"] = new_score
    elif mode == "molar_mass":
        if new_score > data["molar_mass_high_streak"]:
            data["molar_mass_high_streak"] = new_score
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Recalculate checksum across all 4 modes using local machine hardware ID
    data["checksum"] = calculate_checksum(
        data["sliding_high_score"],
        data["balancing_high_streak"],
        data["naming_high_streak"],
        data["molar_mass_high_streak"],
    )

    _write_to_disk(data)