from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_returns_ok_when_database_is_up(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_returns_503_when_database_is_down(client):
    with patch("config.views.connection") as fake_connection:
        fake_connection.cursor.side_effect = Exception("database is down")
        response = client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "down"}