from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .availability import get_free_slots
from .models import Booking

MAX_DAYS_AHEAD = 30


class BookingError(Exception):
    """Base class for booking problems that we can explain to the patient."""


class SlotUnavailable(BookingError):
    """The slot does not exist, or someone else took it."""


class TooFarAhead(BookingError):
    """The slot is further in the future than we allow."""


def create_booking(
    provider, service, start_at, patient_name, patient_phone, patient_email="", now=None
):
    now = now or timezone.now()

    if start_at > now + timedelta(days=MAX_DAYS_AHEAD):
        raise TooFarAhead(f"Bookings are possible up to {MAX_DAYS_AHEAD} days ahead.")

    day = timezone.localtime(start_at).date()
    if start_at not in get_free_slots(provider, service, day, now=now):
        raise SlotUnavailable("This slot is not available.")

    end_at = start_at + timedelta(minutes=service.slot_minutes)
    try:
        with transaction.atomic():
            return Booking.objects.create(
                provider=provider,
                service=service,
                start_at=start_at,
                end_at=end_at,
                patient_name=patient_name,
                patient_phone=patient_phone,
                patient_email=patient_email,
            )
    except IntegrityError as exc:
        raise SlotUnavailable("This slot was just taken by someone else.") from exc