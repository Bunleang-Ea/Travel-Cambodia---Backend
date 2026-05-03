from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Booking, Category, City, Itinerary, ItineraryItem, Place, Review

User = get_user_model()


class ItineraryOwnershipTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', password='Password123')
        self.user2 = User.objects.create_user(email='user2@example.com', password='Password123')
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        self.itinerary1 = Itinerary.objects.create(user=self.user1, title='User1 Trip', description='Trip 1')
        self.itinerary2 = Itinerary.objects.create(user=self.user2, title='User2 Trip', description='Trip 2')

    def test_owner_can_access_their_itinerary(self):
        response = self.client.get(
            f'/api/itineraries/{self.itinerary1.id}/',
            HTTP_AUTHORIZATION=f'Token {self.token1.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'User1 Trip')

    def test_user_cannot_access_other_users_itinerary(self):
        response = self.client.get(
            f'/api/itineraries/{self.itinerary2.id}/',
            HTTP_AUTHORIZATION=f'Token {self.token1.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_access_itineraries(self):
        response = self.client.get('/api/itineraries/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_access_itinerary_detail(self):
        response = self.client.get(f'/api/itineraries/{self.itinerary1.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_returns_only_their_itineraries(self):
        response = self.client.get(
            '/api/itineraries/',
            HTTP_AUTHORIZATION=f'Token {self.token1.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'User1 Trip')


class AdminItineraryContentTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@example.com', password='Password123')
        self.admin_token = Token.objects.create(user=self.admin)
        self.user = User.objects.create_user(email='user@example.com', password='Password123')
        self.user_token = Token.objects.create(user=self.user)
        self.category = Category.objects.create(name='Adventure')
        self.city = City.objects.create(name='Phnom Penh', country='Cambodia')

    def test_admin_can_create_and_manage_categories_cities_placess(self):
        response = self.client.post(
            reverse('category-list-create'),
            {'name': 'History', 'description': 'Historic sites'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        category_id = response.data['id']

        response = self.client.post(
            reverse('city-list-create'),
            {'name': 'Siem Reap', 'country': 'Cambodia', 'description': 'Tourist hub'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        city_id = response.data['id']

        response = self.client.post(
            reverse('place-list-create'),
            {
                'title': 'Angkor Wat',
                'description': 'Historic temple complex',
                'category_id': category_id,
                'city_id': city_id,
                'address': 'Krong Siem Reap',
                'contact_info': '+855123456789',
                'map_url': 'https://maps.example.com/angkor-wat',
                'image_url': 'https://images.example.com/angkor-wat.jpg',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Angkor Wat')
        self.assertEqual(response.data['category'], 'History')
        self.assertEqual(response.data['city'], 'Siem Reap, Cambodia')

    def test_regular_user_cannot_access_admin_content_endpoints(self):
        response = self.client.post(
            reverse('category-list-create'),
            {'name': 'Forbidden', 'description': 'No access'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(
            reverse('category-list-create'),
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PlaceDiscoveryTests(APITestCase):
    def setUp(self):
        self.category_food = Category.objects.create(name='Food')
        self.category_temple = Category.objects.create(name='Temple')
        self.city_phnom = City.objects.create(name='Phnom Penh', country='Cambodia')
        self.city_si = City.objects.create(name='Siem Reap', country='Cambodia')
        self.place1 = Place.objects.create(
            title='Local Food Market',
            description='Fresh market with street food',
            category=self.category_food,
            city=self.city_phnom,
        )
        self.place2 = Place.objects.create(
            title='Ancient Temple',
            description='Old temple with carvings',
            category=self.category_temple,
            city=self.city_si,
        )

    def test_place_discovery_returns_places(self):
        response = self.client.get('/api/itineraries/places/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_place_search_filters_by_keyword(self):
        response = self.client.get('/api/itineraries/places/?q=food')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Local Food Market')

    def test_place_search_filters_by_category(self):
        response = self.client.get(f'/api/itineraries/places/?category={self.category_temple.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Ancient Temple')

    def test_place_search_filters_by_city(self):
        response = self.client.get(f'/api/itineraries/places/?city={self.city_phnom.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Local Food Market')

    def test_place_detail_returns_place_information(self):
        response = self.client.get(f'/api/itineraries/places/{self.place1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Local Food Market')
        self.assertEqual(response.data['category'], 'Food')
        self.assertEqual(response.data['city'], 'Phnom Penh, Cambodia')


class ReviewAndServiceRequestTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com', password='Password123')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='Password123')
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)
        self.category = Category.objects.create(name='Adventure')
        self.city = City.objects.create(name='Battambang', country='Cambodia')
        self.place = Place.objects.create(
            title='River Tour',
            description='Boat tour on the river',
            category=self.category,
            city=self.city,
        )

    def test_review_submission_and_display(self):
        response = self.client.post(
            f'/api/itineraries/places/{self.place.id}/reviews/',
            {'place_id': self.place.id, 'rating': 5, 'comment': 'Great tour!'},
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['comment'], 'Great tour!')

        response = self.client.get(f'/api/itineraries/places/{self.place.id}/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['comment'], 'Great tour!')

    def test_review_requires_authentication(self):
        response = self.client.post(
            f'/api/itineraries/places/{self.place.id}/reviews/',
            {'place_id': self.place.id, 'rating': 4, 'comment': 'Nice experience'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_service_request_flow_for_user_and_admin(self):
        response = self.client.post(
            '/api/itineraries/service-requests/',
            {
                'place_id': self.place.id,
                'service_type': 'guide',
                'subject': 'Guide needed',
                'message': 'Need an English-speaking guide for a morning tour.',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['service_type'], 'guide')
        self.assertEqual(response.data['place'], 'River Tour')

        response = self.client.get('/api/itineraries/service-requests/', HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get('/api/itineraries/service-requests/', HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_service_request_detail_requires_authentication(self):
        response = self.client.get('/api/itineraries/service-requests/1/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_access_other_users_service_request(self):
        response = self.client.post(
            '/api/itineraries/service-requests/',
            {
                'place_id': self.place.id,
                'service_type': 'guide',
                'subject': 'Private request',
                'message': 'I need help',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_id = response.data['id']

        other_user = User.objects.create_user(email='other@example.com', password='Password123')
        other_token = Token.objects.create(user=other_user)
        response = self.client.get(f'/api/itineraries/service-requests/{request_id}/', HTTP_AUTHORIZATION=f'Token {other_token.key}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BookingItineraryItemTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com', password='Password123')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='Password123')
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)
        self.category = Category.objects.create(name='Adventure')
        self.city = City.objects.create(name='Battambang', country='Cambodia')
        self.place = Place.objects.create(
            title='River Tour',
            description='Boat tour on the river',
            category=self.category,
            city=self.city,
        )
        self.itinerary = Itinerary.objects.create(user=self.user, title='Weekend Escape')

    def test_booking_workflow(self):
        response = self.client.post(
            '/api/itineraries/bookings/',
            {
                'place_id': self.place.id,
                'service_type': 'guide',
                'start_date': '2026-05-10',
                'end_date': '2026-05-10',
                'guests': 2,
                'notes': 'Need English guide.',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['service_type'], 'guide')
        self.assertEqual(response.data['place'], 'River Tour')

        response = self.client.get('/api/itineraries/bookings/', HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get('/api/itineraries/bookings/', HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_itinerary_item_schedule(self):
        response = self.client.post(
            f'/api/itineraries/{self.itinerary.id}/items/',
            {
                'day_number': 1,
                'title': 'Morning market visit',
                'description': 'Explore local food stalls',
                'place_id': self.place.id,
                'start_time': '08:00:00',
                'end_time': '10:00:00',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['day_number'], 1)
        self.assertEqual(response.data['title'], 'Morning market visit')

        response = self.client.get(
            f'/api/itineraries/{self.itinerary.id}/items/',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Morning market visit')

    def test_review_photo_upload(self):
        image_file = SimpleUploadedFile('photo.jpg', b'fake-image-content', content_type='image/jpeg')
        response = self.client.post(
            f'/api/itineraries/places/{self.place.id}/reviews/',
            {
                'place_id': self.place.id,
                'rating': 5,
                'comment': 'Excellent tour!',
                'image': image_file,
            },
            format='multipart',
            HTTP_AUTHORIZATION=f'Token {self.user_token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['image'])
