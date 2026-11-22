from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .bookings import BookingError, BookingNotFound
from .models import Booking

NO_SHOW_GRACE_MINUTES = 15


class InvalidTransition(BookingError):
    """The booking is not in a state where this action is allowed."""


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
        booking.save(update_fields=["status"])
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