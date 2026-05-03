from django.db import models
from rest_framework import permissions
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, Category, City, Itinerary, ItineraryItem, Place, Review, Ticket
from .serializers import (
    BookingSerializer,
    CategorySerializer,
    CitySerializer,
    ItineraryItemSerializer,
    ItinerarySerializer,
    PlaceSerializer,
    ReviewSerializer,
    TicketSerializer,
)


class ItineraryListCreateView(ListCreateAPIView):
    serializer_class = ItinerarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Itinerary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ItineraryDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ItinerarySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Itinerary.objects.filter(user=self.request.user)


class CategoryListCreateView(ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Category.objects.all()


class CategoryDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Category.objects.all()
    lookup_field = 'pk'


class CityListCreateView(ListCreateAPIView):
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return City.objects.all()


class CityDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = City.objects.all()
    lookup_field = 'pk'


class PlaceListCreateView(ListCreateAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Place.objects.select_related('city', 'category').all()


class PlaceDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Place.objects.select_related('city', 'category').all()
    lookup_field = 'pk'


class PlaceDiscoveryView(ListAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Place.objects.select_related('city', 'category').all()
        category_id = self.request.query_params.get('category')
        city_id = self.request.query_params.get('city')
        keyword = self.request.query_params.get('q')

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        if keyword:
            queryset = queryset.filter(
                models.Q(title__icontains=keyword)
                | models.Q(description__icontains=keyword)
                | models.Q(address__icontains=keyword)
            )
        return queryset


class PlacePublicDetailView(RetrieveAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Place.objects.select_related('city', 'category').all()
    lookup_field = 'pk'


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Category.objects.all()


class CityListView(ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return City.objects.all()


class PlaceReviewListCreateView(ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        place_id = self.kwargs['place_pk']
        return Review.objects.select_related('user', 'place').filter(place_id=place_id)

    def perform_create(self, serializer):
        place = Place.objects.get(pk=self.kwargs['place_pk'])
        serializer.save(user=self.request.user, place=place)


class UserReviewDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Review.objects.select_related('user', 'place').all()
        return Review.objects.select_related('user', 'place').filter(user=self.request.user)


class ServiceRequestListCreateView(ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Ticket.objects.select_related('user', 'place').all()
        return Ticket.objects.filter(user=self.request.user).select_related('user', 'place')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ServiceRequestDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Ticket.objects.select_related('user', 'place').all()
        return Ticket.objects.filter(user=self.request.user).select_related('user', 'place')


class BookingListCreateView(ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Booking.objects.select_related('user', 'place').all()
        return Booking.objects.filter(user=self.request.user).select_related('user', 'place')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BookingDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Booking.objects.select_related('user', 'place').all()
        return Booking.objects.filter(user=self.request.user).select_related('user', 'place')


class ItineraryItemListCreateView(ListCreateAPIView):
    serializer_class = ItineraryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ItineraryItem.objects.filter(itinerary__user=self.request.user, itinerary_id=self.kwargs['itinerary_pk'])

    def perform_create(self, serializer):
        itinerary = Itinerary.objects.get(pk=self.kwargs['itinerary_pk'], user=self.request.user)
        serializer.save(itinerary=itinerary)


class ItineraryItemDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ItineraryItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return ItineraryItem.objects.filter(itinerary__user=self.request.user, itinerary_id=self.kwargs['itinerary_pk'])


class ReviewListView(ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Review.objects.select_related('user', 'place').all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Review.objects.select_related('user', 'place').all()
    lookup_field = 'pk'


class TicketListView(ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Ticket.objects.select_related('user').all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Ticket.objects.select_related('user').all()
    lookup_field = 'pk'
