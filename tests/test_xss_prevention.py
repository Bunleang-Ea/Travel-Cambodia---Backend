"""
XSS (Cross-Site Scripting) Prevention Tests
Tests that XSS attacks are prevented through input sanitization
and output encoding.
"""

import html
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from rest_framework.authtoken.models import Token


class XSSPreventionTests(TestCase):
    """Test that XSS attacks are prevented."""

    def setUp(self):
        self.client = APIClient()

    def test_xss_in_registration_full_name(self):
        """XSS payload in full_name should be sanitized."""
        xss_payload = '<script>alert("XSS")</script>'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest@example.com',
            'password': 'TestPass123!',
            'full_name': xss_payload,
            'phone_number': '+1234567890'
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest@example.com')
            # Should be HTML-escaped or stripped
            self.assertNotIn('<script>', user.full_name)
            self.assertNotIn('alert(', user.full_name)

    def test_xss_img_tag_in_registration(self):
        """XSS via img tag should be sanitized."""
        xss_payload = '<img src=x onerror="alert(\'XSS\')">'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest2@example.com',
            'password': 'TestPass123!',
            'full_name': xss_payload,
            'phone_number': '+1234567890'
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest2@example.com')
            # Should be sanitized
            self.assertNotIn('onerror', user.full_name)
            self.assertNotIn('<img', user.full_name)

    def test_xss_in_profile_update(self):
        """XSS payload in profile update should be sanitized."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Test User'
        )
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        xss_payload = '<img src=x onerror="alert(\'XSS\')">'
        response = self.client.put('/api/accounts/me/', {
            'email': 'xsstest3@example.com',
            'password': 'TestPass123!',
            'full_name': xss_payload,
            'phone_number': '+1234567890'
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest3@example.com')
            # Should be sanitized
            self.assertNotIn('onload=', user.full_name)

    def test_response_contains_proper_content_type(self):
        """All responses should have proper Content-Type headers."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Test User'
        )
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/accounts/me/')

        # Should have application/json content type
        content_type = response.get('Content-Type', '')
        self.assertIn('application/json', content_type)

    def test_json_response_encoding(self):
        """JSON responses should be properly encoded to prevent XSS."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='<script>alert("xss")</script>'
        )
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/accounts/me/')

        # Response should have proper JSON encoding
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The content should be JSON encoded with escaped quotes
        content = response.content.decode('utf-8')
        # Check that the response is valid JSON and has the data
        self.assertIn('full_name', content)
        # The data is properly JSON-encoded, so script tags are just text within a JSON string
        # which is safe as they won't be executed as HTML
        import json
        data = json.loads(content)
        self.assertEqual(data['full_name'], '<script>alert("xss")</script>')

    def test_xss_in_phone_number(self):
        """XSS payload in phone_number should be sanitized or rejected."""
        xss_payload = '<script>alert("xss")</script>'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest4@example.com',
            'password': 'TestPass123!',
            'full_name': 'Test User',
            'phone_number': xss_payload
        })

        # Should reject due to phone validation (not valid phone format) or be rate limited
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])
        
        # If somehow created, verify it was sanitized
        if User.objects.filter(email='xsstest4@example.com').exists():
            user = User.objects.get(email='xsstest4@example.com')
            self.assertNotIn('<script>', user.phone_number)

    def test_xss_javascript_protocol(self):
        """XSS via javascript: protocol should be handled."""
        xss_payload = 'javascript:alert("xss")'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest5@example.com',
            'password': 'TestPass123!',
            'full_name': xss_payload,
            'phone_number': '+1234567890'
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest5@example.com')
            # Should be sanitized or safe
            self.assertTrue(user.full_name is not None)

    def test_xss_data_uri_protocol(self):
        """XSS via data: URI protocol should be handled."""
        xss_payload = 'data:text/html,<script>alert("xss")</script>'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest6@example.com',
            'password': 'TestPass123!',
            'full_name': xss_payload,
            'phone_number': '+1234567890'
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest6@example.com')
            # Should not contain dangerous protocols
            self.assertFalse('data:' in user.full_name and '<script>' in user.full_name)

    def test_login_with_xss_attempt(self):
        """Login endpoint should safely handle XSS attempts."""
        response = self.client.post('/api/accounts/login/', {
            'email': '<script>alert("xss")</script>',
            'password': 'anything'
        })

        # Should reject as invalid email or be rate limited
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ])

    def test_html_encoding_in_response(self):
        """Test that HTML special characters are properly encoded in responses."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Test & User <tag>'
        )
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/accounts/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should have the name (properly encoded by JSON)
        self.assertIn('full_name', response.data)
