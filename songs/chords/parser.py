"""ChordPro parsing.

Turns a sheet like::

    {comment: Verse 1}
    [G]Amazing [C]grace, how [G]sweet the sound

into structured lines that templates can render as chords above lyrics.

This module is deliberately free of Django imports: it is pure text in, pure
data out, which keeps it fast to test and reusable outside the web layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

CHORD_RE = re.compile(r"\[([^\[\]]*)\]")
DIRECTIVE_RE = re.compile(r"^\{\s*([A-Za-z_]+)\s*(?::\s*(.*?))?\s*\}$")

COMMENT_DIRECTIVES = frozenset({"comment", "c"})

SECTION_DIRECTIVES = frozenset(
    {
        "start_of_chorus",
        "soc",
        "end_of_chorus",
        "eoc",
        "start_of_verse",
        "sov",
        "end_of_verse",
        "eov",
        "start_of_bridge",
        "sob",
        "end_of_bridge",
        "eob",
        "start_of_tab",
        "sot",
        "end_of_tab",
        "eot",
        "start_of_grid",
        "sog",
        "end_of_grid",
        "eog",
    }
)


class LineKind(StrEnum):
    LYRIC = "lyric"
    COMMENT = "comment"
    DIRECTIVE = "directive"
    BLANK = "blank"


@dataclass(frozen=True, slots=True)
class Segment:
    """A run of syllables and the chord struck at its start."""

    chord: str | None
    lyric: str

    @property
    def has_chord(self) -> bool:
        return bool(self.chord)


@dataclass(frozen=True, slots=True)
class Line:
    kind: LineKind
    segments: tuple[Segment, ...] = ()
    text: str = ""
    name: str = ""

    @property
    def chords(self) -> tuple[str, ...]:
        return tuple(s.chord for s in self.segments if s.chord)

    @property
    def is_blank(self) -> bool:
        return self.kind is LineKind.BLANK

    @property
    def is_section_marker(self) -> bool:
        return self.kind is LineKind.DIRECTIVE and self.name in SECTION_DIRECTIVES


def parse_lyric_line(raw: str) -> Line:
    """Split one line into chord/lyric segments.

    Text before the first chord becomes a chordless segment. A chord with no
    lyric after it becomes an empty segment, which renders as a standalone
    chord (used for intros and instrumental stabs).
    """
    segments: list[Segment] = []
    pending_chord: str | None = None
    started = False
    last_end = 0

    for match in CHORD_RE.finditer(raw):
        lyric = raw[last_end : match.start()]
        if started:
            segments.append(Segment(pending_chord, lyric))
        elif lyric:
            segments.append(Segment(None, lyric))
        started = True
        pending_chord = match.group(1).strip() or None
        last_end = match.end()

    tail = raw[last_end:]
    if started:
        segments.append(Segment(pending_chord, tail))
    elif tail:
        segments.append(Segment(None, tail))

    # `Hello []world` produces two chordless runs; join them back up.
    merged: list[Segment] = []
    for segment in segments:
        if merged and segment.chord is None and merged[-1].chord is None:
            merged[-1] = Segment(None, merged[-1].lyric + segment.lyric)
        else:
            merged.append(segment)

    return Line(kind=LineKind.LYRIC, segments=tuple(merged))


def parse_line(raw: str) -> Line:
    line = raw.rstrip()
    stripped = line.strip()

    if not stripped:
        return Line(kind=LineKind.BLANK)

    directive = DIRECTIVE_RE.match(stripped)
    if directive:
        name = directive.group(1).lower()
        value = (directive.group(2) or "").strip()
        if name in COMMENT_DIRECTIVES:
            return Line(kind=LineKind.COMMENT, text=value, name=name)
        return Line(kind=LineKind.DIRECTIVE, text=value, name=name)

    return parse_lyric_line(line)


def parse_sheet(body: str) -> list[Line]:
    """Parse a full sheet, preserving blank lines for spacing."""
    if not body:
        return []
    return [parse_line(raw) for raw in body.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
