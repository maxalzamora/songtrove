import pytest
from django.urls import reverse

from songs.models import Song

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"
PLAIN = "G       C\nAmazing grace, how sweet the sound"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


def post_convert(client, user, url, body):
    client.force_login(user)
    return client.post(url, {"action": "convert", "sheet_body": body})


def test_convert_on_create_rewrites_the_form(client, max):
    response = post_convert(client, max, reverse("songs:song_create"), PLAIN)

    assert response.status_code == 200
    form = response.context["form"]
    assert form.initial["sheet_body"] == "[G]Amazing [C]grace, how sweet the sound"
    assert form.initial["sheet_format"] == Song.SheetFormat.CHORDPRO


def test_convert_does_not_create_a_song(client, max):
    post_convert(client, max, reverse("songs:song_create"), PLAIN)

    assert not Song.objects.exists()


def test_convert_keeps_other_typed_values(client, max):
    client.force_login(max)

    response = client.post(
        reverse("songs:song_create"),
        {"action": "convert", "sheet_body": PLAIN, "title": "Amazing Grace", "capo": "2"},
    )

    form = response.context["form"]
    assert form.initial["title"] == "Amazing Grace"
    assert form.initial["capo"] == "2"


def test_convert_reports_how_many_lines_changed(client, max):
    response = post_convert(client, max, reverse("songs:song_create"), PLAIN)

    messages = [str(message) for message in response.context["messages"]]
    assert any("Converted 1 chord line" in message for message in messages)


def test_convert_warns_when_there_is_nothing_to_do(client, max):
    response = post_convert(client, max, reverse("songs:song_create"), "Just lyrics\nNo chords")

    messages = [str(message) for message in response.context["messages"]]
    assert any("No chord lines found" in message for message in messages)


def test_convert_is_a_no_op_for_chordpro(client, max):
    body = "[G]Amazing [C]grace"

    response = post_convert(client, max, reverse("songs:song_create"), body)

    assert response.context["form"].initial["sheet_body"] == body
    messages = [str(message) for message in response.context["messages"]]
    assert any("already looks like ChordPro" in message for message in messages)


def test_convert_on_update_does_not_touch_the_database(client, max):
    song = Song.objects.create(owner=max, title="Amazing Grace", sheet_body="old body")

    response = post_convert(client, max, reverse("songs:song_update", args=[song.pk]), PLAIN)

    song.refresh_from_db()
    assert response.status_code == 200
    assert song.sheet_body == "old body"
    assert response.context["form"].initial["sheet_body"].startswith("[G]Amazing")


def test_convert_is_scoped_to_owner(client, max, django_user_model):
    other = django_user_model.objects.create_user("ana", password=PASSWORD)
    song = Song.objects.create(owner=max, title="Private")
    client.force_login(other)

    response = client.post(
        reverse("songs:song_update", args=[song.pk]),
        {"action": "convert", "sheet_body": PLAIN},
    )

    assert response.status_code == 404
