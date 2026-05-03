"""
SQL Injection Prevention Tests
Tests that SQL injection attempts are properly handled.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from rest_framework.authtoken.models import Token


class SQLInjectionPreventionTests(TestCase):
    """Test that SQL injection attempts are properly handled."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Test User'
        )
        self.token = Token.objects.create(user=self.user)

    def test_login_with_sql_injection_attempt_in_email(self):
        """Login endpoint should handle SQL injection attempts safely."""
        response = self.client.post('/api/accounts/login/', {
            'email': "admin'--",
            'password': 'anything'
        })

        # Should either reject the invalid email or return 401
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_login_with_sql_injection_attempt_in_password(self):
        """Login endpoint should safely handle injection in password."""
        response = self.client.post('/api/accounts/login/', {
            'email': 'test@example.com',
            'password': "'; DROP TABLE users;--"
        })

        # Should reject due to failed authentication
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST
        ])

        # Verify users table still exists
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_registration_with_injection_attempt_in_name(self):
        """Registration should handle injection attempts in name fields."""
        response = self.client.post('/api/accounts/register/', {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'full_name': 'Test\'); DROP TABLE users;--',
            'phone_number': '+1234567890'
        })

        # Should reject or sanitize the input
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED
        ])

        # Verify data wasn't actually injected
        if User.objects.filter(email='test@example.com').exists():
            new_user = User.objects.get(email='test@example.com')
            # Name should not contain SQL
            self.assertNotIn('DROP TABLE', new_user.full_name)

    def test_registration_with_injection_attempt_in_email(self):
        """Registration should handle injection in email field."""
        response = self.client.post('/api/accounts/register/', {
            'email': 'test\'; DELETE FROM users;--@example.com',
            'password': 'TestPass123!',
            'full_name': 'Test User',
            'phone_number': '+1234567890'
        })

        # Should reject the invalid email format
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED
        ])

        # Verify all users still exist
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_password_reset_with_injection_attempt(self):
        """Password reset should safely handle injection attempts."""
        response = self.client.post('/api/accounts/password-reset/request/', {
            'email': "'; DROP TABLE users;--"
        })

        # Should handle safely
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ])

        # Verify users table still exists
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_profile_update_with_injection_attempt(self):
        """Profile update should safely handle injection in user input."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        response = self.client.put('/api/accounts/me/', {
            'full_name': 'Test\'); DROP TABLE users;--'
        })

        # Should succeed or reject
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])

        # Verify user still exists and data is safe
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.user.refresh_from_db()
        self.assertNotIn('DROP TABLE', self.user.full_name)

    def test_union_based_sql_injection_attempt(self):
        """Test protection against UNION-based SQL injection."""
        response = self.client.post('/api/accounts/login/', {
            'email': "admin' UNION SELECT * FROM accounts_user--",
            'password': 'anything'
        })

        # Should be rejected as invalid email format or be rate limited
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])

    def test_time_based_sql_injection_attempt(self):
        """Test protection against time-based blind SQL injection."""
        response = self.client.post('/api/accounts/login/', {
            'email': "admin'; WAITFOR DELAY '00:00:05'--",
            'password': 'anything'
        })

        # Should be rejected
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ])
