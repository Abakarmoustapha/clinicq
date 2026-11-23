from django.urls import path

from . import queue_views, staff_views, views

urlpatterns = [
    path("services/", views.ServiceListView.as_view(), name="service-list"),
    path("providers/", views.ProviderListView.as_view(), name="provider-list"),
    path("slots/", views.FreeSlotsView.as_view(), name="free-slots"),
    path("bookings/", views.BookingCreateView.as_view(), name="booking-create"),
    path("bookings/<str:code>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<str:code>/cancel/",
        views.BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path(
        "staff/bookings/",
        staff_views.StaffBookingListView.as_view(),
        name="staff-booking-list",
    ),
    path(
        "staff/bookings/<str:code>/check-in/",
        staff_views.CheckInView.as_view(),
        name="staff-check-in",
    ),
    path(
        "staff/bookings/<str:code>/no-show/",
        staff_views.NoShowView.as_view(),
        name="staff-no-show",
    ),
    path(
        "staff/bookings/<str:code>/done/",
        queue_views.DoneView.as_view(),
        name="staff-done",
    ),
    path(
        "staff/walk-ins/",
        staff_views.WalkInCreateView.as_view(),
        name="staff-walk-in",
    ),
    path("staff/queue/", queue_views.QueueView.as_view(), name="staff-queue"),
    path(
        "staff/queue/call-next/",
        queue_views.CallNextView.as_view(),
        name="staff-call-next",
    ),
]