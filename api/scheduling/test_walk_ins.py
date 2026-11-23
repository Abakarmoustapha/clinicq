from datetime import date, datetime, time, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .availability import get_free_slots
from .models import Booking, Provider, Service, WorkingHours

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"
MONDAY = date(2030, 1, 7)
LONG_AGO = timezone.make_aware(datetime(2029, 12, 31, 8, 0))


def make_user(email, role):
    return User.objects.create_user(email=email, password=PASSWORD, role=role)


@pytest.fixture
def reception():
    return make_user("reception@example.com", User.Role.RECEPTIONIST)


@pytest.fixture
def working_today(service):
    provider = Provider.objects.create(name="Dr. Today")
    provider.services.add(service)
    WorkingHours.objects.create(
        provider=provider,
        weekday=timezone.localdate().weekday(),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    return provider


def logged_in(user):
    client = Client()
    client.force_login(user)
    return client


def payload(provider, service, **overrides):
    data = {
        "provider": provider.pk,
        "service": service.pk,
        "patient_name": "Amina Ali",
        "patient_phone": "+235 66 12 34 56",
    }
    data.update(overrides)
    return data


def add_walk_in(client, data):
    return client.post(
        reverse("staff-walk-in"), data, content_type="application/json"
    )


def test_reception_adds_a_walk_in(reception, working_today, service):
    response = add_walk_in(logged_in(reception), payload(working_today, service))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "checked_in"
    assert body["is_walk_in"] is True
    assert body["checked_in_at"] is not None
    assert body["patient_phone"] == "+23566123456"
    assert len(body["code"]) == 8


def test_walk_in_is_allowed_even_when_a_booked_slot_overlaps(
    reception, working_today, service
):
    now = timezone.now()
    Booking.objects.create(
        provider=working_today,
        service=service,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(minutes=15),
        patient_name="Booked Patient",
        patient_phone="+23566123456",
    )
    response = add_walk_in(logged_in(reception), payload(working_today, service))
    assert response.status_code == 201


def test_walk_in_does_not_remove_a_free_slot(provider, service):
    start = timezone.make_aware(datetime.combine(MONDAY, time(9, 0)))
    Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start,
        end_at=start + timedelta(minutes=20),
        patient_name="Walk In",
        patient_phone="+23566123456",
        status=Booking.Status.CHECKED_IN,
        is_walk_in=True,
        checked_in_at=start,
    )
    assert start in get_free_slots(provider, service, MONDAY, now=LONG_AGO)


def test_provider_cannot_add_walk_ins(working_today, service):
    doctor = make_user("doctor@example.com", User.Role.PROVIDER)
    response = add_walk_in(logged_in(doctor), payload(working_today, service))
    assert response.status_code == 403


def test_strangers_cannot_add_walk_ins(client, working_today, service):
    assert add_walk_in(client, payload(working_today, service)).status_code == 403


def test_provider_not_working_today_gives_409(reception, service):
    idle = Provider.objects.create(name="Dr. Idle")
    idle.services.add(service)
    response = add_walk_in(logged_in(reception), payload(idle, service))
    assert response.status_code == 409


def test_provider_who_does_not_offer_the_service_gives_409(reception, working_today):
    other = Service.objects.create(name="X-ray", slot_minutes=30)
    response = add_walk_in(logged_in(reception), payload(working_today, other))
    assert response.status_code == 409


def test_inactive_provider_gives_409(reception, working_today, service):
    working_today.is_active = False
    working_today.save()
    response = add_walk_in(logged_in(reception), payload(working_today, service))
    assert response.status_code == 409


def test_invalid_phone_gives_400(reception, working_today, service):
    data = payload(working_today, service, patient_phone="abc")
    assert add_walk_in(logged_in(reception), data).status_code == 400


def test_invalid_name_gives_400(reception, working_today, service):
    data = payload(working_today, service, patient_name="123")
    assert add_walk_in(logged_in(reception), data).status_code == 400

def test_unknown_provider_gives_400(reception, working_today, service):
    data = payload(working_today, service)
    data["provider"] = 9999
    assert add_walk_in(logged_in(reception), data).status_code == 400

def test_walk_in_needs_a_csrf_token(reception, working_today, service):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(reception)
    response = add_walk_in(strict, payload(working_today, service))
    assert response.status_code == 403


def test_check_in_records_the_arrival_time(reception, working_today, service):
    noon = timezone.make_aware(datetime.combine(timezone.localdate(), time(12, 0)))
    booking = Booking.objects.create(
        provider=working_today,
        service=service,
        start_at=noon,
        end_at=noon + timedelta(minutes=20),
        patient_name="Amina Ali",
        patient_phone="+23566123456",
    )
    response = logged_in(reception).post(
        reverse("staff-check-in", args=[booking.code])
    )
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.checked_in_at is not None


def test_patient_can_follow_a_walk_in_with_the_code(
    client, reception, working_today, service
):
    created = add_walk_in(logged_in(reception), payload(working_today, service))
    code = created.json()["code"]
    response = client.get(reverse("booking-detail", args=[code]))
    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"