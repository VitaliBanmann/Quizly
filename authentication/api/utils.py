"""Helper functions for cookie based JWT handling."""
from django.conf import settings
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


def set_token_cookie(response, key, token, lifetime):
    """Store a token as HTTP-only cookie on the response."""
    response.set_cookie(
        key=key,
        value=str(token),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
    )


def set_access_cookie(response, access_token):
    """Set the access token cookie."""
    set_token_cookie(response, 'access_token', access_token,
                     api_settings.ACCESS_TOKEN_LIFETIME)


def set_refresh_cookie(response, refresh_token):
    """Set the refresh token cookie."""
    set_token_cookie(response, 'refresh_token', refresh_token,
                     api_settings.REFRESH_TOKEN_LIFETIME)


def delete_token_cookies(response):
    """Remove both token cookies from the client."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')


def create_tokens(user):
    """Return a (refresh, access) token pair for the given user."""
    refresh = RefreshToken.for_user(user)
    return refresh, refresh.access_token
