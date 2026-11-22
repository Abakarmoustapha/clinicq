import pytest
from django.db import IntegrityError, transaction

from accounts.models import User

from .models import Provider

pytestmark = pytest.mark.django_db


def make_doctor(email="doctor@example.com"):
    return User.objects.create_user(
        email=email, password="x-long-password-123", role=User.Role.PROVIDER
    )


def test_provider_can_be_linked_to_a_staff_account():
    doctor = make_doctor()
    provider = Provider.objects.create(name="Dr. Ali", user=doctor)
    assert doctor.provider_profile == provider


def test_one_account_cannot_be_two_providers():
    doctor = make_doctor()
    Provider.objects.create(name="Dr. Ali", user=doctor)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Provider.objects.create(name="Dr. Ali again", user=doctor)


def test_providers_without_an_account_are_allowed():
    assert Provider.objects.create(name="Dr. Walk-in").user is None