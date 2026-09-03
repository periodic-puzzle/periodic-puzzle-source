import json
import os
import hashlib
import uuid
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


save_dir = Path(os.environ.get("APPDATA", Path.home())) / "Periodic Puzzle"
save_dir.mkdir(parents=True, exist_ok=True)
SAVE_KEY = "highscores_data"
SAVE_FILE = "highscores.json"
SECRET_SALT = "PeriodicPuzzleSecretSalt10910(!)#*"


class SaveJson(TypedDict):
    sliding_high_score: int
    balancing_high_streak: int
    naming_high_streak: int
    periodic_trends_high_streak: int
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
        return localStorage.getItem(SAVE_KEY)
    
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


def calculate_checksum(sliding: int, balancing: int, naming: int, periodic_trends: int) -> str:
    """Calculates SHA-256 checksum across active modes combined with the local Machine ID."""
    machine_id = get_machine_id()
    raw_str = f"{sliding}-{balancing}-{naming}-{periodic_trends}-{SECRET_SALT}-{machine_id}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


def calculate_legacy_checksum(sliding: int, balancing: int, naming: int, molar_mass: int) -> str:
    """Calculates legacy SHA-256 checksum for backward compatibility migration."""
    machine_id = get_machine_id()
    raw_str = f"{sliding}-{balancing}-{naming}-{molar_mass}-{SECRET_SALT}-{machine_id}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


def load_high_scores() -> SaveJson:
    """Loads high scores from disk (EXE) or localStorage (Web). Automatically migrates legacy saves."""
    default_data: SaveJson = {
        "sliding_high_score": 0,
        "balancing_high_streak": 0,
        "naming_high_streak": 0,
        "periodic_trends_high_streak": 0,
        "checksum": calculate_checksum(0, 0, 0, 0),
    }

    raw_save = _read_save_raw()
    if not raw_save:
        return default_data

    try:
        data = json.loads(raw_save)

        sliding = data.get("sliding_high_score", 0)
        balancing = data.get("balancing_high_streak", 0)
        naming = data.get("naming_high_streak", 0)

        # 1. Check for legacy 'molar_mass_high_streak' key and attempt migration
        if "periodic_trends_high_streak" not in data and "molar_mass_high_streak" in data:
            legacy_molar = data.get("molar_mass_high_streak", 0)
            legacy_checksum = calculate_legacy_checksum(sliding, balancing, naming, legacy_molar)

            if data.get("checksum") == legacy_checksum:
                # Valid legacy file: Migrate score to periodic_trends_high_streak
                migrated_data: SaveJson = {
                    "sliding_high_score": sliding,
                    "balancing_high_streak": balancing,
                    "naming_high_streak": naming,
                    "periodic_trends_high_streak": legacy_molar,
                    "checksum": calculate_checksum(sliding, balancing, naming, legacy_molar),
                }
                _write_to_disk(migrated_data)
                return migrated_data

        # 2. Standard load for updated schema
        periodic_trends = data.get("periodic_trends_high_streak", 0)
        expected_checksum = calculate_checksum(sliding, balancing, naming, periodic_trends)

        if data.get("checksum") != expected_checksum:
            print("Warning: Save file invalid, corrupted, or transferred from another device! Resetting.")
            return default_data

        return {
            "sliding_high_score": sliding,
            "balancing_high_streak": balancing,
            "naming_high_streak": naming,
            "periodic_trends_high_streak": periodic_trends,
            "checksum": expected_checksum,
        }

    except (json.JSONDecodeError, OSError):
        return default_data


def save_high_score(mode: str, new_score: int) -> None:
    """Saves a score for 'sliding', 'balancing', 'naming', or 'periodic_trends' mode."""
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
    elif mode in ("periodic_trends", "periodic_trends_high_streak"):
        if new_score > data["periodic_trends_high_streak"]:
            data["periodic_trends_high_streak"] = new_score
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Recalculate checksum across all active modes
    data["checksum"] = calculate_checksum(
        data["sliding_high_score"],
        data["balancing_high_streak"],
        data["naming_high_streak"],
        data["periodic_trends_high_streak"],
    )

    _write_to_disk(data)