"""Transpose chord symbols and keys without mangling their spelling.

The rules that matter in practice:

* ``C`` up two semitones is ``D``, but ``C`` up one is ``C#`` in a sharp key
  and ``Db`` in a flat one.
* The quality of a chord (``m7``, ``sus4``, ``b5``) is carried through
  untouched, including the ``b`` in ``7b5``.
* Slash basses move too, and a bass that lands on the root is dropped.
* Anything that is not a chord (``N.C.``, ``|``, a stray word) passes through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .theory import FLAT_BY_DEFAULT, pitch_of, prefers_flats, spell

CHORD_RE = re.compile(
    r"^(?P<root>[A-G])(?P<accidental>[#b]?)(?P<quality>[^/]*)(?:/(?P<bass>[A-G])(?P<bass_accidental>[#b]?))?$"
)

NON_CHORDS = frozenset({"N.C.", "NC", "N.C", "|", "%", "-", "/"})


@dataclass(frozen=True, slots=True)
class ParsedChord:
    root: str
    quality: str
    bass: str | None

    @property
    def accidentals(self) -> str:
        """Only the accidentals on root and bass, ignoring ``b5``-style qualities."""
        text = self.root[1:]
        if self.bass:
            text += self.bass[1:]
        return text


def parse_chord(symbol: str) -> ParsedChord | None:
    """Split a chord symbol into root, quality and optional slash bass."""
    text = symbol.strip()
    if not text or text in NON_CHORDS:
        return None

    match = CHORD_RE.match(text)
    if not match:
        return None

    root = match.group("root") + match.group("accidental")
    bass = None
    if match.group("bass"):
        bass = match.group("bass") + match.group("bass_accidental")

    return ParsedChord(root=root, quality=match.group("quality"), bass=bass)


def transpose_chord(symbol: str, semitones: int, prefer_flats: bool | None = None) -> str:
    """Move a chord symbol by ``semitones``, keeping it readable.

    ``prefer_flats`` overrides the spelling choice. When left as ``None`` the
    symbol's own accidentals decide, so flats stay flats and sharps stay sharp.
    """
    shift = semitones % 12
    if shift == 0:
        return symbol

    chord = parse_chord(symbol)
    if chord is None:
        return symbol

    flats = prefer_flats if prefer_flats is not None else "b" in chord.accidentals

    root_pitch = pitch_of(chord.root)
    if root_pitch is None:
        return symbol

    if prefer_flats is None and not chord.accidentals:
        flats = (root_pitch + shift) % 12 in FLAT_BY_DEFAULT

    new_root = spell(root_pitch + shift, flats)

    new_bass = None
    if chord.bass:
        bass_pitch = pitch_of(chord.bass)
        if bass_pitch is not None:
            candidate = spell(bass_pitch + shift, flats)
            if candidate != new_root:
                new_bass = candidate

    result = new_root + chord.quality
    return f"{result}/{new_bass}" if new_bass else result


def transpose_key(key: str, semitones: int, prefer_flats: bool | None = None) -> str:
    """Move a bare key name, e.g. ``G`` down two semitones to ``F``."""
    text = key.strip()
    pitch = pitch_of(text)
    if pitch is None:
        return key

    flats = prefer_flats if prefer_flats is not None else prefers_flats(text)
    if prefer_flats is None and not flats:
        flats = (pitch + semitones) % 12 in FLAT_BY_DEFAULT
    return spell(pitch + semitones, flats)