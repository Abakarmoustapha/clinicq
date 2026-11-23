from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .bookings import BookingError, BookingNotFound
from .models import Booking, WorkingHours

NO_SHOW_GRACE_MINUTES = 15


class InvalidTransition(BookingError):
    """The booking is not in a state where this action is allowed."""


class WalkInNotPossible(BookingError):
    """A walk-in cannot be added for this provider or service."""


def bookings_for(user):
    """The bookings this staff member is allowed to see and change."""
    if user.role == User.Role.PROVIDER:
        return Booking.objects.filter(provider__user=user)
    return Booking.objects.all()


def _locked(queryset, code):
    booking = queryset.select_for_update(of=("self",)).filter(code=code.upper()).first()
    if booking is None:
        raise BookingNotFound("Booking not found.")
    return booking


def check_in(queryset, code, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        booking = _locked(queryset, code)
        if booking.status != Booking.Status.BOOKED:
            raise InvalidTransition("Only a booked patient can be checked in.")
        booked_day = timezone.localtime(booking.start_at).date()
        if booked_day != timezone.localtime(now).date():
            raise InvalidTransition(
                "Patients can only be checked in on the day of their booking."
            )
        booking.status = Booking.Status.CHECKED_IN
        booking.checked_in_at = now
        booking.save(update_fields=["status", "checked_in_at"])
    return booking


def mark_no_show(queryset, code, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        booking = _locked(queryset, code)
        if booking.status != Booking.Status.BOOKED:
            raise InvalidTransition(
                "Only a booked patient can be marked as a no-show."
            )
        earliest = booking.start_at + timedelta(minutes=NO_SHOW_GRACE_MINUTES)
        if now < earliest:
            raise InvalidTransition(
                f"Wait {NO_SHOW_GRACE_MINUTES} minutes after the start time "
                "before marking a no-show."
            )
        booking.status = Booking.Status.NO_SHOW
        booking.save(update_fields=["status"])
    return booking


def create_walk_in(
    provider, service, patient_name, patient_phone, patient_email="", now=None
):
    now = now or timezone.now()
    if not provider.is_active or not service.is_active:
        raise WalkInNotPossible("This provider or service is not available.")
    if not provider.services.filter(pk=service.pk).exists():
        raise WalkInNotPossible("This provider does not offer this service.")
    weekday = timezone.localtime(now).weekday()
    if not WorkingHours.objects.filter(provider=provider, weekday=weekday).exists():
        raise WalkInNotPossible("This provider is not working today.")
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=now,
        end_at=now + timedelta(minutes=service.slot_minutes),
        patient_name=patient_name,
        patient_phone=patient_phone,
        patient_email=patient_email,
        status=Booking.Status.CHECKED_IN,
        is_walk_in=True,
        checked_in_at=now,
    )