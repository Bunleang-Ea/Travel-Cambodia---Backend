from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Category, Location, PasswordResetOTP, Place, PlaceGallery, SupportTicket, Tag

User = get_user_model()


class AccountFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='Password123!')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='Password123!')
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)
        self.register_url = reverse('account-register')
        self.login_url = reverse('account-login')
        self.password_request_url = reverse('password-reset-request')
        self.password_confirm_url = reverse('password-reset-confirm')
        self.profile_url = reverse('account-profile')
        self.logout_url = reverse('account-logout')
        self.support_ticket_url = reverse('support-ticket-list-create')

    def test_register_and_login(self):
        response = self.client.post(
            self.register_url,
            {
                'email': 'newuser@example.com',
                'password': 'StrongPass123!',
                'full_name': 'New User',
                'phone_number': '+1-234-567-8901',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['email'], 'newuser@example.com')

        response = self.client.post(
            self.login_url,
            {'email': 'newuser@example.com', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_password_reset_otp_flow(self):
        response = self.client.post(self.password_request_url, {'email': self.user.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        otp_record = PasswordResetOTP.objects.filter(user=self.user, used=False).order_by('-created_at').first()
        self.assertIsNotNone(otp_record)

        response = self.client.post(
            self.password_confirm_url,
            {'email': self.user.email, 'otp': otp_record.code, 'new_password': 'NewPassword123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Password updated successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword123!'))

    def test_profile_update_requires_authentication(self):
        response = self.client.put(self.profile_url, {'full_name': 'Updated Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(
            self.profile_url,
            {'full_name': 'Updated Name'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Updated Name')

    def test_logout_revokes_token(self):
        response = self.client.post(
            self.logout_url,
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Logged out successfully.')
        self.assertFalse(Token.objects.filter(key=self.user_token.key).exists())

        response = self.client.get(self.profile_url, format='json', HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_support_ticket_create_and_view(self):
        response = self.client.post(
            self.support_ticket_url,
            {'subject': 'Need help', 'description': 'I cannot update my itinerary.'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['subject'], 'Need help')
        self.assertEqual(response.data['status'], 'open')

        ticket_id = response.data['id']
        detail_url = reverse('support-ticket-detail', kwargs={'pk': ticket_id})
        response = self.client.get(detail_url, format='json', HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], 'Need help')

        other_user = User.objects.create_user(email='other@example.com', password='Password123')
        other_token = Token.objects.create(user=other_user)
        response = self.client.get(detail_url, format='json', HTTP_AUTHORIZATION=f'Token {other_token.key}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_support_ticket_response_requires_admin(self):
        ticket = SupportTicket.objects.create(user=self.user, subject='Login issue', description='Cannot login')
        response = self.client.post(
            reverse('support-ticket-respond', kwargs={'pk': ticket.id}),
            {'status': 'in_progress', 'response': 'We are reviewing your issue.'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse('support-ticket-respond', kwargs={'pk': ticket.id}),
            {'status': 'in_progress', 'response': 'We are reviewing your issue.'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['response'], 'We are reviewing your issue.')

    def test_non_admin_cannot_access_admin_endpoints(self):
        response = self.client.get(
            reverse('admin-user-list'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse('admin-create-user'),
            {
                'email': 'newadmin@example.com',
                'password': 'StrongPass123!',
                'full_name': 'New Admin',
                'phone_number': '+1-000-000-0000',
                'is_staff': True,
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_and_delete_users_and_cannot_delete_self(self):
        response = self.client.post(
            reverse('admin-create-user'),
            {
                'email': 'managed@example.com',
                'password': 'StrongPass123!',
                'full_name': 'Managed User',
                'phone_number': '+1-231-231-2341',
                'is_staff': False,
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user_id = response.data['id']

        response = self.client.delete(
            reverse('admin-delete-user', kwargs={'pk': created_user_id}),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(
            reverse('admin-delete-user', kwargs={'pk': self.admin.id}),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Admins cannot delete their own account while authenticated.')

    def test_support_ticket_requires_authentication(self):
        response = self.client.get(reverse('support-ticket-list-create'), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(
            reverse('support-ticket-list-create'),
            {'subject': 'Test', 'description': 'Test description'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_role_and_permission_endpoints(self):
        response = self.client.get(
            reverse('admin-role-list'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse('admin-permission-list'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            reverse('admin-assign-role'),
            {'email': self.user.email, 'role': 'support'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIn('support', [group.name for group in self.user.groups.all()])

        response = self.client.post(
            reverse('admin-remove-role'),
            {'email': self.user.email, 'role': 'support'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertNotIn('support', [group.name for group in self.user.groups.all()])

    def test_non_admin_cannot_access_admin_role_and_permission_endpoints(self):
        response = self.client.get(
            reverse('admin-role-list'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_health_and_api_docs_are_available(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'ok'})

        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'].split(';')[0], 'application/json')

        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('SwaggerUIBundle', response.content.decode())

        response = self.client.get(
            reverse('admin-permission-list'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PublicPlaceEndpointsTests(APITestCase):
    def setUp(self):
        self.category_temple = Category.objects.create(name='Temple')
        self.category_beach = Category.objects.create(name='Beach')
        self.location_siem_reap = Location.objects.create(name='Siem Reap')
        self.location_sihanoukville = Location.objects.create(name='Sihanoukville')
        self.tag_culture = Tag.objects.create(name='culture')
        self.tag_family = Tag.objects.create(name='family')

        self.published_place = Place.objects.create(
            name='Angkor Wat',
            description='Ancient temple complex',
            publishing_status='Published',
            category=self.category_temple,
            location=self.location_siem_reap,
        )
        self.published_place.tags.set([self.tag_culture, self.tag_family])
        PlaceGallery.objects.create(
            place=self.published_place,
            image_url='https://example.com/angkor.jpg',
            is_main=True,
        )

        self.other_published_place = Place.objects.create(
            name='Otres Beach',
            description='Relaxing beach',
            publishing_status='Published',
            category=self.category_beach,
            location=self.location_sihanoukville,
        )

        self.draft_place = Place.objects.create(
            name='Unpublished Spot',
            description='Draft place',
            publishing_status='Draft',
            category=self.category_temple,
            location=self.location_siem_reap,
        )

    def test_place_list_returns_paginated_published_places_only(self):
        response = self.client.get(reverse('place-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        returned_ids = {item['place_id'] for item in response.data['results']}
        self.assertIn(self.published_place.place_id, returned_ids)
        self.assertIn(self.other_published_place.place_id, returned_ids)
        self.assertNotIn(self.draft_place.place_id, returned_ids)

    def test_place_list_filters_and_validates_category_id(self):
        response = self.client.get(reverse('place-list'), {'category_id': self.category_temple.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['place_id'] for item in response.data['results']}
        self.assertEqual(returned_ids, {self.published_place.place_id})

        invalid_response = self.client.get(reverse('place-list'), {'category_id': 'abc'})
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category_id', invalid_response.data)

    def test_place_detail_increments_view_count(self):
        detail_url = reverse('place-detail', kwargs={'pk': self.published_place.place_id})

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['place_id'], self.published_place.place_id)
        self.assertEqual(response.data['view_count'], 1)

        second_response = self.client.get(detail_url)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data['view_count'], 2)

    def test_public_category_and_tag_endpoints(self):
        category_response = self.client.get(reverse('category-list'))
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
        category_names = {item['name'] for item in category_response.data}
        self.assertIn('Temple', category_names)
        self.assertIn('Beach', category_names)

        tag_response = self.client.get(reverse('tag-list'))
        self.assertEqual(tag_response.status_code, status.HTTP_200_OK)
        tag_names = {item['name'] for item in tag_response.data}
        self.assertIn('culture', tag_names)
        self.assertIn('family', tag_names)
