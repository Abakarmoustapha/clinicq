from django.db import models


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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name