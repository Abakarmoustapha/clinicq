from rest_framework import serializers

from .models import Booking, Provider, Service
from .serializers import clean_name, clean_phone


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
            "is_walk_in",
            "checked_in_at",
        ]


class StaffListQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(), required=False
    )


class WalkInSerializer(serializers.Serializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    patient_name = serializers.CharField(max_length=100)
    patient_phone = serializers.CharField(max_length=30)
    patient_email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_patient_name(self, value):
        return clean_name(value)

    def validate_patient_phone(self, value):
        return clean_phone(value)