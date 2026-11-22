import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from .models import User
from .permissions import IsAdminRole, IsFrontDesk, IsProviderRole

pytestmark = pytest.mark.django_db


def make_user(role):
    return User.objects.create_user(
        email=f"{role}@example.com", password="x-long-password-123", role=role
    )


def allowed(permission_class, user):
    request = APIRequestFactory().get("/")
    request.user = user
    return permission_class().has_permission(request, view=None)


@pytest.mark.parametrize(
    "permission_class, role, expected",
    [
        (IsAdminRole, "admin", True),
        (IsAdminRole, "receptionist", False),
        (IsAdminRole, "provider", False),
        (IsFrontDesk, "admin", True),
        (IsFrontDesk, "receptionist", True),
        (IsFrontDesk, "provider", False),
        (IsProviderRole, "provider", True),
        (IsProviderRole, "admin", False),
        (IsProviderRole, "receptionist", False),
    ],
)
def test_roles_are_allowed_or_denied(permission_class, role, expected):
    assert allowed(permission_class, make_user(role)) is expected


@pytest.mark.parametrize("permission_class", [IsAdminRole, IsFrontDesk, IsProviderRole])
def test_anonymous_visitors_are_always_denied(permission_class):
    assert allowed(permission_class, AnonymousUser()) is False


@pytest.mark.parametrize("permission_class", [IsAdminRole, IsFrontDesk, IsProviderRole])
def test_disabled_accounts_are_denied(permission_class):
    user = make_user(permission_class.allowed_roles[0].value)
    user.is_active = False
    assert allowed(permission_class, user) is False