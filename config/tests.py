import pytest
from django.db import DatabaseError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_check_is_public_and_reports_ok(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.content == b"ok"


def test_health_check_reports_a_database_outage(client, monkeypatch):
    def unavailable():
        raise DatabaseError("no database here")

    monkeypatch.setattr("config.views.connection.cursor", unavailable)

    response = client.get(reverse("healthz"))

    assert response.status_code == 503
    assert b"database unavailable" in response.content
