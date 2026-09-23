"""Tiny persistence layer for audio preferences.

Deliberately separate from save_manager.py: high scores go through a
checksum to resist tampering, but there's no reason to punish someone
for editing their own volume setting, so this is just a plain JSON
blob (or localStorage entry on web) with no integrity check.
"""
from __future__ import annotations

import json

from src.utils.save_manager import IS_WEB, localStorage, save_dir

SETTINGS_KEY = "audio_settings"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "muted": False,
    "volume": 1.0,
}


def _read_raw() -> str | None:
    if IS_WEB and localStorage:
        return localStorage.getItem(SETTINGS_KEY)

    path = save_dir / SETTINGS_FILE
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return f.read()
    except OSError:
        return None


def _write_raw(data: dict) -> None:
    json_str = json.dumps(data)
    if IS_WEB and localStorage:
        localStorage.setItem(SETTINGS_KEY, json_str)
        return
    try:
        with open(save_dir / SETTINGS_FILE, "w") as f:
            f.write(json_str)
    except OSError as e:
        print(f"[settings] failed to save: {e}")


def load_audio_settings() -> dict:
    """Returns {"muted": bool, "volume": float}. Falls back to defaults
    on any missing/corrupt data instead of raising."""
    raw = _read_raw()
    if not raw:
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(raw)
        muted = bool(data.get("muted", DEFAULT_SETTINGS["muted"]))
        volume = float(data.get("volume", DEFAULT_SETTINGS["volume"]))
        volume = max(0.0, min(1.0, volume))
        return {"muted": muted, "volume": volume}
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(DEFAULT_SETTINGS)


def save_audio_settings(muted: bool, volume: float) -> None:
    _write_raw({"muted": muted, "volume": max(0.0, min(1.0, volume))})
