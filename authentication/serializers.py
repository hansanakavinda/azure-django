# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, )
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        # write_only means password never comes back in responses
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken.')
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)