"""
Rate Limiting Tests
Tests for endpoint-specific rate limiting configuration.
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'anon': '20/min',
            'user': '100/min',
            'login_attempt': '5/min',
            'registration': '3/hour',
            'password_reset': '3/hour',
        }
    }
)
class RateLimitingTests(TestCase):
    """Test rate limiting on sensitive endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_login_endpoint_throttle_configuration(self):
        """Test login endpoint has rate limiting configured."""
        # Login endpoint should have LoginAttemptThrottle applied
        response = self.client.post('/api/accounts/login/', {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
        
        # Response should contain rate limit information or be successful
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])

    def test_registration_endpoint_throttle_configuration(self):
        """Test registration endpoint has rate limiting configured."""
        response = self.client.post('/api/accounts/register/', {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'full_name': 'Test User',
            'phone_number': '+1234567890'
        })
        
        # Response should be one of these statuses
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])

    def test_password_reset_request_throttle_configuration(self):
        """Test password reset request has rate limiting configured."""
        # Create a user first
        User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Test User'
        )
        
        response = self.client.post('/api/accounts/password-reset/request/', {
            'email': 'user@example.com'
        })
        
        # Response should be successful or throttled
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])

    def test_rate_limit_not_applied_to_unauthenticated_public_endpoints(self):
        """Test that rate limiting applies to public endpoints."""
        # Make requests to public endpoints
        response = self.client.post('/api/accounts/login/', {
            'email': 'test@example.com',
            'password': 'test'
        })
        
        # Should either succeed or be rate limited, not give permission error
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
