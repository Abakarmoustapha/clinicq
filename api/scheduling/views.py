from datetime import timedelta

from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .availability import get_free_slots
from .bookings import MAX_DAYS_AHEAD
from .models import Provider, Service
from .serializers import (
    FreeSlotsQuerySerializer,
    ProviderSerializer,
    ServiceSerializer,
)


class ServiceListView(ListAPIView):
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(is_active=True)
    pagination_class = None


class ProviderListView(ListAPIView):
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


class FreeSlotsView(APIView):
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