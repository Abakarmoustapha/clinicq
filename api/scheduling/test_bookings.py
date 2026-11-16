from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Booking, Provider, Service

pytestmark = pytest.mark.django_db


@pytest.fixture
def service():
    return Service.objects.create(name="General consultation", slot_minutes=20)


@pytest.fixture
def provider(service):
    p = Provider.objects.create(name="Dr. Ali")
    p.services.add(service)
    return p


@pytest.fixture
def other_provider(service):
    p = Provider.objects.create(name="Dr. Fatima")
    p.services.add(service)
    return p


@pytest.fixture
def start():
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    return now + timedelta(days=1)


def make_booking(provider, service, start_at, minutes=20, status=Booking.Status.BOOKED):
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=minutes),
        patient_name="Test Patient",
        patient_phone="+23500000000",
        status=status,
    )


def test_booking_gets_a_code(provider, service, start):
    booking = make_booking(provider, service, start)
    assert len(booking.code) == 8


def test_same_slot_same_provider_is_rejected(provider, service, start):
    make_booking(provider, service, start)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_booking(provider, service, start)


def test_overlapping_slot_same_provider_is_rejected(provider, service, start):
    make_booking(provider, service, start)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_booking(provider, service, start + timedelta(minutes=10))


def test_back_to_back_slots_are_allowed(provider, service, start):
    make_booking(provider, service, start)
    second = make_booking(provider, service, start + timedelta(minutes=20))
    assert second.pk is not None


def test_same_time_with_another_provider_is_allowed(
    provider, other_provider, service, start
):
    make_booking(provider, service, start)
    other = make_booking(other_provider, service, start)
    assert other.pk is not None


def test_cancelled_booking_frees_the_slot(provider, service, start):
    first = make_booking(provider, service, start)
    first.status = Booking.Status.CANCELLED
    first.save()
    again = make_booking(provider, service, start)
    assert again.pk is not None


def test_end_must_be_after_start(provider, service, start):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_booking(provider, service, start, minutes=0)