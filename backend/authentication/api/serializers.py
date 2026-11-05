"""Serializers for registration and login."""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate and create a new user account."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Ensure the email address is not used yet."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate(self, attrs):
        """Ensure both passwords match."""
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        """Create the user with a hashed password."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Validate login credentials."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def get_user(self):
        """Return the authenticated user or None."""
        return authenticate(
            username=self.validated_data['username'],
            password=self.validated_data['password'],
        )


class UserSerializer(serializers.ModelSerializer):
    """Public user data returned after login."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email']
