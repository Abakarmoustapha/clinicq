from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Booking, WorkingHours

OCCUPYING_STATUSES = ["booked", "checked_in", "in_progress", "done"]


def get_free_slots(provider, service, day, now=None):
    """Return the start times of the free slots of one provider on one day."""
    now = now or timezone.now()

    if not provider.is_active or not service.is_active:
        return []
    if not provider.services.filter(pk=service.pk).exists():
        return []

    length = timedelta(minutes=service.slot_minutes)
    day_start = timezone.make_aware(datetime.combine(day, time.min))
    day_end = day_start + timedelta(days=1)

    # Walk-ins do not reserve a slot, so they never remove one from the list.
    busy = list(
        Booking.objects.filter(
            provider=provider,
            is_walk_in=False,
            status__in=OCCUPYING_STATUSES,
            start_at__lt=day_end,
            end_at__gt=day_start,
        ).values_list("start_at", "end_at")
    )

    slots = []
    for block in WorkingHours.objects.filter(provider=provider, weekday=day.weekday()):
        slot_start = timezone.make_aware(datetime.combine(day, block.start_time))
        block_end = timezone.make_aware(datetime.combine(day, block.end_time))
        while slot_start + length <= block_end:
            slot_end = slot_start + length
            is_in_future = slot_start > now
            is_free = all(
                not (slot_start < busy_end and slot_end > busy_start)
                for busy_start, busy_end in busy
            )
            if is_in_future and is_free:
                slots.append(slot_start)
            slot_start = slot_end
    return sorted(slots)