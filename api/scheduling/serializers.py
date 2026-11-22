import re

from rest_framework import serializers

from .models import Booking, Provider, Service

DIGIT_RUN = "01234567890123456789"


def clean_name(value):
    name = " ".join(value.split())
    letters = sum(ch.isalpha() for ch in name)
    allowed = all(ch.isalpha() or ch in " '.-" for ch in name)
    if letters < 2 or not allowed:
        raise serializers.ValidationError(
            "Enter your real name, using letters only."
        )
    return name


def clean_phone(value):
    phone = re.sub(r"[ \-]", "", value)
    if not re.fullmatch(r"\+?[0-9]{8,15}", phone):
        raise serializers.ValidationError(
            "Enter a valid phone number, for example +23566123456."
        )
    digits = phone.lstrip("+")
    if len(set(digits)) == 1 or digits in DIGIT_RUN or digits[::-1] in DIGIT_RUN:
        raise serializers.ValidationError("Enter your real phone number.")
    return phone


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "slot_minutes"]


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "name"]


class FreeSlotsQuerySerializer(serializers.Serializer):
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.filter(is_active=True)
    )
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True)
    )
    date = serializers.DateField()


class BookingCreateSerializer(serializers.Serializer):
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.filter(is_active=True)
    )
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True)
    )
    start_at = serializers.DateTimeField()
    patient_name = serializers.CharField(max_length=100)
    patient_phone = serializers.CharField(max_length=30)
    patient_email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_patient_name(self, value):
        return clean_name(value)

    def validate_patient_phone(self, value):
        return clean_phone(value)


class BookingCancelSerializer(serializers.Serializer):
    patient_phone = serializers.CharField(max_length=30)

    def validate_patient_phone(self, value):
        return clean_phone(value)


class BookingSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="provider.name", read_only=True)
    service = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Booking
        fields = ["code", "status", "start_at", "end_at", "provider", "service"]