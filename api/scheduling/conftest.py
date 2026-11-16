from datetime import time

import pytest

from .models import Provider, Service, WorkingHours


@pytest.fixture
def service():
    return Service.objects.create(name="General consultation", slot_minutes=20)


@pytest.fixture
def provider(service):
    p = Provider.objects.create(name="Dr. Ali")
    p.services.add(service)
    WorkingHours.objects.create(
        provider=p, weekday=0, start_time=time(9, 0), end_time=time(10, 0)
    )
    return p