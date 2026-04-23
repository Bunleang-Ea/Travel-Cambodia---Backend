from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

# Your models here
class Location(models.Model):
    # Django auto-creates an 'id' field, but we can explicitly define yours to match the blueprint
    location_id = models.AutoField(primary_key=True)
    
    # max_length is required for CharFields. blank=True, null=True means it's optional
    city_name = models.CharField(max_length=100, blank=True, null=True)
    province_name = models.CharField(max_length=100) # Cannot be null based on your DBML

    def __str__(self):
        # This determines how the record looks in the Django Admin panel
        if self.city_name:
            return f"{self.city_name}, {self.province_name}"
        return self.province_name


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # URLField is a special Django CharField that validates the text is an actual link
    icon_url = models.URLField(max_length=500, blank=True, null=True)
    display_in_menu = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        # If we don't do this, Django will name it "Categorys" in the database/admin panel
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.category_name


class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    tag_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.tag_name


class SystemSetting(models.Model):
    # This one uses setting_key as the primary key instead of an integer ID
    setting_key = models.CharField(max_length=100, primary_key=True)
    setting_value = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # auto_now=True automatically updates to 'now()' every time this row is saved/updated
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.setting_key
    
# ==========================================
# USER & AUTHENTICATION
# ==========================================

class User(AbstractUser):
    # Overriding the default email field to force uniqueness
    email = models.EmailField(unique=True)
    
    # Custom Fields from your DBML
    auth_provider = models.CharField(max_length=20, default="local") # 'local' or 'google'
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.CharField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_photo = models.URLField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    trip_updates_enabled = models.BooleanField(default=True)
    
    # Account Status Dropdown
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Inactive', 'Inactive'),
    ]
    account_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    # This tells Django: "Ignore usernames. Users MUST log in with their email."
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class OTPVerification(models.Model):
    otp_id = models.AutoField(primary_key=True)
    
    # Links directly to your new Custom User
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    
    otp_code = models.CharField(max_length=6)
    expired_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.email}"
    
# ==========================================
# DESTINATIONS & PLACES
# ==========================================

class Place(models.Model):
    place_id = models.AutoField(primary_key=True)
    
    # FOREIGN KEYS: Linking to the Core tables we built in Phase 1
    # on_delete=models.CASCADE means if a Location is deleted, all its Places are deleted.
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='places')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='places')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    contact_info = models.CharField(max_length=255, blank=True, null=True)
    map_link = models.URLField(max_length=500, blank=True, null=True)
    
    # Decimals for precise GPS coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    ]
    publishing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    is_featured = models.BooleanField(default=False)
    
    best_time_to_visit = models.CharField(max_length=100, blank=True, null=True)
    recommended_duration = models.CharField(max_length=100, blank=True, null=True)
    dress_code = models.CharField(max_length=100, blank=True, null=True)
    opening_hours = models.CharField(max_length=255, blank=True, null=True)
    
    # The Denormalized Fields: We kept these here for read-speed optimization!
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    
    # auto_now_add=True sets the timestamp ONLY when the place is first created
    created_at = models.DateTimeField(auto_now_add=True)

    # ==========================================
    # THE "SIMPLE" M:N RELATIONSHIP 
    # ==========================================
    # Django will read this single line and automatically generate 
    # the hidden PLACE_TAG SQL table in your database for you!
    tags = models.ManyToManyField(Tag, related_name='places', blank=True)

    def __str__(self):
        return self.name


class PlaceGallery(models.Model):
    image_id = models.AutoField(primary_key=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='gallery_images')
    image_url = models.URLField(max_length=500)
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.place.name}"


# ==========================================
# THE "DATA-RICH" M:N RELATIONSHIP 
# ==========================================
class SavedPlace(models.Model):
    # Because we need the `saved_at` timestamp, we explicitly create this junction table.
    
    # Notice we use settings.AUTH_USER_MODEL instead of importing the User directly.
    # This is the safest way to link to custom users in Django!
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_places')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='saved_by_users')
    
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A professional Database Architect trick:
        # This constraint prevents a user from saving the exact same place twice!
        unique_together = ('user', 'place')

    def __str__(self):
        # We can pull the email dynamically because of the Foreign Key
        return f"User {self.user.email} saved {self.place.name}"
    
# ==========================================
# ITINERARIES & TRIP PLANNING
# ==========================================

class Itinerary(models.Model):
    itinerary_id = models.AutoField(primary_key=True)
    
    # Linking back to the custom user. 
    # Because we imported settings at the top, we use settings.AUTH_USER_MODEL
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='itineraries')
    
    trip_name = models.CharField(max_length=255)
    
    TRIP_TYPE_CHOICES = [
        ('Solo Travel', 'Solo Travel'),
        ('Family', 'Family'),
        ('Business', 'Business'),
        ('Honeymoon', 'Honeymoon'),
    ]
    trip_type = models.CharField(max_length=50, choices=TRIP_TYPE_CHOICES, blank=True, null=True)
    
    # We use DateField instead of DateTimeField because we only care about the calendar day
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    
    cover_image_url = models.URLField(max_length=500, blank=True, null=True)
    quick_notes = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Upcoming', 'Upcoming'),
        ('Current', 'Current'),
        ('Completed', 'Completed'),
        ('Archived', 'Archived'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trip_name} by {self.user.email}"


class ItineraryItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    
    # Linking the specific item to its parent Itinerary and the actual Place
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='items')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='itinerary_appearances')
    
    day_number = models.IntegerField(default=1)
    
    # This integer field is what your React frontend will update when a user drags and drops a card!
    sequence_order = models.IntegerField(default=0) 
    
    # We use TimeField because we only care about the clock time (e.g., 14:30), not the date
    arrival_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        # A Database Architect Pro-Tip:
        # This guarantees that whenever we fetch items from the database, 
        # they are automatically sorted by Day first, and then by their Drag-and-Drop order!
        ordering = ['day_number', 'sequence_order']

    def __str__(self):
        return f"{self.itinerary.trip_name} - Day {self.day_number}: {self.place.name}"
    
# ==========================================
# REVIEWS & MODERATION
# ==========================================

class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    
    # Here is that data integrity constraint! It strictly forces the database to only accept 1 through 5.
    star_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    comment_text = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ('Live', 'Live'),
        ('Needs Review', 'Needs Review'),
        ('Reported', 'Reported'),
        ('Taken Down', 'Taken Down'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Live')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.star_rating}-Star Review by {self.user.email} for {self.place.name}"


class ReviewPhoto(models.Model):
    photo_id = models.AutoField(primary_key=True)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='photos')
    photo_url = models.URLField(max_length=500)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Review #{self.review.review_id}"


class ReviewReport(models.Model):
    # This feeds your Admin Moderation Dashboard
    report_id = models.AutoField(primary_key=True)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    
    # We must explicitly define a different related_name here so it doesn't clash with the main reviews
    reported_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports')
    
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on Review #{self.review.review_id} by {self.reported_by_user.email}"
    