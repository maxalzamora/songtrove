"""Turn chord-sheet markup into safe, alignment-preserving HTML."""

from __future__ import annotations

import difflib
import html
import re

# Chord sheets may wrap chord names in [ch]...[/ch] and monospace blocks in
# [tab]...[/tab]. We keep the chord markup (as spans) and drop the block tags,
# because the <pre> element already gives us the fixed-width layout.
CHORD_RE = re.compile(r"\[ch\](.*?)\[/ch\]", re.IGNORECASE | re.DOTALL)
TAB_TAG_RE = re.compile(r"\[/?tab\]", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*\[[^\[\]\n]{1,80}\](?:\s*\([^)\n]*\))?\s*$")

# Chord names copied from a plain-text sheet (or typed into the editor) do not
# have [ch] wrappers. This recognises the common spellings without treating
# ordinary words in a lyric line as chords.
CHORD_NAME_RE = re.compile(
    r"(?<![A-Za-z0-9#b])"
    r"(\*?[A-G](?:#|b)?"
    r"(?:(?:maj|min|m|dim|aug|sus|add|no|°|ø|Δ)\d*|[#b]?\d+)*"
    r"(?:\([#b]?\d+\))*"
    r"(?:/(?:[A-G](?:#|b)?|\d+))?"
    r")"
    r"(?![A-Za-z0-9#b])"
)
CHORD_ANNOTATION_RE = re.compile(
    r"(?:\(\s*(?:x|×)?\s*\d+\s*(?:x|×)?\s*\)"
    r"|\[\s*(?:x|×)?\s*\d+\s*(?:x|×)?\s*\]"
    r"|\b(?:x|×)\s*\d+\b"
    r"|\b\d+\s*(?:x|×)\b)",
    re.IGNORECASE,
)
CHORD_SEPARATORS = set(" \t|:-–—,.[]()/×xX")

NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
# A guitarist-friendly default. Natural chord spellings use the most common
# accidental for each note; explicit sharps/flats keep their own style.
DEFAULT_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B")


def chord_sheet_html(content: str, transpose: int = 0) -> str:
    """Render tab text to HTML while keeping every character's position.

    All user/page text is escaped; only our own chord and section spans are
    added. The result is meant to live inside ``<pre class="sheet">`` with
    ``white-space: pre``. ``transpose`` shifts chord names by that many
    semitones; the original chord is kept in ``data-chord`` so the browser can
    update it immediately when the capo changes.
    """
    text = _normalize(content)
    text = TAB_TAG_RE.sub("", text)

    lines = []
    for line in text.split("\n"):
        if SECTION_RE.match(line):
            lines.append(f'<span class="sheet-section">{html.escape(line)}</span>')
        elif CHORD_RE.search(line):
            lines.append(_render_line(line, transpose))
        else:
            lines.append(_render_plain_line(line, transpose))
    return "\n".join(lines)


def transpose_chord(chord: str, semitones: int) -> str:
    """Move a chord name by ``semitones``, keeping its quality and slash bass."""
    if not semitones or semitones % 12 == 0:
        return chord

    match = re.match(r"^(\*?)([A-G])([#b]?)(.*)$", chord)
    if not match:
        return chord

    prefix, letter, accidental, suffix = match.groups()
    root = _shift_note(letter, accidental, semitones)

    # Slash basses are notes too. Leave numeric extensions such as C6/9 alone.
    suffix = re.sub(
        r"/([A-G])([#b]?)(?![A-Za-z0-9#b])",
        lambda slash: "/" + _shift_note(slash.group(1), slash.group(2), semitones),
        suffix,
    )
    return f"{prefix}{root}{suffix}"


def plain_sheet_text(content: str) -> str:
    """Return the sheet exactly as it appears on the song page.

    The editor uses this instead of showing ``[ch]`` / ``[tab]`` markup. Chord
    names are kept in place, and only the invisible wrapper tags are removed, so
    the monospace alignment is unchanged.
    """
    text = _normalize(content)
    text = TAB_TAG_RE.sub("", text)
    return CHORD_RE.sub(lambda match: match.group(1).strip(), text)


def merge_edited_text(original: str, edited: str) -> str:
    """Save visible-text edits while preserving markup on unchanged lines.

    A line that was not changed keeps its original ``[ch]`` markup, so chord
    highlighting survives a cleanup of filler lines. New or edited lines are
    stored as plain text; the renderer escapes them as usual.
    """
    original_text = _normalize(original)
    edited_text = _normalize(edited)
    original_lines = original_text.split("\n")
    visible_lines = plain_sheet_text(original_text).split("\n")
    edited_lines = edited_text.split("\n")

    # This should always hold: removing tags never adds or removes newlines.
    # If an unusual tab contains a multi-line [ch] tag, fall back to the text
    # the person just saved rather than risking misaligned output.
    if len(original_lines) != len(visible_lines):
        return edited_text

    matcher = difflib.SequenceMatcher(
        None, visible_lines, edited_lines, autojunk=False
    )
    merged: list[str] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            merged.extend(original_lines[old_start:old_end])
        elif tag in {"replace", "insert"}:
            merged.extend(edited_lines[new_start:new_end])
        # Deleted lines are simply omitted.

    return "\n".join(merged)


def _render_line(line: str, transpose: int = 0) -> str:
    pieces = []
    position = 0
    for match in CHORD_RE.finditer(line):
        pieces.append(html.escape(line[position : match.start()]))
        chord = _chord_span(match.group(1).strip(), transpose)
        pieces.append(chord)
        position = match.end()
    pieces.append(html.escape(line[position:]))
    return "".join(pieces)


def _render_plain_line(line: str, transpose: int = 0) -> str:
    """Render a line from a plain-text tab, highlighting chord-only lines."""
    if not _is_chord_line(line):
        return html.escape(line)

    pieces = []
    position = 0
    for match in CHORD_NAME_RE.finditer(line):
        pieces.append(html.escape(line[position : match.start()]))
        pieces.append(_chord_span(match.group(1), transpose))
        position = match.end()
    pieces.append(html.escape(line[position:]))
    return "".join(pieces)


def _is_chord_line(line: str) -> bool:
    if not CHORD_NAME_RE.search(line):
        return False

    remainder = CHORD_NAME_RE.sub("", line)
    remainder = CHORD_ANNOTATION_RE.sub("", remainder)
    return all(char in CHORD_SEPARATORS for char in remainder)


def _chord_span(chord: str, transpose: int) -> str:
    original = chord.strip()
    displayed = transpose_chord(original, transpose)
    original_attr = html.escape(original, quote=True)
    return (
        f'<span class="chord" data-chord="{original_attr}">'
        f"{html.escape(displayed)}</span>"
    )


def _shift_note(letter: str, accidental: str, semitones: int) -> str:
    index = NOTE_INDEX[letter]
    if accidental == "#":
        index += 1
        names = SHARP_NAMES
    elif accidental == "b":
        index -= 1
        names = FLAT_NAMES
    else:
        names = DEFAULT_NAMES
    return names[(index + semitones) % 12]


def _normalize(content: str) -> str:
    return (content or "").replace("\r\n", "\n").replace("\r", "\n")
