from .models import ActivityLog


def record(action, booking, actor=None):
    """Write one line of history. Call it inside the same transaction as the change."""
    user = actor if getattr(actor, "is_authenticated", False) else None
    return ActivityLog.objects.create(
        action=action,
        booking_code=booking.code,
        status_after=booking.status,
        actor=user,
        actor_email=user.email if user else "",
    )