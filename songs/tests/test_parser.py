import pytest

from songs.chords import LineKind, Segment, parse_line, parse_sheet


def chords_and_lyrics(line):
    return [(segment.chord, segment.lyric) for segment in line.segments]


def test_chord_at_line_start():
    line = parse_line("[G]Amazing grace")

    assert line.kind is LineKind.LYRIC
    assert chords_and_lyrics(line) == [("G", "Amazing grace")]


def test_chord_mid_line():
    line = parse_line("Amazing [G]grace how [C]sweet")

    assert chords_and_lyrics(line) == [
        (None, "Amazing "),
        ("G", "grace how "),
        ("C", "sweet"),
    ]


def test_blank_line_is_preserved():
    lines = parse_sheet("Verse one\n\nVerse two")

    assert [line.kind for line in lines] == [
        LineKind.LYRIC,
        LineKind.BLANK,
        LineKind.LYRIC,
    ]


def test_instrumental_chord_only_line():
    line = parse_line("[G][D][Em][C]")

    assert chords_and_lyrics(line) == [("G", ""), ("D", ""), ("Em", ""), ("C", "")]


def test_empty_brackets_are_not_a_chord():
    line = parse_line("Hello []world")

    assert chords_and_lyrics(line) == [(None, "Hello world")]


def test_comment_directive():
    line = parse_line("{comment: Verse 1}")

    assert line.kind is LineKind.COMMENT
    assert line.text == "Verse 1"


def test_short_comment_alias():
    assert parse_line("{c: quiet}").text == "quiet"


def test_section_directive_is_a_marker():
    line = parse_line("{start_of_chorus}")

    assert line.kind is LineKind.DIRECTIVE
    assert line.is_section_marker


def test_unknown_directive_is_kept_out_of_the_lyrics():
    line = parse_line("{capo: 3}")

    assert line.kind is LineKind.DIRECTIVE
    assert line.name == "capo"
    assert line.text == "3"
    assert line.segments == ()


def test_windows_line_endings():
    lines = parse_sheet("one\r\ntwo\rthree")

    assert [line.segments[0].lyric for line in lines] == ["one", "two", "three"]


def test_whitespace_only_line_is_blank():
    assert parse_line("   \t ").kind is LineKind.BLANK


def test_plain_lyrics_without_chords():
    line = parse_line("No chords here")

    assert line.chords == ()
    assert chords_and_lyrics(line) == [(None, "No chords here")]


def test_chord_whitespace_is_trimmed():
    line = parse_line("[ Am7 ]leave")

    assert line.segments[0] == Segment("Am7", "leave")


@pytest.mark.parametrize("symbol", ["F#m7b5", "C/G", "N.C.", "Bbadd9", "E7#9"])
def test_unusual_chords_survive_parsing(symbol):
    line = parse_line(f"[{symbol}]x")

    assert line.chords == (symbol,)


def test_empty_sheet():
    assert parse_sheet("") == []
