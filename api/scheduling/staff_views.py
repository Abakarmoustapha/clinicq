from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAnyStaff, IsFrontDesk

from .bookings import BookingNotFound
from .staff_serializers import (
    StaffBookingSerializer,
    StaffListQuerySerializer,
    WalkInSerializer,
)
from .staff_services import (
    InvalidTransition,
    WalkInNotPossible,
    bookings_for,
    check_in,
    create_walk_in,
    mark_no_show,
)


class StaffBookingListView(APIView):
    permission_classes = [IsAnyStaff]

    def get(self, request):
        query = StaffListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data.get("date") or timezone.localdate()
        day_start = timezone.make_aware(datetime.combine(day, time.min))
        day_end = day_start + timedelta(days=1)

        bookings = (
            bookings_for(request.user)
            .filter(start_at__gte=day_start, start_at__lt=day_end)
            .select_related("provider", "service")
        )
        provider = query.validated_data.get("provider")
        if provider is not None:
            bookings = bookings.filter(provider=provider)

        data = StaffBookingSerializer(bookings, many=True).data
        return Response({"date": day.isoformat(), "bookings": data})


def run_action(request, code, action):
    try:
        booking = action(bookings_for(request.user), code)
    except BookingNotFound:
        return Response(
            {"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND
        )
    except InvalidTransition as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    return Response(StaffBookingSerializer(booking).data)


class CheckInView(APIView):
    permission_classes = [IsFrontDesk]

    def post(self, request, code):
        return run_action(request, code, check_in)


class NoShowView(APIView):
    permission_classes = [IsFrontDesk]

    def post(self, request, code):
        return run_action(request, code, mark_no_show)


class WalkInCreateView(APIView):
    permission_classes = [IsFrontDesk]

    def post(self, request):
        data = WalkInSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            booking = create_walk_in(**data.validated_data)
        except WalkInNotPossible as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            StaffBookingSerializer(booking).data, status=status.HTTP_201_CREATED
        )