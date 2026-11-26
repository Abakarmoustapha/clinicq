from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """One line of history: who did what to which booking, and when.

    The log never stores patient names or phone numbers. The booking code is enough
    to find the booking, and copying personal data would spread it to more places.
    """

    class Action(models.TextChoices):
        BOOKING_CREATED = "booking_created", "Booking created by a patient"
        BOOKING_CANCELLED = "booking_cancelled", "Booking cancelled by a patient"
        WALK_IN_ADDED = "walk_in_added", "Walk-in added"
        CHECKED_IN = "checked_in", "Patient checked in"
        NO_SHOW = "no_show", "Marked as a no-show"
        CALLED = "called", "Patient called"
        FINISHED = "finished", "Consultation finished"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=30, choices=Action.choices)
    booking_code = models.CharField(max_length=8, db_index=True)
    status_after = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # A copy of the actor's email, so the history stays readable if the account is deleted.
    actor_email = models.CharField(max_length=254, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        who = self.actor_email or "patient"
        return f"{self.created_at:%Y-%m-%d %H:%M} {who}: {self.action} {self.booking_code}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Activity log entries can never be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Activity log entries can never be deleted.")