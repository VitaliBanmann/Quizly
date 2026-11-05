"""Tests for the authentication endpoints."""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase


class AuthenticationTests(APITestCase):
    """Cover register, login, logout and token refresh."""

    def setUp(self):
        self.user = User.objects.create_user(
            'tester', 'tester@example.com', 'secret123')

    def login(self):
        return self.client.post(reverse('login'), {
            'username': 'tester', 'password': 'secret123'})

    def test_register_creates_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'new', 'email': 'new@example.com',
            'password': 'pw12345', 'confirmed_password': 'pw12345'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['detail'], 'User created successfully!')

    def test_register_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'new', 'email': 'new@example.com',
            'password': 'pw12345', 'confirmed_password': 'other'})
        self.assertEqual(response.status_code, 400)

    def test_login_sets_http_only_cookies(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['username'], 'tester')
        for name in ('access_token', 'refresh_token'):
            self.assertTrue(response.cookies[name]['httponly'])

    def test_login_wrong_password(self):
        response = self.client.post(reverse('login'), {
            'username': 'tester', 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

    def test_refresh_sets_new_access_cookie(self):
        self.login()
        response = self.client.post(reverse('token-refresh'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.cookies)

    def test_refresh_without_cookie(self):
        response = self.client.post(reverse('token-refresh'))
        self.assertEqual(response.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        refresh = self.login().cookies['refresh_token'].value
        self.client.post(reverse('logout'))
        self.client.cookies['refresh_token'] = refresh
        self.assertEqual(
            self.client.post(reverse('token-refresh')).status_code, 401)

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 401)
