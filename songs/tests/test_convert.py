import pytest

from songs.chords.convert import convert, is_chord


@pytest.mark.parametrize(
    "symbol",
    ["G", "Am", "F#m7b5", "C/G", "Dmaj7", "Esus4", "A7sus4", "Bbadd9", "G7(b9)", "C#dim7", "N.C."],
)
def test_recognises_chords(symbol):
    assert is_chord(symbol)


@pytest.mark.parametrize(
    "word",
    ["Amazing", "grace", "Gone", "Blues", "Ballad", "A", "The", "and"],
)
def test_rejects_words_that_start_with_a_note(word):
    # "A" is a chord; "Amazing" is not, even though it starts on A.
    assert is_chord(word) is (word == "A")


def test_converts_simple_sheet():
    result = convert("G       C\nAmazing grace, how sweet the sound")

    assert result.text == "[G]Amazing [C]grace, how sweet the sound"
    assert result.chord_lines == 1
    assert result.changed


def test_chords_land_on_the_right_columns():
    result = convert("G     C\nHello world")

    assert result.text == "[G]Hello [C]world"


def test_chords_beyond_the_lyric_are_appended():
    result = convert("G          C\nShort")

    assert result.text == "[G]Short[C]"


def test_instrumental_line_becomes_a_chord_run():
    result = convert("G  D  Em  C\n\nG  D  C")

    assert result.text == "[G][D][Em][C]\n\n[G][D][C]"


def test_bar_lines_are_treated_as_instrumental():
    result = convert("| G | D |\nHello")

    assert result.text == "[G][D]\nHello"


def test_existing_chordpro_is_left_alone():
    body = "[G]Amazing [C]grace"

    result = convert(body)

    assert result.text == body
    assert result.already_chordpro is True
    assert result.changed is False


def test_plain_lyrics_are_untouched():
    body = "Amazing grace\nHow sweet the sound"

    result = convert(body)

    assert result.text == body
    assert result.chord_lines == 0


def test_blank_lines_are_preserved():
    result = convert("G\nHello\n\nC\nWorld")

    assert result.text == "[G]Hello\n\n[C]World"


def test_windows_line_endings_are_normalised():
    result = convert("G\r\nHello\r\n")

    assert "\r" not in result.text
    assert result.text == "[G]Hello\n"


def test_mixed_content_keeps_words_intact():
    body = "Verse 1\nG       C\nAmazing grace"

    result = convert(body)

    assert result.text == "Verse 1\n[G]Amazing [C]grace"


@pytest.mark.parametrize("symbol", ["C/H", "C/", "Gm/xyz"])
def test_rejects_a_bass_note_that_is_not_a_note(symbol):
    assert not is_chord(symbol)
