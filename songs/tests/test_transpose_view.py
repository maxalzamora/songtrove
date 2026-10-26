import pytest
from django.urls import reverse

from songs.models import Song

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


@pytest.fixture
def song(max):
    return Song.objects.create(
        owner=max,
        title="Amazing Grace",
        song_key="G",
        capo=2,
        sheet_body="[G]Amazing [C]grace",
    )


def detail(client, user, song, query=""):
    client.force_login(user)
    return client.get(song.get_absolute_url() + query).content.decode()


def test_capo_bar_shows_shapes_and_sounding_key(client, max, song):
    content = detail(client, max, song)

    assert "Shapes" in content
    assert "Sounds in" in content
    # G shapes with a capo on 2 sound in A.
    assert ">A<" in content


def test_transpose_down_moves_the_sheet(client, max, song):
    content = detail(client, max, song, "?transpose=-2")

    assert ">F<" in content  # written key
    assert ">G<" in content  # sounding key, F + capo 2
    # The first chord of the sheet moved with it.
    assert "chord-cell__chord\">F<" in content


def test_transpose_up_moves_the_sheet(client, max, song):
    content = detail(client, max, song, "?transpose=2")

    assert ">B<" in content  # written key
    assert "chord-cell__chord\">A<" in content  # first chord


def test_transpose_is_normalised(client, max, song):
    content = detail(client, max, song, "?transpose=14")

    # 14 semitones is 2 up, modulo an octave.
    assert ">A<" in content


def test_bad_transpose_falls_back_to_zero(client, max, song):
    content = detail(client, max, song, "?transpose=nonsense")

    assert "chord-cell__chord\">G<" in content


def test_reset_link_appears_only_after_transposing(client, max, song):
    assert ">Reset</a>" not in detail(client, max, song)
    assert ">Reset</a>" in detail(client, max, song, "?transpose=3")


def test_plain_sheets_cannot_be_transposed(client, max):
    song = Song.objects.create(
        owner=max,
        title="Plain",
        song_key="G",
        capo=0,
        sheet_format=Song.SheetFormat.PLAIN,
        sheet_body="G   C\nAmazing grace",
    )

    content = detail(client, max, song)

    assert "transpose__value" not in content
    # The capo bar still explains the key.
    assert "Sounds in" in content


def test_song_without_key_has_no_toolbar(client, max):
    song = Song.objects.create(owner=max, title="Untitled", song_key="", capo=0)

    content = detail(client, max, song)

    assert "capo-bar" not in content


def test_transpose_does_not_change_stored_sheet(client, max, song):
    detail(client, max, song, "?transpose=5")

    song.refresh_from_db()
    assert song.sheet_body == "[G]Amazing [C]grace"
    assert song.song_key == "G"
