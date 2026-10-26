import pytest
from django.urls import reverse

from songs.forms import SongForm
from songs.models import Song, Tag

pytestmark = pytest.mark.django_db

PASSWORD = "pw-for-tests-42"


@pytest.fixture
def max(django_user_model):
    return django_user_model.objects.create_user("max", password=PASSWORD)


@pytest.fixture
def ana(django_user_model):
    return django_user_model.objects.create_user("ana", password=PASSWORD)


@pytest.fixture
def song(max):
    return Song.objects.create(
        owner=max,
        title="Amazing Grace",
        artist="Traditional",
        song_key="G",
        capo=2,
        sheet_body="[G]Amazing [C]grace",
    )


def payload(**overrides):
    return {
        "title": "House of the Rising Sun",
        "artist": "Traditional",
        "status": Song.Status.LEARNING,
        "song_key": "A",
        "mode": Song.Mode.MINOR,
        "capo": 0,
        "tempo": 120,
        "time_signature": "6/8",
        "tuning": "Standard",
        "sheet_format": Song.SheetFormat.CHORDPRO,
        "sheet_body": "[Am]There is a [C]house in [D]New Or[F]leans",
        "source_url": "",
        "notes": "",
        "tags_input": "folk, campfire",
        **overrides,
    }


# ---------- create ----------


def test_create_requires_login(client):
    response = client.get(reverse("songs:song_create"))

    assert response.status_code == 302


def test_create_form_renders(client, max):
    client.force_login(max)

    response = client.get(reverse("songs:song_create"))

    assert response.status_code == 200
    assert "ChordPro" in response.content.decode()


def test_create_saves_song_and_redirects_to_it(client, max):
    client.force_login(max)

    response = client.post(reverse("songs:song_create"), payload())

    song = Song.objects.get(title="House of the Rising Sun")
    assert response.status_code == 302
    assert response.url == song.get_absolute_url()
    assert song.owner == max
    assert song.mode == Song.Mode.MINOR


def test_create_attaches_tags(client, max):
    client.force_login(max)

    client.post(reverse("songs:song_create"), payload(tags_input="folk, campfire, folk"))

    song = Song.objects.get(title="House of the Rising Sun")
    assert sorted(song.tags.values_list("name", flat=True)) == ["campfire", "folk"]
    assert Tag.objects.filter(owner=max).count() == 2


def test_create_reuses_existing_tag_case_insensitively(client, max):
    Tag.objects.create(owner=max, name="Folk")
    client.force_login(max)

    client.post(reverse("songs:song_create"), payload(tags_input="folk"))

    assert Tag.objects.filter(owner=max, name__iexact="folk").count() == 1


def test_create_does_not_reuse_another_users_tag(client, max, ana):
    foreign = Tag.objects.create(owner=ana, name="folk")
    client.force_login(max)

    client.post(reverse("songs:song_create"), payload(tags_input="folk"))

    song = Song.objects.get(title="House of the Rising Sun")
    assert foreign not in song.tags.all()
    assert Tag.objects.filter(owner=max, name="folk").exists()


def test_create_requires_title(client, max):
    client.force_login(max)

    response = client.post(reverse("songs:song_create"), payload(title=""))

    assert response.status_code == 200
    assert not Song.objects.exists()


def test_create_rejects_capo_out_of_range(client, max):
    client.force_login(max)

    response = client.post(reverse("songs:song_create"), payload(capo=15))

    assert response.status_code == 200
    assert not Song.objects.exists()


def test_create_accepts_plain_sheet(client, max):
    client.force_login(max)

    client.post(
        reverse("songs:song_create"),
        payload(sheet_format=Song.SheetFormat.PLAIN, sheet_body="G       C\nAmazing grace"),
    )

    song = Song.objects.get(title="House of the Rising Sun")
    assert song.sheet_format == Song.SheetFormat.PLAIN


# ---------- detail ----------


def test_detail_requires_login(client, song):
    response = client.get(song.get_absolute_url())

    assert response.status_code == 302


def test_detail_renders_sheet_and_metadata(client, max, song):
    client.force_login(max)

    content = client.get(song.get_absolute_url()).content.decode()

    assert "Amazing Grace" in content
    assert ">G<" in content
    assert ">Amazing <" in content
    assert "Capo 2" in content


def test_detail_is_scoped_to_owner(client, ana, song):
    client.force_login(ana)

    response = client.get(song.get_absolute_url())

    assert response.status_code == 404


def test_detail_plain_sheet_is_not_parsed(client, max):
    song = Song.objects.create(
        owner=max,
        title="Plain",
        sheet_format=Song.SheetFormat.PLAIN,
        sheet_body="G       C\nAmazing grace",
    )
    client.force_login(max)

    content = client.get(song.get_absolute_url()).content.decode()

    assert "chord-sheet--plain" in content


# ---------- update ----------


def test_update_changes_fields(client, max, song):
    client.force_login(max)

    response = client.post(
        reverse("songs:song_update", args=[song.pk]),
        payload(title="Amazing Grace (revised)", capo=4),
    )

    song.refresh_from_db()
    assert response.status_code == 302
    assert song.title == "Amazing Grace (revised)"
    assert song.capo == 4


def test_update_is_scoped_to_owner(client, ana, song):
    client.force_login(ana)

    response = client.post(
        reverse("songs:song_update", args=[song.pk]),
        payload(title="Hijacked"),
    )

    assert response.status_code == 404
    song.refresh_from_db()
    assert song.title == "Amazing Grace"


def test_update_prefills_tags(client, max, song):
    tag = Tag.objects.create(owner=max, name="folk")
    song.tags.add(tag)
    client.force_login(max)

    content = client.get(reverse("songs:song_update", args=[song.pk])).content.decode()

    assert 'value="folk"' in content


# ---------- delete ----------


def test_delete_get_shows_confirmation(client, max, song):
    client.force_login(max)

    response = client.get(reverse("songs:song_delete", args=[song.pk]))

    assert response.status_code == 200
    assert "Delete this song?" in response.content.decode()


def test_delete_removes_song(client, max, song):
    client.force_login(max)

    response = client.post(reverse("songs:song_delete", args=[song.pk]))

    assert response.status_code == 302
    assert not Song.objects.filter(pk=song.pk).exists()


def test_delete_is_scoped_to_owner(client, ana, song):
    client.force_login(ana)

    response = client.post(reverse("songs:song_delete", args=[song.pk]))

    assert response.status_code == 404
    assert Song.objects.filter(pk=song.pk).exists()


def test_delete_requires_post(client, max, song):
    client.force_login(max)

    client.get(reverse("songs:song_delete", args=[song.pk]))

    assert Song.objects.filter(pk=song.pk).exists()


# ---------- form unit tests ----------


def test_form_dedupes_tags(max):
    form = SongForm(data=payload(tags_input="Folk, folk, FOLK, blues"), owner=max)

    assert form.is_valid()
    assert form.cleaned_data["tags_input"] == ["Folk", "blues"]


def test_form_rejects_too_many_tags(max):
    form = SongForm(data=payload(tags_input=", ".join(f"tag{i}" for i in range(20))), owner=max)

    assert not form.is_valid()
    assert "tags_input" in form.errors


def test_form_rejects_overlong_tag(max):
    form = SongForm(data=payload(tags_input="x" * 60), owner=max)

    assert not form.is_valid()
    assert "tags_input" in form.errors
