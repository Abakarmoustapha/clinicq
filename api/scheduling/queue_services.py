from datetime import datetime, time, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from .bookings import BookingNotFound
from .models import Booking, Provider
from .staff_services import InvalidTransition


def provider_of(user):
    """The provider profile linked to this staff account, or None."""
    try:
        return user.provider_profile
    except ObjectDoesNotExist:
        return None


def todays_queue(provider, now=None):
    """Return (patient with the provider, list of waiting patients in arrival order)."""
    now = now or timezone.now()
    day_start = timezone.make_aware(
        datetime.combine(timezone.localtime(now).date(), time.min)
    )
    day_end = day_start + timedelta(days=1)
    todays = Booking.objects.filter(
        provider=provider,
        checked_in_at__gte=day_start,
        checked_in_at__lt=day_end,
    ).select_related("provider", "service")
    in_progress = todays.filter(status=Booking.Status.IN_PROGRESS).first()
    waiting = list(
        todays.filter(status=Booking.Status.CHECKED_IN).order_by("checked_in_at", "id")
    )
    return in_progress, waiting


def call_next(provider, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        # Locking the provider means only one "call next" runs at a time for them.
        Provider.objects.select_for_update().get(pk=provider.pk)
        in_progress, waiting = todays_queue(provider, now)
        if in_progress is not None:
            raise InvalidTransition("Finish the current patient first.")
        if not waiting:
            raise InvalidTransition("No patients are waiting.")
        booking = waiting[0]
        booking.status = Booking.Status.IN_PROGRESS
        booking.save(update_fields=["status"])
    return booking


def finish(queryset, code):
    with transaction.atomic():
        booking = (
            queryset.select_for_update(of=("self",)).filter(code=code.upper()).first()
        )
        if booking is None:
            raise BookingNotFound("Booking not found.")
        if booking.status != Booking.Status.IN_PROGRESS:
            raise InvalidTransition(
                "Only a patient who is with the provider can be marked as done."
            )
        booking.status = Booking.Status.DONE
        booking.save(update_fields=["status"])
    return booking