"""Template tags for printing a song's sheet."""

from django import template

from songs.chords.render import render_sheet
from songs.chords.theory import prefers_flats
from songs.chords.transpose import transpose_key

from ..models import Song

register = template.Library()


@register.inclusion_tag("songs/_sheet.html")
def chord_sheet(song: Song, transpose: int = 0) -> dict:
    """Render a song's sheet, transposed by ``transpose`` semitones."""
    # Spelling follows the key after transposition, so a sheet moved down into
    # Bb starts using flats rather than sharps.
    key = transpose_key(song.song_key, transpose) if song.song_key else ""
    prefer_flats = prefers_flats(key) if key else None

    return {
        "song": song,
        "is_plain": song.sheet_format == Song.SheetFormat.PLAIN,
        "plain_body": song.sheet_body,
        "rows": render_sheet(
            song.sheet_body,
            semitones=transpose,
            prefer_flats=prefer_flats,
        ),
    }
