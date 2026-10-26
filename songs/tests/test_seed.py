import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from songs.models import Song, Tag
from songs.seed_data import SONGS

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


def seed(username="max"):
    call_command("seed_songs", "--user", username, verbosity=0)


def test_seed_creates_every_song(max):
    seed()

    assert Song.objects.filter(owner=max).count() == len(SONGS)


def test_seed_is_safe_to_run_twice(max):
    seed()
    seed()

    assert Song.objects.filter(owner=max).count() == len(SONGS)


def test_seed_needs_an_existing_user(max):
    with pytest.raises(CommandError):
        seed("nobody")


def test_seed_attaches_tags(max):
    seed()

    song = Song.objects.get(owner=max, title="Amazing Grace")

    assert set(song.tags.values_list("name", flat=True)) == {"hymn", "waltz", "campfire"}


def test_seed_reuses_a_tag_in_any_case(max):
    Tag.objects.create(owner=max, name="FOLK")

    seed()

    assert Tag.objects.filter(owner=max, name__iexact="folk").count() == 1


def test_seed_includes_both_sheet_formats(max):
    seed()

    formats = set(Song.objects.filter(owner=max).values_list("sheet_format", flat=True))

    assert formats == {Song.SheetFormat.CHORDPRO, Song.SheetFormat.PLAIN}


def test_seed_leaves_other_accounts_alone(max, django_user_model):
    other = django_user_model.objects.create_user("ana", password=PASSWORD)

    seed()

    assert Song.objects.filter(owner=other).count() == 0


@pytest.mark.parametrize("transpose", [0, 2, -2])
def test_every_seeded_sheet_renders(client, max, transpose):
    seed()
    client.force_login(max)

    for song in Song.objects.filter(owner=max):
        url = song.get_absolute_url()
        if transpose:
            url += f"?transpose={transpose}"

        assert client.get(url).status_code == 200, song.title
