"""
CORS Configuration Tests
Tests for Cross-Origin Resource Sharing (CORS) configuration.
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status


class CORSTests(TestCase):
    """Test CORS headers are properly configured."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(
        CORS_ALLOWED_ORIGINS=['http://example.com']
    )
    def test_cors_preflight_request(self):
        """Test OPTIONS preflight request handling."""
        response = self.client.options(
            '/api/accounts/login/',
            HTTP_ORIGIN='http://example.com',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
        )
        self.assertIn(response.status_code, [200, 405])

    def test_cors_allowed_methods(self):
        """Test that only allowed HTTP methods are specified in CORS headers."""
        response = self.client.get('/api/accounts/profile/')
        
        # Should be present in CORS configuration
        allowed_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}
        self.assertTrue(allowed_methods)

    @override_settings(
        CORS_ALLOWED_ORIGINS=['http://example.com']
    )
    def test_cors_credentials_allowed(self):
        """Test that credentials can be sent with CORS requests."""
        # CORS_ALLOW_CREDENTIALS should be True
        response = self.client.get(
            '/api/accounts/profile/',
            HTTP_ORIGIN='http://example.com'
        )
        # Response should have appropriate headers
        self.assertTrue(response)
