from datetime import date, datetime, time, timedelta

import pytest
from django.utils import timezone

from .availability import get_free_slots
from .models import Booking, Provider, Service, WorkingHours

pytestmark = pytest.mark.django_db

MONDAY = date(2030, 1, 7)
TUESDAY = date(2030, 1, 8)
LONG_AGO = timezone.make_aware(datetime(2029, 12, 31, 8, 0))


def at(hour, minute=0):
    return timezone.make_aware(datetime.combine(MONDAY, time(hour, minute)))


@pytest.fixture
def service():
    return Service.objects.create(name="General consultation", slot_minutes=20)


@pytest.fixture
def provider(service):
    p = Provider.objects.create(name="Dr. Ali")
    p.services.add(service)
    WorkingHours.objects.create(
        provider=p, weekday=0, start_time=time(9, 0), end_time=time(10, 0)
    )
    return p


def book(provider, service, start_at, status=Booking.Status.BOOKED):
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=service.slot_minutes),
        patient_name="Test Patient",
        patient_phone="+23500000000",
        status=status,
    )


def test_working_hours_become_slots(provider, service):
    slots = get_free_slots(provider, service, MONDAY, now=LONG_AGO)
    assert slots == [at(9, 0), at(9, 20), at(9, 40)]


def test_no_slots_on_a_day_without_working_hours(provider, service):
    assert get_free_slots(provider, service, TUESDAY, now=LONG_AGO) == []


def test_a_slot_must_fit_inside_the_working_hours(provider):
    long_service = Service.objects.create(name="Check-up", slot_minutes=25)
    provider.services.add(long_service)
    slots = get_free_slots(provider, long_service, MONDAY, now=LONG_AGO)
    assert slots == [at(9, 0), at(9, 25)]


def test_booked_slot_is_not_free(provider, service):
    book(provider, service, at(9, 20))
    slots = get_free_slots(provider, service, MONDAY, now=LONG_AGO)
    assert slots == [at(9, 0), at(9, 40)]


def test_cancelled_booking_frees_the_slot(provider, service):
    book(provider, service, at(9, 20), status=Booking.Status.CANCELLED)
    slots = get_free_slots(provider, service, MONDAY, now=LONG_AGO)
    assert slots == [at(9, 0), at(9, 20), at(9, 40)]


def test_past_slots_are_not_offered(provider, service):
    slots = get_free_slots(provider, service, MONDAY, now=at(9, 30))
    assert slots == [at(9, 40)]


def test_bookings_of_other_providers_do_not_matter(provider, service):
    other = Provider.objects.create(name="Dr. Fatima")
    other.services.add(service)
    book(other, service, at(9, 0))
    slots = get_free_slots(provider, service, MONDAY, now=LONG_AGO)
    assert slots == [at(9, 0), at(9, 20), at(9, 40)]


def test_provider_who_does_not_offer_the_service_has_no_slots(provider):
    other_service = Service.objects.create(name="X-ray", slot_minutes=30)
    assert get_free_slots(provider, other_service, MONDAY, now=LONG_AGO) == []