from rest_framework import serializers

from .models import Booking, Category, City, Itinerary, ItineraryItem, Place, Review, Ticket


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'name', 'country', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class PlaceSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    city_id = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), source='city', write_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = (
            'id',
            'title',
            'description',
            'category',
            'city',
            'category_id',
            'city_id',
            'address',
            'contact_info',
            'map_url',
            'latitude',
            'longitude',
            'image_url',
            'average_rating',
            'review_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'average_rating', 'review_count')

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0
        return round(sum(review.rating for review in reviews) / reviews.count(), 1)

    def get_review_count(self, obj):
        return obj.reviews.count()


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    place = serializers.StringRelatedField(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all(), source='place', write_only=True)
    image = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Review
        fields = ('id', 'user', 'place', 'place_id', 'rating', 'comment', 'image_url', 'image', 'created_at')
        read_only_fields = ('id', 'user', 'place', 'created_at')


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    place = serializers.StringRelatedField(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all(), source='place', write_only=True, required=False, allow_null=True)

    class Meta:
        model = Booking
        fields = (
            'id',
            'user',
            'place',
            'place_id',
            'service_type',
            'start_date',
            'end_date',
            'guests',
            'status',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'place', 'created_at', 'updated_at')


class ItineraryItemSerializer(serializers.ModelSerializer):
    itinerary = serializers.PrimaryKeyRelatedField(read_only=True)
    place = serializers.StringRelatedField(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all(), source='place', write_only=True, required=False, allow_null=True)

    class Meta:
        model = ItineraryItem
        fields = (
            'id',
            'itinerary',
            'day_number',
            'title',
            'description',
            'place',
            'place_id',
            'start_time',
            'end_time',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'itinerary')


class ItinerarySerializer(serializers.ModelSerializer):
    items = ItineraryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Itinerary
        fields = ('id', 'title', 'description', 'start_date', 'end_date', 'items', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TicketSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    place = serializers.StringRelatedField(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=Place.objects.all(), source='place', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Ticket
        fields = (
            'id',
            'user',
            'place',
            'place_id',
            'service_type',
            'subject',
            'message',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'place', 'created_at', 'updated_at')


class TicketAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            'service_type',
            'subject',
            'message',
            'status',
        )
        read_only_fields = ('service_type', 'subject', 'message')
