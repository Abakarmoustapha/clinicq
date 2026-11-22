import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.urls import reverse


def test_api_is_locked_by_default():
    permissions = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    assert permissions == ["rest_framework.permissions.IsAuthenticated"]


@pytest.mark.django_db
def test_responses_carry_basic_security_headers(client):
    response = client.get(reverse("health"))
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"


@pytest.mark.django_db
def test_admin_requires_login(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_production_settings_pass_the_django_deploy_check():
    env = {
        **os.environ,
        "DJANGO_DEBUG": "False",
        "DJANGO_ALLOWED_HOSTS": "clinicq.example.com",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr