from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAnyStaff, IsProviderRole

from .bookings import BookingNotFound
from .models import Provider
from .queue_services import call_next, finish, provider_of, todays_queue
from .staff_serializers import StaffBookingSerializer
from .staff_services import InvalidTransition, bookings_for

NO_PROFILE = {"detail": "This account is not linked to a provider."}


class QueueQuerySerializer(serializers.Serializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())


class QueueView(APIView):
    permission_classes = [IsAnyStaff]

    def get(self, request):
        if request.user.role == User.Role.PROVIDER:
            # A provider always sees their own queue, whatever the request asks for.
            provider = provider_of(request.user)
            if provider is None:
                return Response(NO_PROFILE, status=status.HTTP_409_CONFLICT)
        else:
            query = QueueQuerySerializer(data=request.query_params)
            query.is_valid(raise_exception=True)
            provider = query.validated_data["provider"]

        in_progress, waiting = todays_queue(provider)
        waiting_data = StaffBookingSerializer(waiting, many=True).data
        for position, item in enumerate(waiting_data, start=1):
            item["position"] = position
        return Response(
            {
                "provider": provider.name,
                "in_progress": (
                    StaffBookingSerializer(in_progress).data if in_progress else None
                ),
                "waiting": waiting_data,
            }
        )


class CallNextView(APIView):
    permission_classes = [IsProviderRole]

    def post(self, request):
        provider = provider_of(request.user)
        if provider is None:
            return Response(NO_PROFILE, status=status.HTTP_409_CONFLICT)
        try:
            booking = call_next(provider)
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(StaffBookingSerializer(booking).data)


class DoneView(APIView):
    permission_classes = [IsProviderRole]

    def post(self, request, code):
        try:
            booking = finish(bookings_for(request.user), code)
        except BookingNotFound:
            return Response(
                {"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(StaffBookingSerializer(booking).data)