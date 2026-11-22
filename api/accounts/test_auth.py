import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from rest_framework.throttling import ScopedRateThrottle

from .models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"
EMAIL = "reception@example.com"


@pytest.fixture
def staff():
    return User.objects.create_user(
        email=EMAIL, password=PASSWORD, role=User.Role.RECEPTIONIST
    )


def login(client, email=EMAIL, password=PASSWORD):
    return client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        content_type="application/json",
    )


def test_staff_can_log_in(client, staff):
    response = login(client)
    assert response.status_code == 200
    assert response.json() == {"email": EMAIL, "role": "receptionist"}
    assert "sessionid" in response.cookies


def test_wrong_password_and_unknown_email_get_the_same_answer(client, staff):
    wrong_password = login(client, password="not-the-password")
    unknown_email = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_disabled_account_cannot_log_in(client, staff):
    staff.is_active = False
    staff.save()
    assert login(client).status_code == 401


def test_me_requires_login(client):
    assert client.get(reverse("auth-me")).status_code == 403


def test_me_returns_the_logged_in_user(client, staff):
    login(client)
    response = client.get(reverse("auth-me"))
    assert response.status_code == 200
    assert response.json()["role"] == "receptionist"


def test_logout_ends_the_session(client, staff):
    login(client)
    assert client.post(reverse("auth-logout")).status_code == 204
    assert client.get(reverse("auth-me")).status_code == 403


def test_login_needs_a_csrf_token(staff):
    strict = Client(enforce_csrf_checks=True)
    response = strict.post(
        reverse("auth-login"),
        {"email": EMAIL, "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_login_works_with_a_csrf_token(staff):
    strict = Client(enforce_csrf_checks=True)
    strict.get(reverse("auth-csrf"))
    token = strict.cookies["csrftoken"].value
    response = strict.post(
        reverse("auth-login"),
        {"email": EMAIL, "password": PASSWORD},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200


def test_too_many_login_attempts_are_throttled(client, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "login", "3/hour")
    for _ in range(3):
        assert login(client, password="wrong").status_code == 401
    assert login(client, password="wrong").status_code == 429


def test_basic_authentication_is_switched_off():
    classes = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    assert classes == ["rest_framework.authentication.SessionAuthentication"]