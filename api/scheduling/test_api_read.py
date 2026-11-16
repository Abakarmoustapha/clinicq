from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from .bookings import create_booking
from .models import Service

pytestmark = pytest.mark.django_db


def next_monday():
    today = timezone.localdate()
    return today + timedelta(days=7 - today.weekday())


def slots_url(provider, service, day):
    return (
        f"{reverse('free-slots')}"
        f"?provider={provider.pk}&service={service.pk}&date={day.isoformat()}"
    )


def test_services_lists_only_active_services(client, service):
    Service.objects.create(name="Old service", slot_minutes=30, is_active=False)
    response = client.get(reverse("service-list"))
    assert response.status_code == 200
    assert response.json() == [
        {"id": service.pk, "name": "General consultation", "slot_minutes": 20}
    ]


def test_providers_can_be_filtered_by_service(client, provider, service):
    other_service = Service.objects.create(name="X-ray", slot_minutes=30)
    response = client.get(reverse("provider-list"), {"service": service.pk})
    assert [p["name"] for p in response.json()] == ["Dr. Ali"]
    response = client.get(reverse("provider-list"), {"service": other_service.pk})
    assert response.json() == []


def test_free_slots_for_next_monday(client, provider, service):
    response = client.get(slots_url(provider, service, next_monday()))
    assert response.status_code == 200
    times = [s["time"] for s in response.json()["slots"]]
    assert times == ["09:00", "09:20", "09:40"]


def test_booked_slot_disappears_from_the_list(client, provider, service):
    day = next_monday()
    first = client.get(slots_url(provider, service, day)).json()["slots"]
    start_at = datetime.fromisoformat(first[1]["start_at"])
    create_booking(provider, service, start_at, "Amina", "+23500000001")
    after = client.get(slots_url(provider, service, day)).json()["slots"]
    assert [s["time"] for s in after] == ["09:00", "09:40"]


def test_invalid_date_gives_400(client, provider, service):
    response = client.get(
        reverse("free-slots"),
        {"provider": provider.pk, "service": service.pk, "date": "not-a-date"},
    )
    assert response.status_code == 400


def test_unknown_provider_gives_400(client, service):
    response = client.get(
        reverse("free-slots"),
        {"provider": 9999, "service": service.pk, "date": "2030-01-07"},
    )
    assert response.status_code == 400


def test_days_too_far_ahead_have_no_slots(client, provider, service):
    far_monday = next_monday() + timedelta(days=35)
    response = client.get(slots_url(provider, service, far_monday))
    assert response.json()["slots"] == []