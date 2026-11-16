from datetime import date, datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from .bookings import SlotUnavailable, TooFarAhead, create_booking
from .models import Booking

pytestmark = pytest.mark.django_db

MONDAY = date(2030, 1, 7)
LONG_AGO = timezone.make_aware(datetime(2029, 12, 31, 8, 0))


def at(hour, minute=0):
    return timezone.make_aware(datetime.combine(MONDAY, time(hour, minute)))


def test_creates_a_booking_for_a_free_slot(provider, service):
    booking = create_booking(
        provider, service, at(9, 20), "Amina", "+23500000001", now=LONG_AGO
    )
    assert booking.status == Booking.Status.BOOKED
    assert booking.start_at == at(9, 20)
    assert booking.end_at == at(9, 40)
    assert len(booking.code) == 8


def test_second_booking_for_the_same_slot_is_refused(provider, service):
    create_booking(provider, service, at(9, 0), "Amina", "+23500000001", now=LONG_AGO)
    with pytest.raises(SlotUnavailable):
        create_booking(
            provider, service, at(9, 0), "Omar", "+23500000002", now=LONG_AGO
        )


def test_time_that_is_not_a_slot_is_refused(provider, service):
    with pytest.raises(SlotUnavailable):
        create_booking(
            provider, service, at(9, 10), "Amina", "+23500000001", now=LONG_AGO
        )


def test_time_outside_working_hours_is_refused(provider, service):
    with pytest.raises(SlotUnavailable):
        create_booking(
            provider, service, at(14, 0), "Amina", "+23500000001", now=LONG_AGO
        )


def test_slot_in_the_past_is_refused(provider, service):
    with pytest.raises(SlotUnavailable):
        create_booking(
            provider, service, at(9, 0), "Amina", "+23500000001", now=at(9, 30)
        )


def test_booking_too_far_ahead_is_refused(provider, service):
    far_away = at(9, 0) - timedelta(days=31)
    with pytest.raises(TooFarAhead):
        create_booking(
            provider, service, at(9, 0), "Amina", "+23500000001", now=far_away
        )


def test_race_lost_at_the_database_becomes_slot_unavailable(provider, service):
    create_booking(provider, service, at(9, 0), "Amina", "+23500000001", now=LONG_AGO)
    # Pretend our check ran just before the other person's booking was saved:
    with patch("scheduling.bookings.get_free_slots", return_value=[at(9, 0)]):
        with pytest.raises(SlotUnavailable):
            create_booking(
                provider, service, at(9, 0), "Omar", "+23500000002", now=LONG_AGO
            )
    assert Booking.objects.count() == 1