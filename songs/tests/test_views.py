import pytest
from django.urls import reverse

from songs.models import Song

pytestmark = pytest.mark.django_db


def make_song(owner, **overrides):
    defaults = {
        "title": "Amazing Grace",
        "artist": "Traditional",
        "song_key": "G",
        "capo": 2,
        "sheet_body": "[G]Amazing [C]grace",
    }
    return Song.objects.create(owner=owner, **{**defaults, **overrides})


def test_library_requires_login(client):
    response = client.get(reverse("songs:song_list"))

    assert response.status_code == 302
    assert reverse("login") in response.url


def test_library_shows_only_your_songs(client, django_user_model):
    me = django_user_model.objects.create_user("max", password="pw-for-tests-42")
    someone_else = django_user_model.objects.create_user("ana", password="pw-for-tests-42")
    mine = make_song(me, title="Mine")
    theirs = make_song(someone_else, title="Theirs")
    client.force_login(me)

    response = client.get(reverse("songs:song_list"))
    content = response.content.decode()

    assert mine.title in content
    assert theirs.title not in content


def test_empty_library_has_empty_state(client, django_user_model):
    user = django_user_model.objects.create_user("max", password="pw-for-tests-42")
    client.force_login(user)

    response = client.get(reverse("songs:song_list"))

    assert "No songs yet" in response.content.decode()


def test_library_shows_key_and_capo(client, django_user_model):
    user = django_user_model.objects.create_user("max", password="pw-for-tests-42")
    make_song(user, song_key="Bb", capo=3)
    client.force_login(user)

    content = client.get(reverse("songs:song_list")).content.decode()

    assert ">Bb<" in content
    assert "Capo 3" in content


def test_minor_key_is_labelled(client, django_user_model):
    user = django_user_model.objects.create_user("max", password="pw-for-tests-42")
    make_song(user, song_key="E", mode=Song.Mode.MINOR)
    client.force_login(user)

    content = client.get(reverse("songs:song_list")).content.decode()

    assert ">Em<" in content


def test_layout_ships_a_theme_toggle(client):
    content = client.get(reverse("home")).content.decode()

    assert "data-theme-toggle" in content
    assert "js/theme.js" in content
    # The pre-paint script must know the storage key the toggle writes.
    assert "songtrove-theme" in content
