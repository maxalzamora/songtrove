import pytest

from songs.chords import parse_chord, transpose_chord, transpose_key


@pytest.mark.parametrize(
    ("symbol", "semitones", "expected"),
    [
        ("C", 2, "D"),
        ("C", 1, "C#"),
        ("C", -2, "Bb"),
        ("G", 5, "C"),
        ("G", 2, "A"),
        ("F#", 1, "G"),
        ("B", 1, "C"),
        ("Bb", 1, "B"),
        ("Eb", 2, "F"),
        ("C", 12, "C"),
        ("C", -12, "C"),
        ("C", 24, "C"),
    ],
)
def test_transpose_simple_chords(symbol, semitones, expected):
    assert transpose_chord(symbol, semitones) == expected


@pytest.mark.parametrize(
    ("symbol", "semitones", "expected"),
    [
        ("Am7", 2, "Bm7"),
        ("F#m7b5", 1, "Gm7b5"),
        ("Csus4", 2, "Dsus4"),
        ("G7(b9)", 3, "Bb7(b9)"),
        ("Eadd9", 1, "Fadd9"),
    ],
)
def test_qualities_are_preserved(symbol, semitones, expected):
    assert transpose_chord(symbol, semitones) == expected


def test_flat_in_quality_does_not_force_flat_spelling():
    # `7b5` has a flat, but the chord is sharp-flavoured.
    assert transpose_chord("C7b5", 2) == "D7b5"


def test_slash_bass_moves_with_the_chord():
    assert transpose_chord("C/G", 2) == "D/A"
    assert transpose_chord("C/E", 2) == "D/F#"
    assert transpose_chord("Am/G", 2) == "Bm/A"


def test_slash_bass_is_dropped_when_it_lands_on_the_root():
    # A slash bass keeps its interval from the root, so the only way it can
    # become the root note itself is if the source already doubled it.
    assert transpose_chord("C/C", 2) == "D"


def test_prefer_flats_overrides_spelling():
    assert transpose_chord("C", 1, prefer_flats=True) == "Db"
    assert transpose_chord("Db", 1, prefer_flats=False) == "D"


def test_prefer_flats_keeps_flat_root():
    assert transpose_chord("Bb", 3, prefer_flats=True) == "Db"


@pytest.mark.parametrize("symbol", ["N.C.", "NC", "|", "%", "-", "H", "C/H", "", "  ", "C//G"])
def test_non_chords_pass_through(symbol):
    assert transpose_chord(symbol, 3) == symbol


def test_parse_chord_splits_parts():
    chord = parse_chord("F#m7b5/A")

    assert chord is not None
    assert chord.root == "F#"
    assert chord.quality == "m7b5"
    assert chord.bass == "A"


def test_parse_chord_rejects_garbage():
    assert parse_chord("not a chord") is None


@pytest.mark.parametrize(
    ("key", "semitones", "expected"),
    [
        ("G", -2, "F"),
        ("G", 2, "A"),
        ("Bb", 1, "B"),
        ("F#", 1, "G"),
        ("C", 11, "B"),
    ],
)
def test_transpose_key(key, semitones, expected):
    assert transpose_key(key, semitones) == expected


def test_transpose_key_keeps_flat_preference():
    assert transpose_key("Eb", 2) == "F"
    assert transpose_key("Bb", -2) == "Ab"


def test_transpose_unknown_key_is_unchanged():
    assert transpose_key("", 2) == ""
    assert transpose_key("H", 2) == "H"


def test_automatic_spelling_prefers_flats_for_flat_keys():
    # A chord with no accidental of its own lands on the spelling guitarists
    # reach for: Eb and Bb, not D# and A#.
    assert transpose_chord("D", 1) == "Eb"
    assert transpose_chord("A", 1) == "Bb"
    assert transpose_chord("G", 1) == "Ab"
    # Naturals stay natural, and C# keeps its sharp.
    assert transpose_chord("E", 1) == "F"
    assert transpose_chord("C", 1) == "C#"
