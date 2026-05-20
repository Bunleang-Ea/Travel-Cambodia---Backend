import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    profile_picture_url = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_otps'
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['code', 'used']),
        ]

    def __str__(self):
        return f'OTP for {self.user.email} - {self.code}'

    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at

    @classmethod
    def create_otp(cls, user, lifetime_minutes=15):
        code = f'{random.randint(0, 999999):06d}'
        expires_at = timezone.now() + timedelta(minutes=lifetime_minutes)
        return cls.objects.create(user=user, code=code, expires_at=expires_at)


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        CLOSED = 'closed', 'Closed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Support Ticket #{self.pk} for {self.user.email} - {self.status}'

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Place(models.Model):
    PUBLISHING_STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    )

    place_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    contact_info = models.CharField(max_length=255, blank=True, null=True)
    map_link = models.URLField(max_length=500, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    publishing_status = models.CharField(max_length=20, choices=PUBLISHING_STATUS_CHOICES, default='Draft')
    is_featured = models.BooleanField(default=False)
    best_time_to_visit = models.CharField(max_length=100, blank=True, null=True)
    recommended_duration = models.CharField(max_length=100, blank=True, null=True)
    dress_code = models.CharField(max_length=100, blank=True, null=True)
    opening_hours = models.CharField(max_length=255, blank=True, null=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    review_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='places')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='places')
    tags = models.ManyToManyField(Tag, blank=True, related_name='places')

    def __str__(self):
        return self.name

class PlaceGallery(models.Model):
    image_id = models.AutoField(primary_key=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='gallery_images')
    image_url = models.URLField(max_length=500)
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.place.name}"

class SavedPlace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_places')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='saved_by_users')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place')

    def __str__(self):
        return f"{self.user.email} saved {self.place.name}"

class Itinerary(models.Model):
    itinerary_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='itineraries')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ItineraryItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='items')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='itinerary_items')
    day_number = models.IntegerField(default=1)
    planned_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('day_number', 'planned_time')

    def __str__(self):
        return f'{self.place.name} on Day {self.day_number}'

class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'place')

    def __str__(self):
        return f'Review by {self.user.email} for {self.place.name}'

class ReviewPhoto(models.Model):
    photo_id = models.AutoField(primary_key=True)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='photos')
    image_url = models.URLField(max_length=500)

    def __str__(self):
        return f'Photo for review {self.review.review_id}'

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=Review)
def update_place_rating(sender, instance, **kwargs):
    place = instance.place
    reviews = place.reviews.all()
    if reviews.exists():
        import statistics
        avg = statistics.mean([r.rating for r in reviews])
        place.average_rating = round(avg, 2)
        place.review_count = reviews.count()
    else:
        place.average_rating = 0.0
        place.review_count = 0
    place.save()
