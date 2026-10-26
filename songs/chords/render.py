"""Turn a stored sheet into rows a template can paint.

Chords-above-lyrics is the layout players expect: one cell per chord, with the
syllables the chord sits over directly underneath it. Cells are inline-block,
so the chord stays glued to its syllable no matter how the line wraps.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser import LineKind, parse_sheet
from .transpose import transpose_chord


@dataclass(frozen=True, slots=True)
class Cell:
    chord: str | None
    lyric: str

    @property
    def is_bare(self) -> bool:
        """A chord with no syllable under it, as in an intro."""
        return bool(self.chord) and not self.lyric


@dataclass(frozen=True, slots=True)
class Row:
    kind: LineKind
    cells: tuple[Cell, ...] = ()
    text: str = ""


def render_sheet(
    body: str,
    semitones: int = 0,
    prefer_flats: bool | None = None,
) -> list[Row]:
    """Parse and transpose a ChordPro sheet into render rows.

    Directives are metadata for the header, not sheet content, so they are not
    turned into rows. Comments and blank lines are kept because they carry
    structure the player needs.
    """
    rows: list[Row] = []

    for line in parse_sheet(body):
        if line.kind is LineKind.LYRIC:
            cells = tuple(
                Cell(
                    chord=transpose_chord(segment.chord, semitones, prefer_flats)
                    if segment.chord
                    else None,
                    lyric=segment.lyric,
                )
                for segment in line.segments
            )
            rows.append(Row(kind=LineKind.LYRIC, cells=cells))
        elif line.kind is LineKind.COMMENT:
            rows.append(Row(kind=LineKind.COMMENT, text=line.text))
        elif line.kind is LineKind.BLANK:
            rows.append(Row(kind=LineKind.BLANK))

    return rows
