from datetime import date, datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from .availability import get_free_slots
from .bookings import (
    BookingNotFound,
    NotCancellable,
    cancel_booking,
    create_booking,
)
from .models import Booking

pytestmark = pytest.mark.django_db

MONDAY = date(2030, 1, 7)
LONG_AGO = timezone.make_aware(datetime(2029, 12, 31, 8, 0))
PHONE = "+23566123456"


def at(hour, minute=0):
    return timezone.make_aware(datetime.combine(MONDAY, time(hour, minute)))


def booked(provider, service):
    return create_booking(provider, service, at(9, 0), "Amina", PHONE, now=LONG_AGO)


def test_cancel_marks_booking_cancelled_and_frees_the_slot(provider, service):
    booking = booked(provider, service)
    cancel_booking(booking.code, PHONE, now=LONG_AGO)
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
    assert at(9, 0) in get_free_slots(provider, service, MONDAY, now=LONG_AGO)


def test_wrong_phone_is_treated_as_not_found(provider, service):
    booking = booked(provider, service)
    with pytest.raises(BookingNotFound):
        cancel_booking(booking.code, "+23599999999", now=LONG_AGO)
    booking.refresh_from_db()
    assert booking.status == Booking.Status.BOOKED


def test_unknown_code_is_not_found():
    with pytest.raises(BookingNotFound):
        cancel_booking("ZZZZZZZZ", PHONE, now=LONG_AGO)


def test_code_is_not_case_sensitive(provider, service):
    booking = booked(provider, service)
    cancel_booking(booking.code.lower(), PHONE, now=LONG_AGO)
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED


@pytest.mark.parametrize(
    "status",
    [Booking.Status.CHECKED_IN, Booking.Status.CANCELLED, Booking.Status.DONE],
)
def test_only_booked_status_can_be_cancelled(provider, service, status):
    booking = booked(provider, service)
    booking.status = status
    booking.save()
    with pytest.raises(NotCancellable):
        cancel_booking(booking.code, PHONE, now=LONG_AGO)


def test_cannot_cancel_after_the_slot_has_started(provider, service):
    booking = booked(provider, service)
    with pytest.raises(NotCancellable):
        cancel_booking(booking.code, PHONE, now=at(9, 5))


def next_monday():
    today = timezone.localdate()
    return today + timedelta(days=7 - today.weekday())


def future_booking(provider, service):
    start = timezone.make_aware(datetime.combine(next_monday(), time(9, 0)))
    return create_booking(provider, service, start, "Amina", PHONE)


def cancel(client, code, phone):
    return client.post(
        reverse("booking-cancel", args=[code]),
        {"patient_phone": phone},
        content_type="application/json",
    )


def test_patient_cancels_with_code_and_phone(client, provider, service):
    booking = future_booking(provider, service)
    response = cancel(client, booking.code, "+235 66 12 34 56")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_wrong_phone_gets_the_same_answer_as_unknown_code(client, provider, service):
    booking = future_booking(provider, service)
    wrong_phone = cancel(client, booking.code, "+23599999999")
    unknown_code = cancel(client, "ZZZZZZZZ", PHONE)
    assert wrong_phone.status_code == unknown_code.status_code == 404
    assert wrong_phone.json() == unknown_code.json()


def test_cannot_cancel_twice(client, provider, service):
    booking = future_booking(provider, service)
    assert cancel(client, booking.code, PHONE).status_code == 200
    assert cancel(client, booking.code, PHONE).status_code == 409


def test_invalid_phone_gives_400(client, provider, service):
    booking = future_booking(provider, service)
    assert cancel(client, booking.code, "abc").status_code == 400


def test_cancel_is_rate_limited(client):
    for _ in range(10):
        assert cancel(client, "ZZZZZZZZ", PHONE).status_code == 404
    assert cancel(client, "ZZZZZZZZ", PHONE).status_code == 429