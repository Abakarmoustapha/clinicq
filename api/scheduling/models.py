import secrets

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import F, Func, Q


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


BOOKING_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_booking_code():
    return "".join(secrets.choice(BOOKING_CODE_ALPHABET) for _ in range(8))


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slot_minutes = models.PositiveSmallIntegerField(default=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(slot_minutes__gte=10, slot_minutes__lte=60),
                name="service_slot_minutes_between_10_and_60",
            )
        ]

    def __str__(self):
        return self.name


class Provider(models.Model):
    name = models.CharField(max_length=100)
    services = models.ManyToManyField(Service, related_name="providers", blank=True)
    is_active = models.BooleanField(default=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="provider_profile",
        limit_choices_to={"role": "provider"},
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Booking(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CHECKED_IN = "checked_in", "Checked in"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    code = models.CharField(
        max_length=8, unique=True, default=generate_booking_code, editable=False
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.PROTECT, related_name="bookings"
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="bookings"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    patient_name = models.CharField(max_length=100)
    patient_phone = models.CharField(max_length=30)
    patient_email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.BOOKED
    )
    # A walk-in has no reserved slot: they join the queue when they arrive.
    is_walk_in = models.BooleanField(default=False)
    # When the patient arrived. The queue is ordered by this time.
    checked_in_at = models.DateTimeField(null=True, blank=True)
    # When the provider called the patient, and when the consultation ended.
    called_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_at__gt=F("start_at")),
                name="booking_end_after_start",
            ),
            # Reserved slots of one provider may never overlap.
            # Walk-ins do not reserve a slot, so the rule does not apply to them.
            ExclusionConstraint(
                name="booking_no_overlap_per_provider",
                expressions=[
                    (
                        TsTzRange("start_at", "end_at", RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ("provider", RangeOperators.EQUAL),
                ],
                condition=Q(
                    status__in=["booked", "checked_in", "in_progress", "done"],
                    is_walk_in=False,
                ),
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.patient_name} with {self.provider}"


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["provider", "weekday", "start_time"]
        verbose_name_plural = "working hours"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="working_hours_end_after_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.provider} {self.get_weekday_display()} "
            f"{self.start_time:%H:%M}-{self.end_time:%H:%M}"
        )