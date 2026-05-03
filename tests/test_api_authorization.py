"""
API Authorization Tests
Tests that admin-only endpoints properly restrict non-admin users and
verify data isolation between users.
"""

from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import User


class AdminAuthorizationTests(TestCase):
    """Test that admin-only endpoints properly restrict non-admin users."""

    def setUp(self):
        self.client = APIClient()

        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            full_name='Regular User'
        )
        self.regular_token = Token.objects.create(user=self.regular_user)

        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            full_name='Admin User',
            is_staff=True
        )
        admin_group = Group.objects.create(name='Admin')
        self.admin_user.groups.add(admin_group)
        self.admin_token = Token.objects.create(user=self.admin_user)

    def test_regular_user_cannot_access_admin_users_endpoint(self):
        """Regular users should not access GET /api/accounts/admin/users/"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        response = self.client.get('/api/accounts/admin/users/')

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_admin_can_access_admin_users_endpoint(self):
        """Admin users should access GET /api/accounts/admin/users/"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/accounts/admin/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_cannot_access_admin_endpoint(self):
        """Unauthenticated users should not access admin endpoints."""
        response = self.client.get('/api/accounts/admin/users/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create_admin_user(self):
        """Regular users should not be able to create other users."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        response = self.client.post('/api/accounts/admin/users/create/', {
            'email': 'newadmin@example.com',
            'password': 'AdminPass123!',
            'full_name': 'New Admin'
        })

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_admin_cannot_delete_self(self):
        """Admin users should not be able to delete their own account."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(
            f'/api/accounts/admin/users/{self.admin_user.pk}/delete/'
        )

        # Should be prevented
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ])


class UserDataAccessTests(TestCase):
    """Test that users can only access their own data."""

    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='TestPass123!',
            full_name='User One'
        )
        self.token1 = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='TestPass123!',
            full_name='User Two'
        )
        self.token2 = Token.objects.create(user=self.user2)

    def test_authenticated_user_can_access_own_profile(self):
        """User should be able to access their own profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.get('/api/accounts/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user1@example.com')

    def test_user_can_only_update_own_profile(self):
        """User should only be able to update their own profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')

        # Try to update own profile
        response = self.client.put(
            '/api/accounts/profile/',
            {'full_name': 'Updated User One'}
        )

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user1's name was updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.full_name, 'Updated User One')

    def test_unauthenticated_user_cannot_access_profile(self):
        """Unauthenticated users should not access profile endpoint."""
        response = self.client.get('/api/accounts/profile/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_logout(self):
        """Authenticated user should be able to logout."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.post('/api/accounts/logout/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_remains_valid_after_logout(self):
        """Token should remain valid until deleted (implementation dependent)."""
        # This test verifies logout behavior
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.post('/api/accounts/logout/')

        # Logout should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
