import re

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
    return Song.objects.create(owner=max, title="Amazing Grace", song_key="G")


def rate_url(song):
    return reverse("songs:song_rate", args=[song.pk])


def test_rate_sets_value(client, max, song):
    client.force_login(max)

    response = client.post(rate_url(song), {"rating": "4"})

    song.refresh_from_db()
    assert response.status_code == 302
    assert song.rating == 4


def test_rate_clears_value(client, max, song):
    song.rating = 3
    song.save()
    client.force_login(max)

    client.post(rate_url(song), {"rating": ""})

    song.refresh_from_db()
    assert song.rating is None


@pytest.mark.parametrize("value", ["0", "6", "-1", "abc", "3.5"])
def test_rate_rejects_bad_values(client, max, song, value):
    client.force_login(max)

    response = client.post(rate_url(song), {"rating": value})

    song.refresh_from_db()
    assert response.status_code == 400
    assert song.rating is None


def test_rate_is_owner_scoped(client, song, django_user_model):
    other = django_user_model.objects.create_user("ana", password=PASSWORD)
    client.force_login(other)

    response = client.post(rate_url(song), {"rating": "5"})

    assert response.status_code == 404
    song.refresh_from_db()
    assert song.rating is None


def test_rate_requires_login(client, song):
    response = client.post(rate_url(song), {"rating": "5"})

    assert response.status_code == 302


def test_rate_requires_post(client, max, song):
    client.force_login(max)

    assert client.get(rate_url(song)).status_code == 405


def test_detail_shows_current_rating(client, max, song):
    song.rating = 4
    song.save()
    client.force_login(max)

    content = client.get(song.get_absolute_url()).content.decode()

    input_tag = re.search(r'<input[^>]*value="4"[^>]*>', content)
    assert input_tag is not None
    assert "checked" in input_tag.group(0)


def test_library_shows_stars(client, max, song):
    song.rating = 5
    song.save()
    client.force_login(max)

    content = client.get(reverse("songs:song_list")).content.decode()

    assert "★★★★★" in content


def test_rating_stars_property(song):
    assert song.rating_stars == ""
    song.rating = 3
    assert song.rating_stars == "★★★☆☆"
