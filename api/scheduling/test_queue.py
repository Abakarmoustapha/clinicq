from datetime import datetime, time, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Booking, Provider

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"


def make_user(email, role):
    return User.objects.create_user(email=email, password=PASSWORD, role=role)


@pytest.fixture
def doctor_a(service):
    user = make_user("a@example.com", User.Role.PROVIDER)
    provider = Provider.objects.create(name="Dr. A", user=user)
    provider.services.add(service)
    return provider


@pytest.fixture
def doctor_b(service):
    user = make_user("b@example.com", User.Role.PROVIDER)
    provider = Provider.objects.create(name="Dr. B", user=user)
    provider.services.add(service)
    return provider


@pytest.fixture
def reception():
    return make_user("reception@example.com", User.Role.RECEPTIONIST)


def logged_in(user):
    client = Client()
    client.force_login(user)
    return client


def today_at(hour, minute=0):
    return timezone.make_aware(
        datetime.combine(timezone.localdate(), time(hour, minute))
    )


def patient(
    provider,
    service,
    name,
    slot,
    arrived,
    status=Booking.Status.CHECKED_IN,
    walk_in=False,
    day_offset=0,
):
    """A patient who arrived `arrived` minutes after 07:00 (on today, or another day)."""
    start = today_at(6, 0) + timedelta(minutes=20 * slot)
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start,
        end_at=start + timedelta(minutes=20),
        patient_name=name,
        patient_phone="+23566123456",
        status=status,
        is_walk_in=walk_in,
        checked_in_at=today_at(7, 0)
        + timedelta(minutes=arrived)
        + timedelta(days=day_offset),
    )


def queue_of(client, **params):
    return client.get(reverse("staff-queue"), params)


def waiting_names(response):
    return [p["patient_name"] for p in response.json()["waiting"]]


def call_next(client):
    return client.post(reverse("staff-call-next"))


def done(client, code):
    return client.post(reverse("staff-done", args=[code]))


# --- reading the queue ------------------------------------------------------


def test_waiting_patients_are_ordered_by_arrival(doctor_a, service):
    patient(doctor_a, service, "Late Booked", slot=0, arrived=5)
    patient(doctor_a, service, "Early Booked", slot=1, arrived=1)
    patient(doctor_a, service, "Walk In", slot=2, arrived=3, walk_in=True)
    response = queue_of(logged_in(doctor_a.user))
    assert response.status_code == 200
    assert waiting_names(response) == ["Early Booked", "Walk In", "Late Booked"]
    assert [p["position"] for p in response.json()["waiting"]] == [1, 2, 3]


def test_patient_with_the_provider_is_shown_apart(doctor_a, service):
    patient(
        doctor_a, service, "In Room", slot=0, arrived=1,
        status=Booking.Status.IN_PROGRESS,
    )
    patient(doctor_a, service, "Waiting", slot=1, arrived=2)
    body = queue_of(logged_in(doctor_a.user)).json()
    assert body["in_progress"]["patient_name"] == "In Room"
    assert [p["patient_name"] for p in body["waiting"]] == ["Waiting"]


def test_provider_sees_only_their_own_queue(doctor_a, doctor_b, service):
    patient(doctor_a, service, "Mine", slot=0, arrived=1)
    patient(doctor_b, service, "Not Mine", slot=0, arrived=1)
    assert waiting_names(queue_of(logged_in(doctor_a.user))) == ["Mine"]


def test_provider_cannot_read_another_queue_with_a_filter(doctor_a, doctor_b, service):
    patient(doctor_b, service, "Not Mine", slot=0, arrived=1)
    response = queue_of(logged_in(doctor_a.user), provider=doctor_b.pk)
    assert response.status_code == 200
    assert waiting_names(response) == []


def test_reception_must_say_which_provider(reception):
    assert queue_of(logged_in(reception)).status_code == 400


def test_reception_can_read_a_providers_queue(reception, doctor_a, service):
    patient(doctor_a, service, "Amina Ali", slot=0, arrived=1)
    response = queue_of(logged_in(reception), provider=doctor_a.pk)
    assert waiting_names(response) == ["Amina Ali"]


def test_strangers_cannot_read_a_queue(client, doctor_a):
    response = client.get(reverse("staff-queue"), {"provider": doctor_a.pk})
    assert response.status_code == 403


def test_patients_from_other_days_are_not_in_todays_queue(doctor_a, service):
    patient(doctor_a, service, "Yesterday", slot=0, arrived=1, day_offset=-1)
    patient(doctor_a, service, "Today", slot=1, arrived=1)
    assert waiting_names(queue_of(logged_in(doctor_a.user))) == ["Today"]


# --- calling the next patient -----------------------------------------------


def test_call_next_calls_the_patient_who_arrived_first(doctor_a, service):
    first = patient(doctor_a, service, "First", slot=0, arrived=1)
    patient(doctor_a, service, "Second", slot=1, arrived=2)
    response = call_next(logged_in(doctor_a.user))
    assert response.status_code == 200
    assert response.json()["code"] == first.code
    first.refresh_from_db()
    assert first.status == Booking.Status.IN_PROGRESS


def test_call_next_is_refused_while_a_patient_is_with_the_provider(doctor_a, service):
    patient(
        doctor_a, service, "In Room", slot=0, arrived=1,
        status=Booking.Status.IN_PROGRESS,
    )
    waiting = patient(doctor_a, service, "Waiting", slot=1, arrived=2)
    assert call_next(logged_in(doctor_a.user)).status_code == 409
    waiting.refresh_from_db()
    assert waiting.status == Booking.Status.CHECKED_IN


def test_call_next_with_nobody_waiting_gives_409(doctor_a):
    assert call_next(logged_in(doctor_a.user)).status_code == 409


def test_call_next_never_takes_another_providers_patient(doctor_a, doctor_b, service):
    other = patient(doctor_b, service, "Not Mine", slot=0, arrived=1)
    assert call_next(logged_in(doctor_a.user)).status_code == 409
    other.refresh_from_db()
    assert other.status == Booking.Status.CHECKED_IN


def test_reception_cannot_call_next(reception, doctor_a, service):
    patient(doctor_a, service, "Waiting", slot=0, arrived=1)
    assert call_next(logged_in(reception)).status_code == 403


def test_strangers_cannot_call_next(client):
    assert call_next(client).status_code == 403


def test_provider_without_a_profile_gets_409():
    lonely = make_user("lonely@example.com", User.Role.PROVIDER)
    assert call_next(logged_in(lonely)).status_code == 409


def test_call_next_needs_a_csrf_token(doctor_a, service):
    patient(doctor_a, service, "Waiting", slot=0, arrived=1)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(doctor_a.user)
    assert call_next(strict).status_code == 403


# --- finishing --------------------------------------------------------------


def test_done_finishes_the_patient_in_the_room(doctor_a, service):
    booking = patient(
        doctor_a, service, "In Room", slot=0, arrived=1,
        status=Booking.Status.IN_PROGRESS,
    )
    response = done(logged_in(doctor_a.user), booking.code)
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.DONE


def test_done_is_refused_for_a_patient_who_is_only_waiting(doctor_a, service):
    booking = patient(doctor_a, service, "Waiting", slot=0, arrived=1)
    assert done(logged_in(doctor_a.user), booking.code).status_code == 409


def test_provider_cannot_finish_another_providers_patient(doctor_a, doctor_b, service):
    booking = patient(
        doctor_b, service, "Not Mine", slot=0, arrived=1,
        status=Booking.Status.IN_PROGRESS,
    )
    assert done(logged_in(doctor_a.user), booking.code).status_code == 404
    booking.refresh_from_db()
    assert booking.status == Booking.Status.IN_PROGRESS


def test_reception_cannot_mark_done(reception, doctor_a, service):
    booking = patient(
        doctor_a, service, "In Room", slot=0, arrived=1,
        status=Booking.Status.IN_PROGRESS,
    )
    assert done(logged_in(reception), booking.code).status_code == 403


def test_done_with_an_unknown_code_gives_404(doctor_a):
    assert done(logged_in(doctor_a.user), "ZZZZZZZZ").status_code == 404


def test_a_whole_sequence_in_the_queue(doctor_a, service):
    first = patient(doctor_a, service, "First", slot=0, arrived=1)
    second = patient(doctor_a, service, "Second", slot=1, arrived=2)
    client = logged_in(doctor_a.user)
    assert call_next(client).json()["code"] == first.code
    assert call_next(client).status_code == 409
    assert done(client, first.code).status_code == 200
    assert call_next(client).json()["code"] == second.code