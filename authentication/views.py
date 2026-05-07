# authentication/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .serializers import RegisterSerializer, LoginSerializer, LogoutSerializer
from pdf_storage.responses import success_response, error_response


def get_tokens_for_user(user):
    """Generate access and refresh token manually for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# authentication/views.py


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom refresh view to format the output response matching
    our standardized success/error JSON response schema.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            return success_response(
                data=serializer.validated_data,
                message='Token refreshed successfully.'
            )
        except TokenError as e:
            return error_response(
                message='Invalid or expired refresh token.',
                errors={'detail': str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED
            )

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/"""
    serializer = RegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message='Validation failed.',
        )

    user = User.objects.create_user(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
        email=serializer.validated_data.get('email', ''),
    )

    tokens = get_tokens_for_user(user)

    return success_response(
        data={
            'user_id': user.id,
            'username': user.username,
            **tokens,
        },
        message='Registration successful.',
        status_code=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """POST /api/auth/login/"""
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message='Validation failed.',
        )

    user = authenticate(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
    )

    if not user:
        return error_response(
            message='Invalid credentials.',
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    tokens = get_tokens_for_user(user)

    return success_response(
        data={
            'user_id': user.id,
            'username': user.username,
            **tokens,
        },
        message='Login successful.',
    )


@api_view(['POST'])
def logout(request):
    """
    POST /api/auth/logout/
    
    Pass the 'refresh' token in the body to blacklist it securely.
    """
    serializer = LogoutSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message='Validation failed.',
        )

    try:
        # Blacklist the refresh token so it cannot be used again
        token = RefreshToken(serializer.validated_data['refresh'])
        token.blacklist()

        return success_response(
            message='Logged out successfully. Token blacklisted.',
        )
    except TokenError:
        return error_response(
            message='Token is already invalid or expired.',
            status_code=status.HTTP_400_BAD_REQUEST,
        )