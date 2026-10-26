import pytest
from django.urls import reverse

from songs.models import Song

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


def test_admin_song_list_loads_for_a_superuser(client, django_user_model):
    root = django_user_model.objects.create_superuser("root", "root@example.com", PASSWORD)
    Song.objects.create(owner=root, title="Amazing Grace", artist="John Newton")
    client.force_login(root)

    response = client.get(reverse("admin:songs_song_changelist"))

    assert response.status_code == 200
    assert "Amazing Grace" in response.content.decode()


def test_admin_song_change_page_loads(client, django_user_model):
    root = django_user_model.objects.create_superuser("root", "root@example.com", PASSWORD)
    song = Song.objects.create(owner=root, title="Amazing Grace", sheet_body="[G]Amazing grace")
    client.force_login(root)

    response = client.get(reverse("admin:songs_song_change", args=[song.pk]))

    assert response.status_code == 200


def test_admin_is_closed_to_ordinary_users(client, django_user_model):
    django_user_model.objects.create_user("max", password=PASSWORD)
    client.login(username="max", password=PASSWORD)

    response = client.get(reverse("admin:songs_song_changelist"))

    assert response.status_code == 302
    assert reverse("admin:login") in response.url
