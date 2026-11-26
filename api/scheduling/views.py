from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.models import ActivityLog
from audit.services import record

from .availability import get_free_slots
from .bookings import (
    MAX_DAYS_AHEAD,
    BookingNotFound,
    NotCancellable,
    SlotUnavailable,
    TooFarAhead,
    cancel_booking,
    create_booking,
)
from .models import Booking, Provider, Service
from .serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    FreeSlotsQuerySerializer,
    ProviderSerializer,
    ServiceSerializer,
)


class PublicMixin:
    """Endpoints open to everyone on purpose: no login and no session."""

    authentication_classes = []
    permission_classes = [AllowAny]


class ServiceListView(PublicMixin, ListAPIView):
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(is_active=True)
    pagination_class = None


class ProviderListView(PublicMixin, ListAPIView):
    serializer_class = ProviderSerializer
    pagination_class = None

    def get_queryset(self):
        providers = Provider.objects.filter(is_active=True)
        service_id = self.request.query_params.get("service")
        if service_id is not None:
            if not service_id.isdigit():
                return providers.none()
            providers = providers.filter(services__pk=service_id)
        return providers


class FreeSlotsView(PublicMixin, APIView):
    def get(self, request):
        query = FreeSlotsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        provider = query.validated_data["provider"]
        service = query.validated_data["service"]
        day = query.validated_data["date"]

        last_day = timezone.localdate() + timedelta(days=MAX_DAYS_AHEAD)
        starts = [] if day > last_day else get_free_slots(provider, service, day)

        slots = []
        for start in starts:
            local = timezone.localtime(start)
            slots.append(
                {"start_at": local.isoformat(), "time": local.strftime("%H:%M")}
            )
        return Response({"date": day.isoformat(), "slots": slots})


class BookingCreateView(PublicMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking_create"

    def post(self, request):
        data = BookingCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            # The booking and its log line are saved together, or not at all.
            with transaction.atomic():
                booking = create_booking(
                    provider=values["provider"],
                    service=values["service"],
                    start_at=values["start_at"],
                    patient_name=values["patient_name"],
                    patient_phone=values["patient_phone"],
                    patient_email=values["patient_email"],
                )
                record(ActivityLog.Action.BOOKING_CREATED, booking)
        except SlotUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except TooFarAhead as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(PublicMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking_lookup"

    def get(self, request, code):
        booking = get_object_or_404(
            Booking.objects.select_related("provider", "service"), code=code.upper()
        )
        return Response(BookingSerializer(booking).data)


class BookingCancelView(PublicMixin, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking_cancel"

    def post(self, request, code):
        data = BookingCancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                booking = cancel_booking(code, data.validated_data["patient_phone"])
                record(ActivityLog.Action.BOOKING_CANCELLED, booking)
        except BookingNotFound:
            return Response(
                {"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except NotCancellable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(BookingSerializer(booking).data)