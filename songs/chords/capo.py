"""Capo arithmetic.

A sheet written for a capo holds *shape* chords: what you finger. A capo on
fret *n* raises them by *n* semitones, so the key the audience hears is::

    sounding_key = written_key + capo
    written_key  = sounding_key - capo

A song in G played with a capo on 2 is written in F shapes and sounds in G.
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
    written_key: str
    sounding_key: str
    capo: int

    @property
    def uses_capo(self) -> bool:
        return self.capo > 0

    def describe(self) -> str:
        if not self.written_key:
            return ""
        if not self.uses_capo:
            return f"Play in {self.written_key}, no capo"
        return f"Capo {self.capo}, play {self.written_key} shapes, sounds in {self.sounding_key}"


def sounding_key_for(written_key: str, capo: int, prefer_flats: bool | None = None) -> str:
    """The key that comes out when you play ``written_key`` shapes with a capo."""
    if not written_key:
        return ""
    if prefer_flats is None:
        prefer_flats = prefers_flats(written_key)
    return transpose_key(written_key, capo, prefer_flats)


def written_key_for(sounding_key: str, capo: int, prefer_flats: bool | None = None) -> str:
    """The shape key to finger if a song should sound in ``sounding_key``."""
    if not sounding_key:
        return ""
    if prefer_flats is None:
        prefer_flats = prefers_flats(sounding_key)
    return transpose_key(sounding_key, -capo, prefer_flats)


def plan_for(written_key: str, capo: int, prefer_flats: bool | None = None) -> CapoPlan:
    """Everything the sheet header needs to explain the capo."""
    return CapoPlan(
        written_key=written_key,
        sounding_key=sounding_key_for(written_key, capo, prefer_flats),
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
        written = written_key_for(sounding_key, capo, prefer_flats)
        if written in COMMON_SHAPE_KEYS:
            suggestions.append(
                CapoPlan(written_key=written, sounding_key=sounding_key, capo=capo)
            )
    return suggestions
