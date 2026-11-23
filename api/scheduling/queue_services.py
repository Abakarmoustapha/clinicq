import math
from datetime import datetime, time, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from .bookings import BookingNotFound
from .models import Booking, Provider
from .staff_services import InvalidTransition

MIN_AVERAGE_MINUTES = 5
MAX_AVERAGE_MINUTES = 60
SAMPLES_NEEDED = 3


def provider_of(user):
    """The provider profile linked to this staff account, or None."""
    try:
        return user.provider_profile
    except ObjectDoesNotExist:
        return None


def _day_start(now):
    return timezone.make_aware(
        datetime.combine(timezone.localtime(now).date(), time.min)
    )


def todays_queue(provider, now=None):
    """Return (patient with the provider, list of waiting patients in arrival order)."""
    now = now or timezone.now()
    day_start = _day_start(now)
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
        booking.called_at = now
        booking.save(update_fields=["status", "called_at"])
    return booking


def finish(queryset, code, now=None):
    now = now or timezone.now()
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
        booking.finished_at = now
        booking.save(update_fields=["status", "finished_at"])
    return booking


def average_minutes(provider, service, now=None):
    """Average length of the provider's recent consultations today.

    With fewer than SAMPLES_NEEDED finished consultations we use the service's slot
    length, and the average is always kept between 5 and 60 minutes.
    """
    now = now or timezone.now()
    recent = list(
        Booking.objects.filter(
            provider=provider,
            status=Booking.Status.DONE,
            called_at__isnull=False,
            finished_at__isnull=False,
            finished_at__gte=_day_start(now),
        ).order_by("-finished_at")[:10]
    )
    if len(recent) < SAMPLES_NEEDED:
        return service.slot_minutes
    durations = [(b.finished_at - b.called_at).total_seconds() / 60 for b in recent]
    average = sum(durations) / len(durations)
    return max(MIN_AVERAGE_MINUTES, min(MAX_AVERAGE_MINUTES, average))


def queue_status(booking, now=None):
    """Position, people ahead and estimated wait for one patient. Numbers only."""
    now = now or timezone.now()
    result = {"position": None, "people_ahead": None, "estimated_wait_minutes": None}
    if booking.status != Booking.Status.CHECKED_IN:
        return result
    in_progress, waiting = todays_queue(booking.provider, now)
    ids = [b.pk for b in waiting]
    if booking.pk not in ids:
        return result
    position = ids.index(booking.pk) + 1
    ahead = position - 1 + (1 if in_progress else 0)
    wait = ahead * average_minutes(booking.provider, booking.service, now)
    result.update(
        position=position,
        people_ahead=ahead,
        estimated_wait_minutes=int(math.ceil(wait / 5) * 5),
    )
    return result