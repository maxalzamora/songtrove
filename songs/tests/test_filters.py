import pytest
from django.urls import reverse

from songs.models import Song, Tag

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


@pytest.fixture
def library(max):
    grace = Song.objects.create(
        owner=max,
        title="Amazing Grace",
        artist="Traditional",
        song_key="G",
        capo=2,
        rating=4,
        status=Song.Status.GIG_READY,
    )
    house = Song.objects.create(
        owner=max,
        title="House of the Rising Sun",
        artist="The Animals",
        song_key="A",
        capo=0,
        rating=2,
        status=Song.Status.LEARNING,
    )
    fair = Song.objects.create(
        owner=max,
        title="Scarborough Fair",
        artist="Traditional",
        song_key="D",
        capo=3,
        rating=None,
        status=Song.Status.IDEA,
    )

    folk = Tag.objects.create(owner=max, name="folk")
    blues = Tag.objects.create(owner=max, name="blues")
    grace.tags.add(folk)
    house.tags.add(folk, blues)

    return {"grace": grace, "house": house, "fair": fair}


def results(client, user, **params):
    client.force_login(user)
    response = client.get(reverse("songs:song_list"), params)
    return response, {song.title for song in response.context["songs"]}


def test_search_by_title(client, max, library):
    _, titles = results(client, max, q="grace")

    assert titles == {"Amazing Grace"}


def test_search_by_artist(client, max, library):
    _, titles = results(client, max, q="animals")

    assert titles == {"House of the Rising Sun"}


def test_search_by_tag(client, max, library):
    _, titles = results(client, max, q="blues")

    assert titles == {"House of the Rising Sun"}


def test_search_is_case_insensitive(client, max, library):
    _, titles = results(client, max, q="AMAZING")

    assert titles == {"Amazing Grace"}


def test_search_does_not_duplicate_rows(client, max, library):
    # Both songs share a tag; a naive join would return duplicates.
    response, titles = results(client, max, q="folk")

    assert titles == {"Amazing Grace", "House of the Rising Sun"}
    assert len(response.context["songs"]) == 2


def test_filter_by_status(client, max, library):
    _, titles = results(client, max, status=Song.Status.IDEA)

    assert titles == {"Scarborough Fair"}


def test_filter_by_key(client, max, library):
    _, titles = results(client, max, key="A")

    assert titles == {"House of the Rising Sun"}


def test_filter_by_capo(client, max, library):
    _, titles = results(client, max, capo="3")

    assert titles == {"Scarborough Fair"}


def test_filter_by_no_capo(client, max, library):
    _, titles = results(client, max, capo="0")

    assert titles == {"House of the Rising Sun"}


def test_filter_by_minimum_rating(client, max, library):
    _, titles = results(client, max, rating="2")

    assert titles == {"Amazing Grace", "House of the Rising Sun"}


def test_filter_by_tag(client, max, library):
    _, titles = results(client, max, tag="BLUES")

    assert titles == {"House of the Rising Sun"}


def test_filters_combine(client, max, library):
    _, titles = results(client, max, q="traditional", status=Song.Status.IDEA)

    assert titles == {"Scarborough Fair"}


def test_combined_filters_can_be_empty(client, max, library):
    response, titles = results(client, max, q="grace", key="A")

    assert titles == set()
    assert response.context["has_filters"] is True


@pytest.mark.parametrize(
    "params",
    [
        {"status": "nonsense"},
        {"key": "H"},
        {"capo": "99"},
        {"capo": "x"},
        {"rating": "9"},
        {"rating": "abc"},
    ],
)
def test_invalid_filters_are_ignored(client, max, library, params):
    response, titles = results(client, max, **params)

    assert len(titles) == 3
    assert response.status_code == 200


def test_filters_never_leak_other_users(client, max, library, django_user_model):
    other = django_user_model.objects.create_user("ana", password=PASSWORD)
    Song.objects.create(owner=other, title="Amazing Grace", artist="Traditional")

    _, titles = results(client, max, q="amazing")

    assert titles == {"Amazing Grace"}
    assert len(titles) == 1


def test_filter_form_shows_active_values(client, max, library):
    client.force_login(max)

    content = client.get(reverse("songs:song_list"), {"status": Song.Status.IDEA}).content.decode()

    assert 'value="idea" selected' in content
    assert "Clear" in content


def test_no_filters_hides_clear(client, max, library):
    client.force_login(max)

    content = client.get(reverse("songs:song_list")).content.decode()

    assert "Clear</a>" not in content


def test_empty_result_has_its_own_state(client, max, library):
    client.force_login(max)

    content = client.get(reverse("songs:song_list"), {"q": "nothing matches this"}).content.decode()

    assert "No songs match those filters" in content
