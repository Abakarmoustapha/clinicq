import pytest
from django.urls import reverse
from rest_framework.throttling import SimpleRateThrottle

pytestmark = pytest.mark.django_db


def status_of(client, code):
    return client.get(reverse("booking-queue", args=[code]))


def test_one_booking_code_cannot_be_polled_endlessly(client, monkeypatch):
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "queue_per_code", "3/hour")
    for _ in range(3):
        assert status_of(client, "ZZZZZZZZ").status_code == 404
    assert status_of(client, "ZZZZZZZZ").status_code == 429


def test_patients_sharing_one_connection_do_not_block_each_other(client, monkeypatch):
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "queue_per_code", "3/hour")
    for code in ("AAAAAAAA", "BBBBBBBB", "CCCCCCCC", "DDDDDDDD"):
        for _ in range(3):
            assert status_of(client, code).status_code == 404


def test_one_connection_cannot_try_unlimited_codes(client, monkeypatch):
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "queue_ip", "5/hour")
    for index in range(5):
        assert status_of(client, f"CODE000{index}").status_code == 404
    assert status_of(client, "CODE0009").status_code == 429