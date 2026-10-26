"""Best-effort conversion from chords-above-lyrics text into ChordPro.

Most chord sheets in the wild look like this::

    G           C
    Amazing grace, how sweet the sound

ChordPro wants the chord attached to the syllable it lands on::

    [G]Amazing [C]grace, how sweet the sound

The conversion is mechanical: find lines that are only chords, then splice each
chord into the lyric line underneath at the column it was written at. Anything
that does not look like a chord line is left alone, including existing ChordPro.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ROOT_RE = re.compile(r"^[A-G][#b]?")
BASS_RE = re.compile(r"^[A-G][#b]?$")

SUFFIX_RE = re.compile(
    r"^(?:"
    r"(?:maj|min|dim|aug|sus|add|alt|omit|no|m|M|Δ|°|ø|\+|-)?"
    r"(?:\d{1,2})?"
    r"(?:[#b]\d{1,2})?"
    r"(?:sus\d|add\d{1,2}|no\d{1,2}|\([^)]*\))*"
    r")$"
)

SEPARATORS = frozenset({"|", "||", ":", "-", "/", "x2", "x3", "x4"})
NON_CHORDS = frozenset({"N.C.", "NC", "N.C"})
TOKEN_RE = re.compile(r"\S+")
CHORDPRO_RE = re.compile(r"\[[^\[\]]+\]")


@dataclass(frozen=True, slots=True)
class Conversion:
    text: str
    chord_lines: int
    already_chordpro: bool

    @property
    def changed(self) -> bool:
        return self.chord_lines > 0


def is_chord(token: str) -> bool:
    """Whether a token looks like a chord symbol rather than a word."""
    text = token.strip()
    if not text or text in SEPARATORS:
        return False
    if text in NON_CHORDS:
        return True

    head = text
    if "/" in text:
        head, _, bass = text.rpartition("/")
        if not BASS_RE.match(bass):
            return False

    root = ROOT_RE.match(head)
    if root is None:
        return False
    return bool(SUFFIX_RE.match(head[root.end() :]))


def find_chords(line: str) -> list[tuple[str, int]]:
    """Chords on a line, paired with the column they start at."""
    return [(match.group(), match.start()) for match in TOKEN_RE.finditer(line) if is_chord(match.group())]


def is_chord_line(line: str) -> bool:
    tokens = line.split()
    if not tokens:
        return False

    chords = [token for token in tokens if is_chord(token)]
    leftovers = [token for token in tokens if not is_chord(token) and token not in SEPARATORS]
    return bool(chords) and not leftovers


def merge(chords: list[tuple[str, int]], lyric: str) -> str:
    """Splice chords into a lyric line at their original columns."""
    result: list[str] = []
    cursor = 0

    for chord, column in chords:
        column = max(cursor, min(column, len(lyric)))
        result.append(lyric[cursor:column])
        result.append(f"[{chord}]")
        cursor = column

    result.append(lyric[cursor:])
    return "".join(result)


def convert(text: str) -> Conversion:
    """Convert a pasted sheet to ChordPro, leaving anything ambiguous alone."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")

    if CHORDPRO_RE.search(normalised):
        return Conversion(text=normalised, chord_lines=0, already_chordpro=True)

    lines = normalised.split("\n")
    output: list[str] = []
    chord_lines = 0
    index = 0

    while index < len(lines):
        line = lines[index]

        if not is_chord_line(line):
            output.append(line)
            index += 1
            continue

        chords = find_chords(line)
        following = lines[index + 1] if index + 1 < len(lines) else ""
        chord_lines += 1

        # Bar separators are repeated per bar and do not line up with syllables,
        # so a bar line is treated as instrumental rather than merged.
        has_bars = any(token in {"|", "||"} for token in line.split())

        if following.strip() and not is_chord_line(following) and not has_bars:
            output.append(merge(chords, following))
            index += 2
        else:
            # Instrumental: chords with no lyric underneath.
            output.append("".join(f"[{chord}]" for chord, _ in chords))
            index += 1

    return Conversion(text="\n".join(output), chord_lines=chord_lines, already_chordpro=False)
