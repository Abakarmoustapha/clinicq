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


def book(provider, service, start_at, name="Amina Ali", status=Booking.Status.BOOKED):
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=20),
        patient_name=name,
        patient_phone="+23566123456",
        status=status,
    )


def names(response):
    return [b["patient_name"] for b in response.json()["bookings"]]


# --- the list ---------------------------------------------------------------


def test_reception_sees_every_providers_bookings(reception, doctor_a, doctor_b, service):
    book(doctor_a, service, today_at(10), name="Amina Ali")
    book(doctor_b, service, today_at(11), name="Omar Said")
    response = logged_in(reception).get(reverse("staff-booking-list"))
    assert response.status_code == 200
    assert names(response) == ["Amina Ali", "Omar Said"]
    assert response.json()["bookings"][0]["patient_phone"] == "+23566123456"


def test_admin_sees_every_providers_bookings(doctor_a, doctor_b, service):
    admin = make_user("admin@example.com", User.Role.ADMIN)
    book(doctor_a, service, today_at(10))
    book(doctor_b, service, today_at(11))
    response = logged_in(admin).get(reverse("staff-booking-list"))
    assert len(response.json()["bookings"]) == 2


def test_provider_sees_only_their_own_patients(doctor_a, doctor_b, service):
    book(doctor_a, service, today_at(10), name="Amina Ali")
    book(doctor_b, service, today_at(11), name="Omar Said")
    response = logged_in(doctor_a.user).get(reverse("staff-booking-list"))
    assert names(response) == ["Amina Ali"]


def test_provider_cannot_read_another_providers_patients_with_a_filter(
    doctor_a, doctor_b, service
):
    book(doctor_b, service, today_at(11), name="Omar Said")
    response = logged_in(doctor_a.user).get(
        reverse("staff-booking-list"), {"provider": doctor_b.pk}
    )
    assert response.status_code == 200
    assert response.json()["bookings"] == []


def test_list_shows_only_the_requested_day(reception, doctor_a, service):
    tomorrow = timezone.localdate() + timedelta(days=1)
    book(doctor_a, service, today_at(10), name="Today Patient")
    book(doctor_a, service, today_at(10) + timedelta(days=1), name="Tomorrow Patient")
    client = logged_in(reception)
    today_response = client.get(reverse("staff-booking-list"))
    tomorrow_response = client.get(
        reverse("staff-booking-list"), {"date": tomorrow.isoformat()}
    )
    assert names(today_response) == ["Today Patient"]
    assert names(tomorrow_response) == ["Tomorrow Patient"]


def test_strangers_cannot_read_the_list(client):
    assert client.get(reverse("staff-booking-list")).status_code == 403


def test_bad_date_gives_400(reception):
    response = logged_in(reception).get(reverse("staff-booking-list"), {"date": "abc"})
    assert response.status_code == 400


# --- check-in ---------------------------------------------------------------


def check_in_url(code):
    return reverse("staff-check-in", args=[code])


def test_reception_can_check_in_a_booked_patient(reception, doctor_a, service):
    booking = book(doctor_a, service, today_at(12))
    response = logged_in(reception).post(check_in_url(booking.code))
    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CHECKED_IN


def test_provider_cannot_check_in(doctor_a, service):
    booking = book(doctor_a, service, today_at(12))
    response = logged_in(doctor_a.user).post(check_in_url(booking.code))
    assert response.status_code == 403
    booking.refresh_from_db()
    assert booking.status == Booking.Status.BOOKED


def test_strangers_cannot_check_in(client, doctor_a, service):
    booking = book(doctor_a, service, today_at(12))
    assert client.post(check_in_url(booking.code)).status_code == 403


def test_cannot_check_in_twice(reception, doctor_a, service):
    booking = book(doctor_a, service, today_at(12))
    client = logged_in(reception)
    assert client.post(check_in_url(booking.code)).status_code == 200
    assert client.post(check_in_url(booking.code)).status_code == 409


def test_unknown_code_gives_404(reception):
    response = logged_in(reception).post(check_in_url("ZZZZZZZZ"))
    assert response.status_code == 404


def test_cancelled_booking_cannot_be_checked_in(reception, doctor_a, service):
    booking = book(doctor_a, service, today_at(12), status=Booking.Status.CANCELLED)
    assert logged_in(reception).post(check_in_url(booking.code)).status_code == 409


def test_cannot_check_in_on_another_day(reception, doctor_a, service):
    booking = book(doctor_a, service, today_at(12) + timedelta(days=1))
    assert logged_in(reception).post(check_in_url(booking.code)).status_code == 409


def test_check_in_needs_a_csrf_token(reception, doctor_a, service):
    booking = book(doctor_a, service, today_at(12))
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(reception)
    assert strict.post(check_in_url(booking.code)).status_code == 403


# --- no-show ----------------------------------------------------------------


def no_show_url(code):
    return reverse("staff-no-show", args=[code])


def test_no_show_after_the_waiting_time(reception, doctor_a, service):
    booking = book(doctor_a, service, timezone.now() - timedelta(minutes=30))
    response = logged_in(reception).post(no_show_url(booking.code))
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.NO_SHOW


def test_no_show_is_refused_before_the_waiting_time(reception, doctor_a, service):
    booking = book(doctor_a, service, timezone.now() + timedelta(hours=1))
    response = logged_in(reception).post(no_show_url(booking.code))
    assert response.status_code == 409
    booking.refresh_from_db()
    assert booking.status == Booking.Status.BOOKED


def test_provider_cannot_mark_no_show(doctor_a, service):
    booking = book(doctor_a, service, timezone.now() - timedelta(minutes=30))
    assert logged_in(doctor_a.user).post(no_show_url(booking.code)).status_code == 403


def test_checked_in_patient_cannot_be_marked_no_show(reception, doctor_a, service):
    booking = book(
        doctor_a,
        service,
        timezone.now() - timedelta(minutes=30),
        status=Booking.Status.CHECKED_IN,
    )
    assert logged_in(reception).post(no_show_url(booking.code)).status_code == 409