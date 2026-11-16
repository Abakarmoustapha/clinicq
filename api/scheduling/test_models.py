import pytest
from django.db import IntegrityError, transaction

from .models import Service


@pytest.mark.django_db
def test_service_with_valid_slot_length_is_saved():
    service = Service.objects.create(name="General consultation", slot_minutes=20)
    assert service.pk is not None


@pytest.mark.django_db
@pytest.mark.parametrize("minutes", [5, 61])
def test_database_rejects_slot_length_outside_10_to_60(minutes):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Service.objects.create(name="Bad service", slot_minutes=minutes)