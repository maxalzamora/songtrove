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
        artist="Traditional",
        song_key="G",
        capo=2,
        tempo=72,
        notes="Capo on the second fret.",
        sheet_body="[G]Amazing [C]grace",
    )


def print_url(song):
    return reverse("songs:song_print", args=[song.pk])


def test_print_requires_login(client, song):
    response = client.get(print_url(song))

    assert response.status_code == 302
    assert reverse("login") in response.url


def test_print_renders_a_standalone_sheet(client, max, song):
    client.force_login(max)

    content = client.get(print_url(song)).content.decode()

    assert "Amazing Grace" in content
    assert "Traditional" in content
    assert "chord-cell__chord" in content
    assert ">G<" in content
    # No site chrome: this page is meant for paper.
    assert "site-header" not in content
    assert "site-footer" not in content


def test_print_shows_key_capo_and_tempo(client, max, song):
    client.force_login(max)

    content = client.get(print_url(song)).content.decode()

    assert "Key G" in content
    assert "Capo 2" in content
    assert "Sounds in A" in content
    assert "72 bpm" in content


def test_print_includes_notes(client, max, song):
    client.force_login(max)

    content = client.get(print_url(song)).content.decode()

    assert "Capo on the second fret." in content


def test_print_honours_transpose(client, max, song):
    client.force_login(max)

    content = client.get(print_url(song) + "?transpose=-2").content.decode()

    assert "Key F" in content
    assert ">F<" in content


def test_print_is_owner_scoped(client, song, django_user_model):
    other = django_user_model.objects.create_user("ana", password=PASSWORD)
    client.force_login(other)

    assert client.get(print_url(song)).status_code == 404


def test_print_handles_a_missing_sheet(client, max):
    song = Song.objects.create(owner=max, title="Empty")
    client.force_login(max)

    content = client.get(print_url(song)).content.decode()

    assert "No sheet yet." in content


def test_print_renders_plain_sheets_verbatim(client, max):
    song = Song.objects.create(
        owner=max,
        title="Plain",
        sheet_format=Song.SheetFormat.PLAIN,
        sheet_body="G   C\nAmazing grace",
    )
    client.force_login(max)

    content = client.get(print_url(song)).content.decode()

    assert "chord-sheet--plain" in content


def test_detail_links_to_print_and_keeps_the_transpose(client, max, song):
    client.force_login(max)

    content = client.get(song.get_absolute_url() + "?transpose=3").content.decode()

    expected = print_url(song) + "?transpose=3"
    assert expected in content
