# apps/authentication/serializers.py

import re
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class RegisterSerializer(serializers.Serializer):

    username = serializers.CharField(
        min_length=3,
        max_length=30,
    )

    email = serializers.EmailField(required=False, allow_blank=True)

    password = serializers.CharField(
        min_length=8,
        max_length=128,
        write_only=True,
    )

    confirm_password = serializers.CharField(
        write_only=True,
    )

    def validate_username(self, value):
        """
        Username rules:
          → Must start with a letter
          → Only letters, numbers, underscores, hyphens allowed
          → Cannot be only numbers
          → No spaces allowed
        """

        # Must start with a letter
        if not value[0].isalpha():
            raise serializers.ValidationError(
                'Username must start with a letter.'
            )

        # Only allowed characters
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', value):
            raise serializers.ValidationError(
                'Username can only contain letters, numbers, '
                'underscores and hyphens.'
            )

        # Cannot be all numbers (already handled by starting with letter)
        # but explicitly checking makes the error clearer
        if value.isdigit():
            raise serializers.ValidationError(
                'Username cannot be only numbers.'
            )

        # Check availability
        if User.objects.filter(username__iexact=value).exists():
            # iexact = case insensitive
            # Prevents: "Alice" and "alice" being different users
            raise serializers.ValidationError(
                'This username is already taken.'
            )

        return value.lower()
        # Store all usernames in lowercase
        # Consistent, no case confusion

    def validate_email(self, value):
        """Email must be unique if provided."""
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'An account with this email already exists.'
            )
        return value.lower() if value else value

    def validate_password(self, value):
        """
        Password rules:
          → At least one uppercase letter
          → At least one lowercase letter
          → At least one digit
          → At least one special character
          → Django's built-in validators also run
        """

        errors = []

        if not re.search(r'[A-Z]', value):
            errors.append('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', value):
            errors.append('Password must contain at least one lowercase letter.')

        if not re.search(r'\d', value):
            errors.append('Password must contain at least one number.')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]\/\\]', value):
            errors.append('Password must contain at least one special character.')

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate(self, data):
        """
        Cross field validation.
        Runs after individual field validation.
        """

        # Check passwords match
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })

        # Check password does not contain username
        username = data.get('username', '')
        password = data.get('password', '')

        if username.lower() in password.lower():
            raise serializers.ValidationError({
                'password': 'Password cannot contain your username.'
            })

        # Run Django built-in password validators
        # These check for common passwords, similarity to user attributes etc.
        try:
            # Create a temporary user object for validation context
            temp_user = User(username=username)
            validate_password(password, user=temp_user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })

        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()