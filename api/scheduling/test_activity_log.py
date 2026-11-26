from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import ActivityLog

from .models import Booking, Provider, WorkingHours

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"
PATIENT_PHONE = "+23566123456"


def make_user(email, role):
    return User.objects.create_user(email=email, password=PASSWORD, role=role)


def logged_in(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def reception():
    return make_user("reception@example.com", User.Role.RECEPTIONIST)


@pytest.fixture
def doctor(service):
    user = make_user("doctor@example.com", User.Role.PROVIDER)
    provider = Provider.objects.create(name="Dr. A", user=user)
    provider.services.add(service)
    return provider


@pytest.fixture
def working_today(service):
    provider = Provider.objects.create(name="Dr. Today")
    provider.services.add(service)
    WorkingHours.objects.create(
        provider=provider,
        weekday=timezone.localdate().weekday(),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    return provider


def today_at(hour, minute=0):
    return timezone.make_aware(
        datetime.combine(timezone.localdate(), time(hour, minute))
    )


def make_booking(provider, service, start_at, status=Booking.Status.BOOKED, arrived=None):
    return Booking.objects.create(
        provider=provider,
        service=service,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=20),
        patient_name="Amina Ali",
        patient_phone=PATIENT_PHONE,
        status=status,
        checked_in_at=arrived,
    )


def actions():
    return list(ActivityLog.objects.order_by("id").values_list("action", flat=True))


def next_monday():
    today = timezone.localdate()
    return today + timedelta(days=7 - today.weekday())


def book_online(client, provider, service):
    slots = client.get(
        reverse("free-slots"),
        {
            "provider": provider.pk,
            "service": service.pk,
            "date": next_monday().isoformat(),
        },
    ).json()["slots"]
    return client.post(
        reverse("booking-create"),
        {
            "provider": provider.pk,
            "service": service.pk,
            "start_at": slots[0]["start_at"],
            "patient_name": "Amina Ali",
            "patient_phone": "+235 66 12 34 56",
        },
        content_type="application/json",
    )


# --- what gets logged -------------------------------------------------------


def test_patient_booking_is_logged_without_personal_data(client, provider, service):
    response = book_online(client, provider, service)
    assert response.status_code == 201
    entry = ActivityLog.objects.get()
    assert entry.action == ActivityLog.Action.BOOKING_CREATED
    assert entry.booking_code == response.json()["code"]
    assert entry.status_after == "booked"
    assert entry.actor is None
    assert entry.actor_email == ""
    stored = " ".join(str(value) for value in entry.__dict__.values())
    assert "Amina" not in stored
    assert "23566123456" not in stored


def test_refused_booking_leaves_no_log_entry(client, provider, service):
    first = book_online(client, provider, service)
    assert first.status_code == 201
    second = client.post(
        reverse("booking-create"),
        {
            "provider": provider.pk,
            "service": service.pk,
            "start_at": first.json()["start_at"],
            "patient_name": "Omar Said",
            "patient_phone": "+235 66 98 76 54",
        },
        content_type="application/json",
    )
    assert second.status_code == 409
    assert actions() == ["booking_created"]

def test_patient_cancel_is_logged(client, provider, service):
    code = book_online(client, provider, service).json()["code"]
    response = client.post(
        reverse("booking-cancel", args=[code]),
        {"patient_phone": "+235 66 12 34 56"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert actions() == ["booking_created", "booking_cancelled"]
    assert ActivityLog.objects.order_by("id").last().status_after == "cancelled"


def test_check_in_is_logged_with_the_staff_member(reception, doctor, service):
    booking = make_booking(doctor, service, today_at(12))
    response = logged_in(reception).post(reverse("staff-check-in", args=[booking.code]))
    assert response.status_code == 200
    entry = ActivityLog.objects.get()
    assert entry.action == ActivityLog.Action.CHECKED_IN
    assert entry.booking_code == booking.code
    assert entry.status_after == "checked_in"
    assert entry.actor == reception
    assert entry.actor_email == "reception@example.com"


def test_no_show_is_logged(reception, doctor, service):
    booking = make_booking(doctor, service, timezone.now() - timedelta(minutes=30))
    response = logged_in(reception).post(reverse("staff-no-show", args=[booking.code]))
    assert response.status_code == 200
    assert actions() == ["no_show"]


def test_walk_in_is_logged(reception, working_today, service):
    response = logged_in(reception).post(
        reverse("staff-walk-in"),
        {
            "provider": working_today.pk,
            "service": service.pk,
            "patient_name": "Amina Ali",
            "patient_phone": "+235 66 12 34 56",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    entry = ActivityLog.objects.get()
    assert entry.action == ActivityLog.Action.WALK_IN_ADDED
    assert entry.booking_code == response.json()["code"]
    assert entry.actor == reception


def test_call_next_and_done_are_logged(doctor, service):
    booking = make_booking(
        doctor,
        service,
        today_at(12),
        status=Booking.Status.CHECKED_IN,
        arrived=timezone.now(),
    )
    client = logged_in(doctor.user)
    assert client.post(reverse("staff-call-next")).status_code == 200
    assert client.post(reverse("staff-done", args=[booking.code])).status_code == 200
    assert actions() == ["called", "finished"]
    assert ActivityLog.objects.filter(actor=doctor.user).count() == 2


def test_refused_staff_actions_leave_no_log_entry(reception, doctor, service):
    booking = make_booking(doctor, service, timezone.now() + timedelta(hours=2))
    unknown = logged_in(reception).post(reverse("staff-check-in", args=["ZZZZZZZZ"]))
    assert unknown.status_code == 404
    not_allowed = logged_in(doctor.user).post(
        reverse("staff-check-in", args=[booking.code])
    )
    assert not_allowed.status_code == 403
    too_early = logged_in(reception).post(reverse("staff-no-show", args=[booking.code]))
    assert too_early.status_code == 409
    assert ActivityLog.objects.count() == 0


# --- the log is trustworthy -------------------------------------------------


def test_change_is_rolled_back_when_the_log_cannot_be_written(reception, doctor, service):
    booking = make_booking(doctor, service, today_at(12))
    strict = Client(raise_request_exception=False)
    strict.force_login(reception)
    with patch("scheduling.staff_views.record", side_effect=RuntimeError("log down")):
        response = strict.post(reverse("staff-check-in", args=[booking.code]))
    assert response.status_code == 500
    booking.refresh_from_db()
    assert booking.status == Booking.Status.BOOKED
    assert booking.checked_in_at is None


def test_log_entries_cannot_be_changed_or_deleted():
    entry = ActivityLog.objects.create(
        action=ActivityLog.Action.CHECKED_IN,
        booking_code="ABCDEFGH",
        status_after="checked_in",
    )
    entry.status_after = "done"
    with pytest.raises(RuntimeError):
        entry.save()
    with pytest.raises(RuntimeError):
        entry.delete()
    entry.refresh_from_db()
    assert entry.status_after == "checked_in"


# --- who can read it --------------------------------------------------------


def test_admin_role_can_read_the_activity_list():
    admin = make_user("admin@example.com", User.Role.ADMIN)
    ActivityLog.objects.create(
        action=ActivityLog.Action.CHECKED_IN,
        booking_code="ABCDEFGH",
        status_after="checked_in",
        actor_email="reception@example.com",
    )
    response = logged_in(admin).get(reverse("staff-activity"))
    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["actor"] == "reception@example.com"
    assert entry["booking_code"] == "ABCDEFGH"
    assert entry["action"] == "checked_in"


@pytest.mark.parametrize("role", [User.Role.RECEPTIONIST, User.Role.PROVIDER])
def test_other_staff_cannot_read_the_activity_list(role):
    user = make_user("someone@example.com", role)
    assert logged_in(user).get(reverse("staff-activity")).status_code == 403


def test_strangers_cannot_read_the_activity_list(client):
    assert client.get(reverse("staff-activity")).status_code == 403


def test_activity_list_can_be_filtered_by_booking_code():
    admin = make_user("admin@example.com", User.Role.ADMIN)
    for code in ("AAAAAAAA", "BBBBBBBB"):
        ActivityLog.objects.create(
            action=ActivityLog.Action.CHECKED_IN,
            booking_code=code,
            status_after="checked_in",
        )
    response = logged_in(admin).get(reverse("staff-activity"), {"booking": "bbbbbbbb"})
    codes = [entry["booking_code"] for entry in response.json()["entries"]]
    assert codes == ["BBBBBBBB"]


def test_django_admin_does_not_allow_adding_log_entries():
    superuser = User.objects.create_superuser(email="boss@example.com", password=PASSWORD)
    response = logged_in(superuser).get(reverse("admin:audit_activitylog_add"))
    assert response.status_code == 403