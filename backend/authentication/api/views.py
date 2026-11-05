"""API views for registration, login, logout and token refresh."""
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (LoginSerializer, RegistrationSerializer,
                          UserSerializer)
from .utils import (create_tokens, delete_token_cookies, set_access_cookie,
                    set_refresh_cookie)


class RegisterAPIView(APIView):
    """Create a new user account."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'User created successfully!'},
                        status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """Log a user in and set the JWT cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()
        if user is None:
            return Response({'detail': 'Invalid username or password.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        refresh, access = create_tokens(user)
        response = Response({'detail': 'Login successfully!',
                             'user': UserSerializer(user).data})
        set_access_cookie(response, access)
        set_refresh_cookie(response, refresh)
        return response


class LogoutAPIView(APIView):
    """Blacklist the refresh token and delete the cookies."""

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass
        response = Response({'detail': (
            'Log-Out successfully! All Tokens will be deleted. '
            'Refresh token is now invalid.')})
        delete_token_cookies(response)
        return response


class TokenRefreshAPIView(APIView):
    """Issue a new access token from the refresh token cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(
            data={'refresh': request.COOKIES.get('refresh_token')})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, ValidationError):
            return Response({'detail': 'Invalid refresh token.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        response = Response({'detail': 'Token refreshed'})
        set_access_cookie(response, serializer.validated_data['access'])
        return response
