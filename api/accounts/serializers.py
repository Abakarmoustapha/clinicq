from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # No trimming, and a length limit so nobody can send a gigantic password.
    password = serializers.CharField(trim_whitespace=False, max_length=128)