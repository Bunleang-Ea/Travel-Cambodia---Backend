from django.contrib import admin

from .models import Booking, Category, City, Itinerary, ItineraryItem, Place, Review, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'created_at')
    search_fields = ('name', 'country', 'description')
    ordering = ('name',)


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'category', 'address', 'created_at')
    list_filter = ('city', 'category')
    search_fields = ('title', 'description', 'address', 'city__name', 'category__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('place', 'user', 'rating', 'created_at', 'image')
    list_filter = ('rating',)
    search_fields = ('place__title', 'user__email', 'comment')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'user', 'place', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('service_type', 'status')
    search_fields = ('user__email', 'place__title', 'subject')


@admin.register(ItineraryItem)
class ItineraryItemAdmin(admin.ModelAdmin):
    list_display = ('itinerary', 'day_number', 'title', 'start_time', 'end_time')
    list_filter = ('day_number',)
    search_fields = ('title', 'description', 'itinerary__title')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('subject', 'message', 'user__email')


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'start_date', 'end_date', 'created_at')
    list_filter = ('start_date', 'end_date')
    search_fields = ('title', 'description', 'user__email')
