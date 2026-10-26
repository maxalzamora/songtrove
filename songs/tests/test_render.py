from types import SimpleNamespace

from django.template import Context, Template

from songs.chords import LineKind
from songs.chords.render import render_sheet
from songs.models import Song


def rows_of(body, semitones=0, prefer_flats=None):
    return render_sheet(body, semitones=semitones, prefer_flats=prefer_flats)


def test_lyric_row_carries_cells():
    rows = rows_of("[G]Amazing [C]grace")

    assert len(rows) == 1
    assert rows[0].kind is LineKind.LYRIC
    assert [(cell.chord, cell.lyric) for cell in rows[0].cells] == [
        ("G", "Amazing "),
        ("C", "grace"),
    ]


def test_chords_are_transposed():
    rows = rows_of("[G]Amazing [C]grace", semitones=2)

    assert [cell.chord for cell in rows[0].cells] == ["A", "D"]


def test_transposition_respects_flat_preference():
    rows = rows_of("[C]x", semitones=1, prefer_flats=True)

    assert rows[0].cells[0].chord == "Db"


def test_bare_chord_is_flagged():
    rows = rows_of("[G][D]")

    assert [cell.is_bare for cell in rows[0].cells] == [True, True]


def test_blank_lines_survive_as_rows():
    rows = rows_of("one\n\ntwo")

    assert [row.kind for row in rows] == [
        LineKind.LYRIC,
        LineKind.BLANK,
        LineKind.LYRIC,
    ]


def test_comments_survive_as_rows():
    rows = rows_of("{comment: Chorus}\n[G]sing")

    assert rows[0].kind is LineKind.COMMENT
    assert rows[0].text == "Chorus"


def test_directives_are_not_sheet_rows():
    rows = rows_of("{capo: 2}\n[G]sing")

    assert [row.kind for row in rows] == [LineKind.LYRIC]


def test_empty_body_renders_nothing():
    assert rows_of("") == []


def render_tag(song, transpose=0):
    template = Template("{% load sheet %}{% chord_sheet song transpose=transpose %}")
    return template.render(Context({"song": song, "transpose": transpose}))


def song(**overrides):
    defaults = {
        "song_key": "G",
        "sheet_format": Song.SheetFormat.CHORDPRO,
        "sheet_body": "[G]Amazing [C]grace",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_tag_renders_chords_above_lyrics():
    html = render_tag(song())

    # The chord span must come before its syllable, inside one cell.
    assert '<span class="chord-cell">' in html
    assert html.index("chord-cell__chord") < html.index("chord-cell__lyric")
    assert ">G<" in html
    assert ">Amazing <" in html


def test_tag_transposes():
    html = render_tag(song(sheet_body="[G]hi"), transpose=2)

    assert ">A<" in html


def test_tag_renders_plain_sheets_verbatim():
    html = render_tag(
        song(
            sheet_format=Song.SheetFormat.PLAIN,
            sheet_body="G       C\nAmazing grace",
        )
    )

    assert "chord-sheet--plain" in html
    assert "Amazing grace" in html
    assert "chord-cell" not in html


def test_tag_escapes_lyrics():
    html = render_tag(song(sheet_body="[G]<script>alert(1)</script>"))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_tag_renders_bare_chord_class():
    html = render_tag(song(sheet_body="[G][C]"))

    assert "chord-cell--bare" in html


def test_tag_flat_key_spelling():
    html = render_tag(song(song_key="Bb", sheet_body="[C]x"), transpose=1)

    assert ">Db<" in html
