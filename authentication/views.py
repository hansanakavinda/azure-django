# authentication/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, LoginSerializer
from pdf_storage.responses import success_response, error_response


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/"""
    serializer = RegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message="Invalid data provided."
        )

    user = User.objects.create_user(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
        email=serializer.validated_data.get('email', ''),
    )
    token = Token.objects.create(user=user)

    return success_response(
        data={
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
        },
        message="User registered successfully.",
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """POST /api/auth/login/"""
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message="Invalid data provided."
        )

    user = authenticate(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
    )

    if not user:
        return error_response(
            errors='Invalid credentials.',
            message="Invalid credentials provided."
        )

    token, created = Token.objects.get_or_create(user=user)

    return success_response(
        data={
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
        },
        message="User logged in successfully."
    )


@api_view(['POST'])
def logout(request):
    """POST /api/auth/logout/"""
    request.user.auth_token.delete()
    return success_response(message="User logged out successfully.")