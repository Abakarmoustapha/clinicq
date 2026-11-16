from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from .models import Booking

pytestmark = pytest.mark.django_db


def next_monday():
    today = timezone.localdate()
    return today + timedelta(days=7 - today.weekday())


def first_slot(client, provider, service):
    response = client.get(
        reverse("free-slots"),
        {
            "provider": provider.pk,
            "service": service.pk,
            "date": next_monday().isoformat(),
        },
    )
    return response.json()["slots"][0]["start_at"]


def payload(provider, service, start_at, **overrides):
    data = {
        "provider": provider.pk,
        "service": service.pk,
        "start_at": start_at,
        "patient_name": "Amina",
        "patient_phone": "+235 66 12 34 56",
    }
    data.update(overrides)
    return data


def post(client, data):
    return client.post(reverse("booking-create"), data, content_type="application/json")


def test_patient_can_book_a_free_slot(client, provider, service):
    start = first_slot(client, provider, service)
    response = post(client, payload(provider, service, start))
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 8
    assert body["status"] == "booked"
    assert Booking.objects.get(code=body["code"]).patient_phone == "+23566123456"


def test_response_does_not_leak_personal_data(client, provider, service):
    start = first_slot(client, provider, service)
    body = post(client, payload(provider, service, start)).json()
    assert "patient_phone" not in body
    assert "patient_email" not in body
    assert "patient_name" not in body


def test_second_patient_gets_409_for_the_same_slot(client, provider, service):
    start = first_slot(client, provider, service)
    assert post(client, payload(provider, service, start)).status_code == 201
    second = post(client, payload(provider, service, start, patient_name="Omar"))
    assert second.status_code == 409


def test_time_that_is_not_a_slot_gives_409(client, provider, service):
    start = datetime.fromisoformat(first_slot(client, provider, service))
    off_grid = (start + timedelta(minutes=10)).isoformat()
    response = post(client, payload(provider, service, off_grid))
    assert response.status_code == 409


def test_invalid_phone_gives_400(client, provider, service):
    start = first_slot(client, provider, service)
    response = post(client, payload(provider, service, start, patient_phone="abc"))
    assert response.status_code == 400


def test_missing_name_gives_400(client, provider, service):
    start = first_slot(client, provider, service)
    data = payload(provider, service, start)
    del data["patient_name"]
    assert post(client, data).status_code == 400


def test_unknown_provider_gives_400(client, provider, service):
    start = first_slot(client, provider, service)
    response = post(client, payload(provider, service, start, provider=9999))
    assert response.status_code == 400


def test_booking_can_be_looked_up_by_code(client, provider, service):
    start = first_slot(client, provider, service)
    code = post(client, payload(provider, service, start)).json()["code"]
    response = client.get(reverse("booking-detail", args=[code.lower()]))
    assert response.status_code == 200
    assert response.json()["code"] == code
    assert response.json()["provider"] == "Dr. Ali"


def test_unknown_code_gives_404(client):
    response = client.get(reverse("booking-detail", args=["ZZZZZZZZ"]))
    assert response.status_code == 404


def test_too_many_booking_requests_are_throttled(client):
    for _ in range(10):
        assert post(client, {}).status_code == 400
    assert post(client, {}).status_code == 429