import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "correct-horse-battery-42"


def signup_payload(**overrides):
    return {
        "username": "max",
        "email": "max@example.com",
        "password1": STRONG_PASSWORD,
        "password2": STRONG_PASSWORD,
        **overrides,
    }


def test_landing_page_renders(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert "SongTrove" in response.content.decode()


def test_landing_page_redirects_signed_in_users(client, django_user_model):
    user = django_user_model.objects.create_user("max", password=STRONG_PASSWORD)
    client.force_login(user)

    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == reverse("songs:song_list")


def test_signup_page_renders(client):
    response = client.get(reverse("signup"))

    assert response.status_code == 200
    assert "Sign up" in response.content.decode() or "Create account" in response.content.decode()


def test_signup_creates_and_logs_in_user(client, django_user_model):
    response = client.post(reverse("signup"), signup_payload())

    assert response.status_code == 302
    assert response.url == reverse("songs:song_list")
    user = django_user_model.objects.get(username="max")
    assert user.email == "max@example.com"
    assert client.session["_auth_user_id"] == str(user.pk)


def test_signup_lowercases_email(client, django_user_model):
    client.post(reverse("signup"), signup_payload(email="Max@Example.COM"))

    assert django_user_model.objects.get(username="max").email == "max@example.com"


def test_signup_rejects_duplicate_email(client, django_user_model):
    django_user_model.objects.create_user("other", email="max@example.com", password=STRONG_PASSWORD)

    response = client.post(reverse("signup"), signup_payload())

    assert response.status_code == 200
    assert "already exists" in response.content.decode()


def test_signup_rejects_mismatched_passwords(client, django_user_model):
    response = client.post(reverse("signup"), signup_payload(password2="different-password-42"))

    assert response.status_code == 200
    assert not django_user_model.objects.filter(username="max").exists()


def test_signup_rejects_weak_password(client, django_user_model):
    response = client.post(reverse("signup"), signup_payload(password1="short", password2="short"))

    assert response.status_code == 200
    assert not django_user_model.objects.filter(username="max").exists()


def test_signup_redirects_when_already_signed_in(client, django_user_model):
    user = django_user_model.objects.create_user("max", password=STRONG_PASSWORD)
    client.force_login(user)

    response = client.get(reverse("signup"))

    assert response.status_code == 302


def test_login(client, django_user_model):
    django_user_model.objects.create_user("max", password=STRONG_PASSWORD)

    response = client.post(
        reverse("login"),
        {"username": "max", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("songs:song_list")


def test_login_honours_next_parameter(client, django_user_model):
    django_user_model.objects.create_user("max", password=STRONG_PASSWORD)

    response = client.post(
        reverse("login") + "?next=/songs/",
        {"username": "max", "password": STRONG_PASSWORD, "next": "/songs/"},
    )

    assert response.url == "/songs/"


def test_login_with_bad_password(client, django_user_model):
    django_user_model.objects.create_user("max", password=STRONG_PASSWORD)

    response = client.post(reverse("login"), {"username": "max", "password": "nope"})

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_logout_requires_post(client, django_user_model):
    user = django_user_model.objects.create_user("max", password=STRONG_PASSWORD)
    client.force_login(user)

    assert client.get(reverse("logout")).status_code == 405


def test_logout(client, django_user_model):
    user = django_user_model.objects.create_user("max", password=STRONG_PASSWORD)
    client.force_login(user)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert "_auth_user_id" not in client.session
