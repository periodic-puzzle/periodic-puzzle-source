"""Lightweight confetti burst effect.

Pure pygame primitives -- no extra assets, no dependencies. Each piece
is a small rotating rectangle under gravity with a bit of horizontal
drag, which reads as paper confetti rather than a particle explosion.

Usage:
    self.confetti = ConfettiSystem()          # in __init__
    self.confetti.burst((300, 300))           # on a win moment
    self.confetti.rain()                      # big celebration, top of screen
    self.confetti.update(dt)                  # in update()
    self.confetti.draw(surface)               # LAST thing in render()
"""
from __future__ import annotations

import math
import random

import pygame

# Warm, saturated palette that stays readable over the cream background
# used throughout the game.
CONFETTI_COLORS: list[tuple[int, int, int]] = [
    (255, 99, 132),   # pink
    (255, 190, 60),   # gold
    (90, 200, 250),   # sky
    (130, 220, 140),  # mint
    (180, 140, 245),  # violet
    (255, 140, 70),   # orange
]

GRAVITY = 900.0      # px/s^2
DRAG = 0.98          # horizontal velocity retained per frame-ish
MAX_PARTICLES = 400  # hard cap so spamming bursts can't tank the framerate


class _Piece:
    __slots__ = ("x", "y", "vx", "vy", "w", "h", "color", "angle", "spin", "life", "max_life")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.w = random.randint(5, 10)
        self.h = random.randint(8, 14)
        self.color = random.choice(CONFETTI_COLORS)
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-420, 420)
        self.life = life
        self.max_life = life

    def update(self, dt: float) -> None:
        self.vy += GRAVITY * dt
        self.vx *= DRAG
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        self.life -= dt

    @property
    def is_dead(self) -> bool:
        return self.life <= 0

    def draw(self, surface: pygame.Surface) -> None:
        # Fade out over the last 30% of the piece's life.
        ratio = self.life / self.max_life
        alpha = 255 if ratio > 0.3 else int(255 * (ratio / 0.3))
        alpha = max(0, min(255, alpha))

        piece = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        piece.fill((*self.color, alpha))

        # Spinning on one axis only would look like a flat sprite turning;
        # squashing the height by cos() fakes the paper flipping over.
        flip = abs(math.cos(math.radians(self.angle)))
        scaled = pygame.transform.scale(
            piece, (self.w, max(1, int(self.h * flip)))
        )
        rotated = pygame.transform.rotate(scaled, self.angle * 0.35)
        surface.blit(rotated, rotated.get_rect(center=(self.x, self.y)))


class ConfettiSystem:
    def __init__(self, screen_size: tuple[int, int] = (600, 600)) -> None:
        self.screen_w, self.screen_h = screen_size
        self.pieces: list[_Piece] = []

    @property
    def is_active(self) -> bool:
        return len(self.pieces) > 0

    def clear(self) -> None:
        self.pieces.clear()

    def burst(self, center: tuple[float, float], count: int = 40, power: float = 420.0) -> None:
        """A radial pop from a point -- use for merges, pops, streaks."""
        if len(self.pieces) >= MAX_PARTICLES:
            return
        cx, cy = center
        count = min(count, MAX_PARTICLES - len(self.pieces))
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(power * 0.4, power)
            self.pieces.append(
                _Piece(
                    x=cx,
                    y=cy,
                    vx=math.cos(angle) * speed,
                    # Bias upward so it arcs instead of splattering sideways.
                    vy=math.sin(angle) * speed - random.uniform(120, 260),
                    life=random.uniform(1.0, 1.8),
                )
            )

    def rain(self, count: int = 90) -> None:
        """A curtain falling from above the screen -- big win moments."""
        if len(self.pieces) >= MAX_PARTICLES:
            return
        count = min(count, MAX_PARTICLES - len(self.pieces))
        for _ in range(count):
            self.pieces.append(
                _Piece(
                    x=random.uniform(0, self.screen_w),
                    y=random.uniform(-self.screen_h * 0.5, -20),
                    vx=random.uniform(-70, 70),
                    vy=random.uniform(40, 160),
                    life=random.uniform(2.0, 3.4),
                )
            )

    def cannons(self, count: int = 50) -> None:
        """Two angled jets from the bottom corners -- celebratory finale."""
        for origin, angle_deg in (((10, self.screen_h), -62), ((self.screen_w - 10, self.screen_h), -118)):
            if len(self.pieces) >= MAX_PARTICLES:
                return
            for _ in range(min(count, MAX_PARTICLES - len(self.pieces))):
                angle = math.radians(angle_deg + random.uniform(-16, 16))
                speed = random.uniform(700, 1050)
                self.pieces.append(
                    _Piece(
                        x=origin[0],
                        y=origin[1],
                        vx=math.cos(angle) * speed,
                        vy=math.sin(angle) * speed,
                        life=random.uniform(1.6, 2.6),
                    )
                )

    def update(self, dt: float) -> None:
        if not self.pieces:
            return
        for piece in self.pieces:
            piece.update(dt)
        # Cull dead pieces and anything that has fallen well off-screen.
        self.pieces = [
            p for p in self.pieces
            if not p.is_dead and p.y < self.screen_h + 60
        ]

    def draw(self, surface: pygame.Surface) -> None:
        for piece in self.pieces:
            piece.draw(surface)
