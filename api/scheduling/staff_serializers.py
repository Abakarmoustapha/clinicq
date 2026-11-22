from rest_framework import serializers

from .models import Booking, Provider


class StaffBookingSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="provider.name", read_only=True)
    service = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "code",
            "status",
            "start_at",
            "end_at",
            "provider",
            "service",
            "patient_name",
            "patient_phone",
            "patient_email",
        ]


class StaffListQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False
    )