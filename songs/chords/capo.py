"""Capo arithmetic.

A capo on fret *n* raises everything you play by *n* semitones. So if a song
sounds in G and the capo is on fret 2, you finger F shapes and hear G::

    shape_key = sounding_key - capo
    sounding_key = shape_key + capo
"""

from __future__ import annotations

from dataclasses import dataclass

from .theory import prefers_flats
from .transpose import transpose_key

MAX_CAPO = 12

# Keys most players are comfortable in, used to suggest capo positions.
COMMON_SHAPE_KEYS = ("C", "G", "D", "A", "E", "F", "Bb", "Eb", "Ab", "B")


@dataclass(frozen=True, slots=True)
class CapoPlan:
    sounding_key: str
    shape_key: str
    capo: int

    @property
    def uses_capo(self) -> bool:
        return self.capo > 0

    def describe(self) -> str:
        if not self.sounding_key:
            return ""
        if not self.uses_capo:
            return f"Original {self.sounding_key} · no capo"
        return f"Original {self.sounding_key} · capo {self.capo} → play {self.shape_key} shapes"


def shape_key_for(sounding_key: str, capo: int, prefer_flats: bool | None = None) -> str:
    """The key you finger when a song in ``sounding_key`` is capoed at ``capo``."""
    if not sounding_key:
        return ""
    if prefer_flats is None:
        prefer_flats = prefers_flats(sounding_key)
    return transpose_key(sounding_key, -capo, prefer_flats)


def sounding_key_for(shape_key: str, capo: int, prefer_flats: bool | None = None) -> str:
    """The key that comes out when you play ``shape_key`` shapes with a capo."""
    if not shape_key:
        return ""
    if prefer_flats is None:
        prefer_flats = prefers_flats(shape_key)
    return transpose_key(shape_key, capo, prefer_flats)


def plan_for(sounding_key: str, capo: int, prefer_flats: bool | None = None) -> CapoPlan:
    """Everything the sheet header needs to explain the capo."""
    return CapoPlan(
        sounding_key=sounding_key,
        shape_key=shape_key_for(sounding_key, capo, prefer_flats),
        capo=capo,
    )


def suggest_capos(
    sounding_key: str,
    max_capo: int = 7,
    prefer_flats: bool | None = None,
) -> list[CapoPlan]:
    """Capo positions between 1 and ``max_capo`` that yield a common shape key."""
    if not sounding_key:
        return []

    limit = max(0, min(max_capo, MAX_CAPO))
    suggestions: list[CapoPlan] = []
    for capo in range(1, limit + 1):
        shape = shape_key_for(sounding_key, capo, prefer_flats)
        if shape in COMMON_SHAPE_KEYS:
            suggestions.append(CapoPlan(sounding_key=sounding_key, shape_key=shape, capo=capo))
    return suggestions
