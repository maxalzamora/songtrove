"""Pitch-class primitives shared by transposition and capo calculations."""

from __future__ import annotations

SHARP_NAMES: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES: tuple[str, ...] = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

NOTE_TO_PITCH: dict[str, int] = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

# Pitch classes that chord charts almost always write with a flat when there is
# no key context to go on. C# vs Db and F# vs Gb stay sharp for guitarists.
FLAT_BY_DEFAULT = frozenset({3, 8, 10})

# Keys offered in the song form. Both spellings of each accidental are kept so
# a sheet written in Eb stays in flats when it is transposed.
KEY_CHOICES: tuple[tuple[str, str], ...] = tuple(
    (name, name)
    for name in ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B")
)


def pitch_of(note: str) -> int | None:
    """Pitch class 0-11 for a note name, or ``None`` if it is not a note."""
    return NOTE_TO_PITCH.get(note.strip())


def spell(pitch: int, prefer_flats: bool = False) -> str:
    """Name a pitch class, choosing sharps or flats."""
    names = FLAT_NAMES if prefer_flats else SHARP_NAMES
    return names[pitch % 12]


def prefers_flats(note: str) -> bool:
    """Whether a note name is written with a flat."""
    return "b" in note
