from datetime import datetime, time, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import User

from .models import Booking, Provider

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"


def today_at(hour, minute=0):
    return timezone.make_aware(
        datetime.combine(timezone.localdate(), time(hour, minute))
    )


@pytest.fixture
def doctor(service):
    user = User.objects.create_user(
        email="doctor@example.com", password=PASSWORD, role=User.Role.PROVIDER
    )
    provider = Provider.objects.create(name="Dr. A", user=user)
    provider.services.add(service)
    return provider


@pytest.fixture
def other_doctor(service):
    provider = Provider.objects.create(name="Dr. B")
    provider.services.add(service)
    return provider


def patient(
    provider,
    service,
    name,
    slot,
    arrived,
    status=Booking.Status.CHECKED_IN,
    day_offset=0,
):
    """A patient who arrived `arrived` minutes after 07:00."""
    start = today_at(6, 0) + timedelta(minutes=20 * slot)
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start,
        end_at=start + timedelta(minutes=20),
        patient_name=name,
        patient_phone="+23566123456",
        status=status,
        checked_in_at=today_at(7, 0)
        + timedelta(minutes=arrived)
        + timedelta(days=day_offset),
    )


def finished(provider, service, name, slot, minutes):
    """A consultation that lasted `minutes` and ended today."""
    start = today_at(6, 0) + timedelta(minutes=20 * slot)
    called = today_at(8, 0) + timedelta(minutes=30 * slot)
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start,
        end_at=start + timedelta(minutes=20),
        patient_name=name,
        patient_phone="+23566123456",
        status=Booking.Status.DONE,
        checked_in_at=today_at(7, 0),
        called_at=called,
        finished_at=called + timedelta(minutes=minutes),
    )


def status_of(client, code):
    return client.get(reverse("booking-queue", args=[code]))


def test_position_people_ahead_and_wait_for_the_third_patient(client, doctor, service):
    patient(doctor, service, "One", slot=0, arrived=1)
    patient(doctor, service, "Two", slot=1, arrived=2)
    third = patient(doctor, service, "Three", slot=2, arrived=3)
    body = status_of(client, third.code).json()
    assert body["position"] == 3
    assert body["people_ahead"] == 2
    assert body["estimated_wait_minutes"] == 40


def test_the_first_patient_does_not_wait(client, doctor, service):
    first = patient(doctor, service, "One", slot=0, arrived=1)
    body = status_of(client, first.code).json()
    assert body["position"] == 1
    assert body["people_ahead"] == 0
    assert body["estimated_wait_minutes"] == 0


def test_the_patient_in_the_room_counts_as_ahead(client, doctor, service):
    patient(doctor, service, "In Room", slot=0, arrived=1, status=Booking.Status.IN_PROGRESS)
    mine = patient(doctor, service, "Mine", slot=1, arrived=2)
    body = status_of(client, mine.code).json()
    assert body["position"] == 1
    assert body["people_ahead"] == 1
    assert body["estimated_wait_minutes"] == 20


def test_estimate_uses_the_real_length_of_recent_consultations(client, doctor, service):
    for slot in (10, 11, 12):
        finished(doctor, service, f"Done {slot}", slot=slot, minutes=10)
    patient(doctor, service, "One", slot=0, arrived=1)
    patient(doctor, service, "Two", slot=1, arrived=2)
    third = patient(doctor, service, "Three", slot=2, arrived=3)
    body = status_of(client, third.code).json()
    assert body["estimated_wait_minutes"] == 20


def test_very_quick_consultations_do_not_promise_a_zero_wait(client, doctor, service):
    for slot in (10, 11, 12):
        finished(doctor, service, f"Done {slot}", slot=slot, minutes=1)
    patient(doctor, service, "One", slot=0, arrived=1)
    patient(doctor, service, "Two", slot=1, arrived=2)
    third = patient(doctor, service, "Three", slot=2, arrived=3)
    body = status_of(client, third.code).json()
    assert body["estimated_wait_minutes"] == 10


def test_with_too_few_finished_consultations_the_slot_length_is_used(
    client, doctor, service
):
    for slot in (10, 11):
        finished(doctor, service, f"Done {slot}", slot=slot, minutes=10)
    patient(doctor, service, "One", slot=0, arrived=1)
    patient(doctor, service, "Two", slot=1, arrived=2)
    third = patient(doctor, service, "Three", slot=2, arrived=3)
    body = status_of(client, third.code).json()
    assert body["estimated_wait_minutes"] == 40


@pytest.mark.parametrize(
    "status",
    [
        Booking.Status.BOOKED,
        Booking.Status.IN_PROGRESS,
        Booking.Status.DONE,
        Booking.Status.CANCELLED,
        Booking.Status.NO_SHOW,
    ],
)
def test_only_waiting_patients_get_a_position(client, doctor, service, status):
    booking = patient(doctor, service, "Amina Ali", slot=0, arrived=1, status=status)
    body = status_of(client, booking.code).json()
    assert body["status"] == status
    assert body["position"] is None
    assert body["people_ahead"] is None
    assert body["estimated_wait_minutes"] is None


def test_other_providers_patients_do_not_count(client, doctor, other_doctor, service):
    patient(other_doctor, service, "Elsewhere", slot=0, arrived=1)
    mine = patient(doctor, service, "Mine", slot=1, arrived=2)
    assert status_of(client, mine.code).json()["position"] == 1


def test_a_check_in_from_yesterday_gets_no_position(client, doctor, service):
    old = patient(doctor, service, "Old", slot=0, arrived=1, day_offset=-1)
    body = status_of(client, old.code).json()
    assert body["status"] == "checked_in"
    assert body["position"] is None


def test_unknown_code_gives_404(client):
    assert status_of(client, "ZZZZZZZZ").status_code == 404


def test_code_is_not_case_sensitive(client, doctor, service):
    booking = patient(doctor, service, "Amina Ali", slot=0, arrived=1)
    assert status_of(client, booking.code.lower()).status_code == 200


def test_the_answer_never_contains_personal_data(client, doctor, service):
    booking = patient(doctor, service, "Amina Ali", slot=0, arrived=1)
    response = status_of(client, booking.code)
    text = response.content.decode()
    assert "Amina" not in text
    assert "+23566123456" not in text
    for key in ("patient_name", "patient_phone", "patient_email"):
        assert key not in response.json()




def test_call_next_and_done_record_their_times(doctor, service):
    waiting = patient(doctor, service, "Amina Ali", slot=0, arrived=1)
    staff = Client()
    staff.force_login(doctor.user)
    staff.post(reverse("staff-call-next"))
    waiting.refresh_from_db()
    assert waiting.called_at is not None
    assert waiting.finished_at is None
    staff.post(reverse("staff-done", args=[waiting.code]))
    waiting.refresh_from_db()
    assert waiting.finished_at is not None