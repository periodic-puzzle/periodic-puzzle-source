"""Central sound-effect manager.

Design goals:
  * Never crash the game if the mixer is unavailable (some web/pygbag
    builds, headless CI, machines with no audio device) or if a sound
    file simply hasn't been added yet -- every failure degrades to
    silence and a single warning.
  * One flat name -> filename table, so adding a new effect means
    dropping a file into assets/sounds/ and adding one line here.
  * Per-sound default volumes, so a loud "game over" sting and a
    subtle "move" tick can coexist without the player reaching for
    the volume knob.

Usage:
    from src.audio.sfx import sfx
    sfx.init()          # once, right after pygame.init()
    sfx.play("merge")
"""
from __future__ import annotations

import array
from dataclasses import dataclass

import pygame

from src.constants.constants import ASSETS
from src.utils.settings_manager import load_audio_settings, save_audio_settings



SOUNDS_DIR = ASSETS / "sounds"

# --------------------------------------------------------------------
# Drop your files in assets/sounds/ using exactly these names.
# .ogg is strongly recommended (it is the only format guaranteed to
# work in a pygbag/web build; .wav also works on desktop).
# --------------------------------------------------------------------
SOUND_FILES: dict[str, str] = {
    # --- Global UI ---
    "ui_click":    "ui_click.ogg",      # any button press
    "ui_back":     "ui_back.ogg",       # "Back" to menu

    # --- Sliding mode ---
    "move":        "move.ogg",          # tiles slid, nothing reacted
    "merge":       "merge.ogg",         # one reaction happened
    "tile_pop":    "tile_pop.ogg",      # player taps a finished compound
    "tier_up":     "tier_up.ogg",       # new progression tier reached
    "game_over":   "game_over.ogg",     # board is full
    "high_score":  "high_score.ogg",    # game over, but a new record

    # --- Quiz modes (Balancing / Naming) ---
    "correct":     "correct.ogg",
    "wrong":       "wrong.ogg",
    "streak":      "streak.ogg",        # every 5th correct in a row

    # --- Periodic Trends ---
    "card_pickup": "card_pickup.ogg",   # grabbing a card off the belt
    "card_drop":   "card_drop.ogg",     # dropped correctly into a bin
    "card_miss":   "card_miss.ogg",     # wrong bin, or card ran off-screen

    # --- Tutorial ---
    "tutorial_step": "tutorial_step.ogg",
}

# 0.0 - 1.0. Anything not listed here falls back to DEFAULT_VOLUME.
DEFAULT_VOLUME = 0.6
VOLUMES: dict[str, float] = {
    "ui_click": 0.35,
    "ui_back": 0.35,
    "move": 0.50,
    "merge": 0.3,
    "tile_pop": 0.5,
    "tier_up": 0.8,
    "game_over": 0.7,
    "high_score": 0.85,
    "correct": 0.6,
    "wrong": 0.45,
    "streak": 0.8,
    "card_pickup": 0.3,
    "card_drop": 0.55,
    "card_miss": 0.45,
    "tutorial_step": 0.5,
}

# Optional background music. Leave the file out and nothing happens.
MUSIC_FILES: dict[str, str] = {
    "menu": "music_menu.ogg",
    "game": "music_game.ogg",
}


@dataclass
class _PendingNote:
    """One note queued by play_chain(), counting down to its play time."""
    delay: float
    sound: pygame.mixer.Sound


class AudioManager:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._missing: set[str] = set()
        self._available = False
        self._muted = False
        self._master_volume = 1.0
        self._current_music: str | None = None
        # Cache of pitch-shifted copies, keyed by (base name, ratio),
        # so a repeated chain doesn't re-resample every time.
        self._pitch_cache: dict[tuple[str, float], pygame.mixer.Sound] = {}
        # Notes queued by play_chain(), waiting for their turn.
        self._pending_notes: list[_PendingNote] = []

    # -- lifecycle ---------------------------------------------------
    def init(self) -> None:
        """Boots the mixer and preloads everything it can find.

        Safe to call more than once. A small buffer keeps latency low
        so a 'move' tick lands on the same frame as the swipe.
        """
        if self._available:
            return
        # Restore the player's saved mute/volume choice regardless of
        # whether the mixer actually comes up, so a settings widget can
        # still reflect the right state even in a silent environment.
        saved = load_audio_settings()
        self._muted = saved["muted"]
        self._master_volume = saved["volume"]

        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            # Plenty of channels so a chain reaction never cuts off the
            # previous pop.
            pygame.mixer.set_num_channels(32)
        except pygame.error as exc:
            print(f"[audio] mixer unavailable, running silent: {exc}")
            return

        self._available = True
        self._preload()
        self.set_master_volume(self._master_volume, persist=False)

    def _preload(self) -> None:
        for name, filename in SOUND_FILES.items():
            path = SOUNDS_DIR / filename
            if not path.exists():
                self._missing.add(name)
                continue
            try:
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(VOLUMES.get(name, DEFAULT_VOLUME))
                self._sounds[name] = sound
            except pygame.error as exc:
                print(f"[audio] could not load {filename}: {exc}")
                self._missing.add(name)

        if self._missing:
            print(
                "[audio] missing sound files (these will be silent): "
                + ", ".join(sorted(SOUND_FILES[n] for n in self._missing))
            )

    # -- playback ----------------------------------------------------
    def play(self, name: str) -> None:
        """Plays a named effect. Unknown or missing names are no-ops."""
        if not self._available or self._muted:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def _pitched(self, name: str, ratio: float) -> pygame.mixer.Sound | None:
        """Returns a pitch/speed-shifted copy of a loaded effect.

        Uses the classic "tape speed" trick: resampling the waveform to
        `1/ratio` of its original length raises pitch by `ratio` (and
        shortens the clip to match) with nothing beyond the stdlib
        `array` module - no extra audio libraries required. Results are
        cached per (name, ratio) since a chain reuses the same handful
        of pitches over and over.
        """
        base = self._sounds.get(name)
        if base is None:
            return None
        if ratio == 1.0:
            return base

        key = (name, round(ratio, 4))
        cached = self._pitch_cache.get(key)
        if cached is not None:
            return cached

        try:
            channels = 2  # matches the mixer's pre_init(channels=2)
            samples = array.array("h")
            samples.frombytes(base.get_raw())
            frame_count = len(samples) // channels
            if frame_count < 2:
                return base

            new_frame_count = max(1, int(frame_count / ratio))
            out = array.array("h", bytes(new_frame_count * channels * 2))
            last_index = frame_count - 1
            for i in range(new_frame_count):
                src_pos = i * ratio
                idx = int(src_pos)
                if idx >= last_index:
                    idx = last_index
                    frac = 0.0
                else:
                    frac = src_pos - idx
                base_i = idx * channels
                next_i = min(idx + 1, last_index) * channels
                out_i = i * channels
                for c in range(channels):
                    s0 = samples[base_i + c]
                    s1 = samples[next_i + c]
                    out[out_i + c] = int(s0 + (s1 - s0) * frac)

            shifted = pygame.mixer.Sound(buffer=out.tobytes())
            shifted.set_volume(base.get_volume())
            self._pitch_cache[key] = shifted
            return shifted
        except (pygame.error, MemoryError, ValueError) as exc:
            print(f"[audio] pitch shift failed for {name} @ {ratio}: {exc}")
            return base

    def play_chain(
        self,
        base: str,
        count: int,
        max_notes: int = 4,
        note_gap: float = 0.09,
        semitone_step: float = 3.0,
    ) -> None:
        """Plays up to `max_notes` copies of `base`, each a bit higher
        pitched than the last and staggered slightly, so a chain reads
        as a short rising run instead of one stacked sound.

        `count` is the number of reactions the chain actually had;
        anything past `max_notes` is dropped rather than piling on more
        notes than a 4-hit run should have.
        """
        if not self._available or self._muted:
            return
        if self._sounds.get(base) is None:
            return

        notes = max(1, min(count, max_notes))
        for i in range(notes):
            ratio = 2 ** ((i * semitone_step) / 12)
            sound = self._pitched(base, ratio)
            if sound is None:
                continue
            self._pending_notes.append(_PendingNote(delay=i * note_gap, sound=sound))

    def update(self, dt: float) -> None:
        """Drains staggered notes queued by play_chain(). Call once per
        frame regardless of which game context is active."""
        if not self._pending_notes:
            return
        if not self._available or self._muted:
            self._pending_notes.clear()
            return
        still_waiting: list[_PendingNote] = []
        for note in self._pending_notes:
            note.delay -= dt
            if note.delay <= 0:
                try:
                    note.sound.play()
                except pygame.error:
                    pass
            else:
                still_waiting.append(note)
        self._pending_notes = still_waiting

    def play_music(self, name: str, loops: int = -1, fade_ms: int = 400) -> None:
        if not self._available or self._muted:
            return
        if self._current_music == name:
            return
        filename = MUSIC_FILES.get(name)
        if filename is None:
            return
        path = SOUNDS_DIR / filename
        if not path.exists():
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.35 * self._master_volume)
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            self._current_music = name
        except pygame.error:
            pass

    def stop_music(self, fade_ms: int = 400) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except pygame.error:
            pass
        self._current_music = None

    # -- settings ----------------------------------------------------
    @property
    def muted(self) -> bool:
        return self._muted

    def set_muted(self, muted: bool, persist: bool = True) -> None:
        self._muted = muted
        if self._muted:
            self.stop_music(fade_ms=200)
        elif self._current_music is None:
            # Nothing was tracked as playing while muted (music was
            # faded out on mute); leave it to the caller to restart a
            # track if one should be running - we don't know which.
            pass
        if persist:
            save_audio_settings(self._muted, self._master_volume)

    def toggle_mute(self) -> bool:
        self.set_muted(not self._muted)
        return self._muted

    def set_master_volume(self, value: float, persist: bool = True) -> None:
        """value in 0.0 - 1.0; scales every effect's baseline volume."""
        self._master_volume = max(0.0, min(1.0, value))
        for name, sound in self._sounds.items():
            sound.set_volume(VOLUMES.get(name, DEFAULT_VOLUME) * self._master_volume)
        for (name, _ratio), sound in self._pitch_cache.items():
            sound.set_volume(VOLUMES.get(name, DEFAULT_VOLUME) * self._master_volume)
        if self._available:
            try:
                pygame.mixer.music.set_volume(0.35 * self._master_volume)
            except pygame.error:
                pass
        if persist:
            save_audio_settings(self._muted, self._master_volume)

    @property
    def master_volume(self) -> float:
        return self._master_volume


# Module-level singleton: import this, don't build your own.
sfx = AudioManager()