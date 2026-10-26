import pytest

from songs.models import Song, Tag

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


def test_tag_reads_as_its_name(max):
    tag = Tag.objects.create(owner=max, name="folk")

    assert str(tag) == "folk"


def test_tag_names_are_trimmed_on_save(max):
    tag = Tag.objects.create(owner=max, name="  folk  ")

    assert tag.name == "folk"


def test_song_without_an_artist_reads_as_the_title(max):
    song = Song.objects.create(owner=max, title="Shady Grove")

    assert str(song) == "Shady Grove"


def test_song_with_an_artist_reads_as_title_and_artist(max):
    song = Song.objects.create(owner=max, title="Shenandoah", artist="Traditional")

    assert str(song) == "Shenandoah — Traditional"


def test_display_key_marks_the_minor_ones(max):
    minor = Song.objects.create(owner=max, title="Wayfaring Stranger", song_key="A", mode=Song.Mode.MINOR)
    major = Song.objects.create(owner=max, title="Shenandoah", song_key="D")
    blank = Song.objects.create(owner=max, title="Untitled")

    assert minor.display_key == "Am"
    assert major.display_key == "D"
    assert blank.display_key == ""
