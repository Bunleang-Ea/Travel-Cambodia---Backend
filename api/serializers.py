from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import serializers
from uuid import uuid4
import os

from .models import (
    PasswordResetOTP, SupportTicket, User, 
    Category, Location, Tag, Place, PlaceGallery, SavedPlace,
    Itinerary, ItineraryItem, Review, ReviewPhoto, RoleProfile,
    SystemNotificationSetting,
)

from .models import Contact
from .sanitizers import XSSSanitizer
from .validators import (
    validate_email_format,
    validate_phone_number,
    validate_full_name,
    validate_profile_picture_file,
    validate_otp_format,
    validate_password_special_characters,
    validate_user_email,
    validate_user_phone,
    validate_user_full_name,
)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'phone_number',
            'profile_picture_url',
            'profile_picture',
            'roles',
            'is_staff',
            'is_superuser',
            'is_active',
            'date_joined',
        )
        read_only_fields = (
            'id',
            'roles',
            'is_staff',
            'is_superuser',
            'is_active',
            'date_joined',
        )

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate_phone_number(self, value):
        """Validate and sanitize phone number format."""
        validated = validate_user_phone(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def validate_full_name(self, value):
        """Validate and sanitize full name format."""
        validated = validate_user_full_name(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def get_roles(self, obj):
        return [group.name for group in obj.groups.all()]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('full_name', 'phone_number', 'profile_picture_url', 'profile_picture')

    def validate_email(self, value):
        """Validate email format if provided."""
        if value:
            return validate_email_format(value)
        return value

    def validate_phone_number(self, value):
        """Validate and sanitize phone number format."""
        validated = validate_user_phone(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def validate_full_name(self, value):
        """Validate and sanitize full name format."""
        validated = validate_user_full_name(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def validate_profile_picture(self, value):
        """Validate profile picture file upload."""
        if value:
            return validate_profile_picture_file(value)
        return value


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate_password(self, value):
        """Validate password strength and special characters."""
        validate_password(value)
        validate_password_special_characters(value)
        return value

    def validate(self, attrs):
        first_name = XSSSanitizer.sanitize_input(
            str(attrs.pop('first_name', '')).strip(),
            allow_html=False,
        )
        last_name = XSSSanitizer.sanitize_input(
            str(attrs.pop('last_name', '')).strip(),
            allow_html=False,
        )
        provided_full_name = str(attrs.get('full_name', '')).strip()

        if not provided_full_name:
            if not first_name and not last_name:
                raise serializers.ValidationError(
                    {'full_name': 'Provide full_name or first_name/last_name.'}
                )
            provided_full_name = f'{first_name} {last_name}'.strip()

        attrs['full_name'] = XSSSanitizer.sanitize_input(
            validate_user_full_name(provided_full_name),
            allow_html=False,
        )

        phone_number = attrs.get('phone_number', '')
        if phone_number:
            attrs['phone_number'] = XSSSanitizer.sanitize_input(
                validate_user_phone(phone_number),
                allow_html=False,
            )
        else:
            attrs['phone_number'] = ''

        return attrs


class RegistrationOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate_otp(self, value):
        """Validate OTP format (must be 6 digits)."""
        return validate_otp_format(value)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found.')

        if user.is_active:
            raise serializers.ValidationError('This account is already verified. Please log in.')

        now = timezone.now()
        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            code=otp,
            used=False,
            expires_at__gte=now,
        ).order_by('-created_at').first()
        if not otp_record:
            raise serializers.ValidationError('Invalid or expired OTP.')

        attrs['user'] = user
        attrs['otp_record'] = otp_record
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if email and password:
            existing_user = User.objects.filter(email=email).first()
            if not existing_user:
                raise serializers.ValidationError(
                    'This email is not registered yet. Please sign up first.',
                    code='authorization',
                )
            if not existing_user.is_active:
                raise serializers.ValidationError('User account is disabled.', code='authorization')

            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    'Incorrect password. Please try again.',
                    code='authorization',
                )
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError('Must include "email" and "password".')


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_id_token(self, value):
        token = str(value or '').strip()
        if not token:
            raise serializers.ValidationError('Google ID token is required.')
        return token


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email format and check if user exists."""
        validated_email = validate_email_format(value)
        if not User.objects.filter(email=validated_email).exists():
            raise serializers.ValidationError('No account found for this email address.')
        return validated_email


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate_otp(self, value):
        """Validate OTP format (must be 6 digits)."""
        return validate_otp_format(value)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found.')

        now = timezone.now()
        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            code=otp,
            used=False,
            expires_at__gte=now,
        ).order_by('-created_at').first()
        if not otp_record:
            raise serializers.ValidationError('Invalid or expired OTP.')
        attrs['user'] = user
        attrs['otp_record'] = otp_record
        return attrs


class PasswordResetConfirmSerializer(PasswordResetVerifySerializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        """Validate password strength and special character requirements."""
        validate_password(value)
        validate_password_special_characters(value)
        return value

    def save(self):
        user = self.validated_data['user']
        otp_record = self.validated_data['otp_record']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        otp_record.used = True
        otp_record.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not user.check_password(value):
            raise serializers.ValidationError('Incorrect current password.')
        return value

    def validate_new_password(self, value):
        validate_password(value)
        validate_password_special_characters(value)
        return value

    def save(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None:
            raise serializers.ValidationError('User context is required.')
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'content_type')


class RoleAssignmentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()

    def validate(self, attrs):
        try:
            attrs['user'] = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found.')
        return attrs


class RolePermissionAssignmentSerializer(serializers.Serializer):
    role = serializers.CharField()
    permission_codename = serializers.CharField()
    content_type_app_label = serializers.CharField()
    content_type_model = serializers.CharField()

    def validate(self, attrs):
        from django.contrib.contenttypes.models import ContentType

        try:
            attrs['group'] = Group.objects.get(name=attrs['role'])
        except Group.DoesNotExist:
            raise serializers.ValidationError('Role not found.')

        try:
            content_type = ContentType.objects.get(app_label=attrs['content_type_app_label'], model=attrs['content_type_model'])
        except ContentType.DoesNotExist:
            raise serializers.ValidationError('Content type not found.')

        try:
            attrs['permission'] = Permission.objects.get(
                codename=attrs['permission_codename'],
                content_type=content_type,
            )
        except Permission.DoesNotExist:
            raise serializers.ValidationError('Permission not found.')

        return attrs


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            'id',
            'user',
            'subject',
            'description',
            'status',
            'response',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'status', 'response', 'created_at', 'updated_at')

    def validate_subject(self, value):
        """Validate support ticket subject."""
        if not value or not isinstance(value, str):
            raise serializers.ValidationError('Subject must be a non-empty string.')
        
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError('Subject must be at least 5 characters long.')
        
        if len(value) > 255:
            raise serializers.ValidationError('Subject must not exceed 255 characters.')
        
        if '\x00' in value:
            raise serializers.ValidationError('Subject contains invalid characters.')
        
        return value

    def validate_description(self, value):
        """Validate support ticket description."""
        if not value or not isinstance(value, str):
            raise serializers.ValidationError('Description must be a non-empty string.')
        
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Description must be at least 10 characters long.')
        
        if len(value) > 5000:
            raise serializers.ValidationError('Description must not exceed 5000 characters.')
        
        if '\x00' in value:
            raise serializers.ValidationError('Description contains invalid characters.')
        
        return value


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id',
            'user',
            'name',
            'email',
            'phone',
            'subject',
            'message',
            'is_resolved',
            'admin_reply',
            'created_at',
        )
        read_only_fields = ('id', 'user', 'created_at')

    def validate_name(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Name is required.')
        return XSSSanitizer.sanitize_input(str(value).strip(), allow_html=False)

    def validate_email(self, value):
        return validate_email_format(value)

    def validate_phone(self, value):
        if not value:
            return ''
        return validate_phone_number(value)

    def validate_subject(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Subject is required.')
        return XSSSanitizer.sanitize_input(str(value).strip(), allow_html=False)

    def validate_message(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Message is required.')
        return XSSSanitizer.sanitize_input(str(value).strip(), allow_html=False)


class AdminContactSerializer(ContactSerializer):
    user = UserSerializer(read_only=True)

    class Meta(ContactSerializer.Meta):
        fields = ContactSerializer.Meta.fields


class SupportTicketResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ('status', 'response')


class AdminCreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'phone_number', 'profile_picture_url', 'is_staff', 'is_active')

    def validate_email(self, value):
        """Validate email format and check for duplicates."""
        validated_email = validate_email_format(value)
        if User.objects.filter(email=validated_email).exists():
            raise serializers.ValidationError('This email is already registered.')
        return validated_email

    def validate_password(self, value):
        """Validate password strength and special character requirements."""
        validate_password(value)
        validate_password_special_characters(value)
        return value

    def validate_full_name(self, value):
        """Validate full name format."""
        return validate_user_full_name(value)

    def validate_phone_number(self, value):
        """Validate phone number format."""
        return validate_user_phone(value)

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class SuperAdminUserUpdateSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = User
        fields = (
            'full_name',
            'phone_number',
            'is_active',
            'is_staff',
            'is_superuser',
            'roles',
        )

    def validate_full_name(self, value):
        if value is None:
            return value
        return validate_user_full_name(value)

    def validate_phone_number(self, value):
        if value in (None, ''):
            return ''
        return validate_user_phone(value)

    def validate_roles(self, value):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return list(dict.fromkeys(normalized))

    def update(self, instance, validated_data):
        roles = validated_data.pop('roles', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if roles is not None:
            groups = []
            for role_name in roles:
                group, _ = Group.objects.get_or_create(name=role_name)
                groups.append(group)
            instance.groups.set(groups)
        return instance


class SuperAdminRoleSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    permissions_count = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'description',
            'users_count',
            'permissions_count',
            'users',
        )

    def get_description(self, obj):
        profile = getattr(obj, 'role_profile', None)
        return profile.description if profile else ''

    def get_users_count(self, obj):
        return obj.user_set.count()

    def get_permissions_count(self, obj):
        return obj.permissions.count()

    def get_users(self, obj):
        users = obj.user_set.all().order_by('email')[:5]
        return [
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
            }
            for user in users
        ]


class SuperAdminRoleUpsertSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value):
        cleaned = str(value).strip()
        if not cleaned:
            raise serializers.ValidationError('Role name is required.')
        return cleaned

    def validate_description(self, value):
        return str(value).strip()


class SuperAdminRolePermissionsUpdateSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        allow_empty=True,
    )


class SuperAdminNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemNotificationSetting
        fields = (
            'critical_errors',
            'new_users',
            'automated_backups',
            'updated_at',
        )
        read_only_fields = ('updated_at',)

class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'image', 'image_url')

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class AdminCategorySerializer(serializers.ModelSerializer):
    places_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'image', 'image_url', 'places_count')

    def get_places_count(self, obj):
        return obj.places.count()

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def validate_image(self, value):
        if value:
            return validate_profile_picture_file(value)
        return value

class LocationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ('id', 'name', 'image', 'image_url')

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class AdminLocationSerializer(serializers.ModelSerializer):
    places_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ('id', 'name', 'image', 'image_url', 'places_count')

    def get_places_count(self, obj):
        return obj.places.count()

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def validate_image(self, value):
        if value:
            return validate_profile_picture_file(value)
        return value

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class PlaceGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceGallery
        fields = '__all__'

class PlaceSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    gallery_images = PlaceGallerySerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = '__all__'

    def get_image(self, obj):
        gallery_images = list(obj.gallery_images.all())
        main_gallery = next(
            (image for image in gallery_images if bool(image.is_main)),
            None,
        )
        if main_gallery:
            return main_gallery.image_url

        return gallery_images[0].image_url if gallery_images else None


class AdminPlaceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    location_name_input = serializers.CharField(write_only=True, required=False, allow_blank=True)
    main_image = serializers.FileField(write_only=True, required=False, allow_null=True)
    main_image_url = serializers.CharField(write_only=True, required=False, allow_null=True)
    gallery_image_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    keep_gallery_image_urls = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    image = serializers.SerializerMethodField(read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )
    tags = TagSerializer(many=True, read_only=True)
    gallery_images = PlaceGallerySerializer(many=True, read_only=True)

    class Meta:
        model = Place
        fields = (
            'place_id',
            'name',
            'description',
            'contact_info',
            'map_link',
            'latitude',
            'longitude',
            'publishing_status',
            'is_featured',
            'best_time_to_visit',
            'recommended_duration',
            'dress_code',
            'opening_hours',
            'average_rating',
            'review_count',
            'view_count',
            'created_at',
            'category',
            'category_name',
            'location',
            'location_name',
            'location_name_input',
            'image',
            'main_image',
            'main_image_url',
            'gallery_image_files',
            'keep_gallery_image_urls',
            'tags',
            'tag_names',
            'gallery_images',
        )
        read_only_fields = (
            'place_id',
            'average_rating',
            'review_count',
            'view_count',
            'created_at',
            'category_name',
            'location_name',
            'tags',
            'gallery_images',
        )
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
            'location': {'required': False, 'allow_null': True},
        }

    def get_image(self, obj):
        gallery_images = list(obj.gallery_images.all())
        main_gallery = next(
            (image for image in gallery_images if bool(image.is_main)),
            None,
        )
        if main_gallery:
            return main_gallery.image_url

        return gallery_images[0].image_url if gallery_images else None

    def validate_main_image(self, value):
        if value:
            return validate_profile_picture_file(value)
        return value

    def validate_gallery_image_files(self, value):
        files = value if isinstance(value, list) else [value]
        for file_obj in files:
            validate_profile_picture_file(file_obj)
        return value

    def validate(self, attrs):
        location = attrs.get('location')
        location_name_input = str(attrs.get('location_name_input', '')).strip()

        if self.instance is None and location is None and not location_name_input:
            raise serializers.ValidationError(
                {'location_name_input': 'Location is required.'}
            )

        return attrs

    def _resolve_tags(self, tag_names):
        tags = []
        for name in tag_names:
            tag_name = str(name).strip()
            if not tag_name:
                continue
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)
        return tags

    def _resolve_location(self, validated_data, instance=None):
        location = validated_data.pop('location', None)
        location_name_input = str(
            validated_data.pop('location_name_input', '')
        ).strip()

        if location is not None:
            return location

        if location_name_input:
            location, _ = Location.objects.get_or_create(name=location_name_input)
            return location

        return instance.location if instance is not None else None

    def _store_uploaded_image(self, uploaded_image):
        extension = os.path.splitext(uploaded_image.name or '')[1].lower()
        if not extension:
            extension = '.jpg'

        file_name = f"places/{uuid4().hex}{extension}"
        stored_path = default_storage.save(file_name, uploaded_image)
        relative_url = default_storage.url(stored_path)

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    def _upsert_main_gallery_image(self, place, uploaded_image):
        image_url = self._store_uploaded_image(uploaded_image)
        main_gallery = place.gallery_images.filter(is_main=True).first()

        if main_gallery:
            main_gallery.image_url = image_url
            main_gallery.save(update_fields=['image_url'])
            return

        first_gallery = place.gallery_images.first()
        if first_gallery:
            first_gallery.image_url = image_url
            first_gallery.is_main = True
            first_gallery.save(update_fields=['image_url', 'is_main'])
            place.gallery_images.exclude(pk=first_gallery.pk).filter(
                is_main=True
            ).update(is_main=False)
            return

        PlaceGallery.objects.create(
            place=place,
            image_url=image_url,
            is_main=True,
        )

    def _extract_gallery_image_files(self, validated_data):
        gallery_files = validated_data.pop('gallery_image_files', [])
        if gallery_files and not isinstance(gallery_files, list):
            gallery_files = [gallery_files]

        request = self.context.get('request')
        if request:
            from_request = request.FILES.getlist('gallery_image_files')
            if from_request:
                gallery_files = from_request

        return [file_obj for file_obj in gallery_files if file_obj]

    def _append_gallery_images(self, place, uploaded_images):
        if not uploaded_images:
            return

        has_main_image = place.gallery_images.filter(is_main=True).exists()
        for index, uploaded_image in enumerate(uploaded_images):
            image_url = self._store_uploaded_image(uploaded_image)
            PlaceGallery.objects.create(
                place=place,
                image_url=image_url,
                is_main=(not has_main_image and index == 0),
            )

    def create(self, validated_data):
        tag_names = validated_data.pop('tag_names', [])
        main_image = validated_data.pop('main_image', None)
        gallery_image_files = self._extract_gallery_image_files(validated_data)
        location = self._resolve_location(validated_data)

        place = Place.objects.create(location=location, **validated_data)
        place.tags.set(self._resolve_tags(tag_names))
        if main_image:
            self._upsert_main_gallery_image(place, main_image)
        if gallery_image_files:
            self._append_gallery_images(place, gallery_image_files)
        return place

    def update(self, instance, validated_data):
        tag_names = validated_data.pop('tag_names', None)
        main_image = validated_data.pop('main_image', None)
        main_image_url = validated_data.pop('main_image_url', None)
        gallery_image_files = self._extract_gallery_image_files(validated_data)
        keep_gallery_image_urls = validated_data.pop('keep_gallery_image_urls', None)
        location = self._resolve_location(validated_data, instance=instance)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.location = location
        instance.save()

        if tag_names is not None:
            instance.tags.set(self._resolve_tags(tag_names))

        if keep_gallery_image_urls is not None:
            from urllib.parse import urlparse
            def get_clean_path(url):
                try:
                    return urlparse(url).path.lstrip('/')
                except Exception:
                    return url.lstrip('/')
            clean_keep_paths = {get_clean_path(url) for url in keep_gallery_image_urls if url}
            
            to_delete_pks = []
            for gallery_img in instance.gallery_images.all():
                db_path = get_clean_path(gallery_img.image_url)
                if db_path not in clean_keep_paths:
                    to_delete_pks.append(gallery_img.pk)
            
            if to_delete_pks:
                instance.gallery_images.filter(pk__in=to_delete_pks).delete()
        elif main_image:
            instance.gallery_images.all().delete()

        if main_image:
            instance.gallery_images.all().update(is_main=False)
            self._upsert_main_gallery_image(instance, main_image)
        elif main_image_url:
            instance.gallery_images.filter(image_url=main_image_url).update(is_main=True)
            instance.gallery_images.exclude(image_url=main_image_url).update(is_main=False)

        if gallery_image_files:
            self._append_gallery_images(instance, gallery_image_files)

        return instance

class PlaceListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Place
        fields = ('place_id', 'name', 'description', 'average_rating', 'review_count', 'view_count', 'category_name', 'location_name', 'is_featured', 'publishing_status')

class ItineraryItemSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source='place.name', read_only=True)

    class Meta:
        model = ItineraryItem
        fields = ('item_id', 'itinerary', 'place', 'place_name', 'day_number', 'planned_time', 'notes')
        read_only_fields = ('item_id',)

class ItinerarySerializer(serializers.ModelSerializer):
    items = ItineraryItemSerializer(many=True, read_only=True)
    image = serializers.URLField(source='image_url', required=False, allow_blank=True, allow_null=True)

    # Accept frontend camelCase write fields while keeping canonical snake_case fields for the model.
    destination = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tripType = serializers.CharField(write_only=True, required=False, allow_blank=True)
    startDate = serializers.DateField(write_only=True, required=False, allow_null=True)
    endDate = serializers.DateField(write_only=True, required=False, allow_null=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Itinerary
        fields = (
            'itinerary_id',
            'user',
            'title',
            'image',
            'description',
            'start_date',
            'end_date',
            'created_at',
            'updated_at',
            'items',
            # frontend-friendly write fields
            'destination',
            'tripType',
            'startDate',
            'endDate',
            'notes',
        )
        read_only_fields = ('itinerary_id', 'user', 'created_at', 'updated_at')
        extra_kwargs = {
            # Frontend sends `destination` instead of `title` on create.
            'title': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'start_date': {'required': False, 'allow_null': True},
            'end_date': {'required': False, 'allow_null': True},
        }

    def to_internal_value(self, data):
        # Frontend can submit empty string for optional dates. Normalize to null.
        mutable = data.copy() if hasattr(data, 'copy') else dict(data)
        for key in ('startDate', 'endDate', 'start_date', 'end_date'):
            if mutable.get(key, None) == '':
                mutable[key] = None
        return super().to_internal_value(mutable)

    def _pop_frontend_fields(self, validated_data):
        # Prefer explicit snake_case if provided, otherwise map camelCase
        title = validated_data.pop('title', None) or validated_data.pop('destination', None)
        image_url = validated_data.pop('image_url', None)
        description = validated_data.pop('description', None) or validated_data.pop('notes', None)
        start_date = validated_data.pop('start_date', None)
        if start_date is None:
            start_date = validated_data.pop('startDate', None)
        end_date = validated_data.pop('end_date', None)
        if end_date is None:
            end_date = validated_data.pop('endDate', None)

        return title, image_url, description, start_date, end_date

    def create(self, validated_data, **kwargs):
        user = kwargs.pop('user', None)
        title, image_url, description, start_date, end_date = self._pop_frontend_fields(validated_data)

        if user is None:
            user = getattr(self.context.get('request'), 'user', None) if self.context else None

        if not title:
            title = 'Untitled Itinerary'

        itinerary = Itinerary.objects.create(
            user=user,
            title=title,
            image_url=image_url or None,
            description=description or '',
            start_date=start_date,
            end_date=end_date,
        )
        return itinerary

    def update(self, instance, validated_data, **kwargs):
        title, image_url, description, start_date, end_date = self._pop_frontend_fields(validated_data)

        if title is not None:
            instance.title = title
        if image_url is not None:
            instance.image_url = image_url or None
        if description is not None:
            instance.description = description
        if start_date is not None:
            instance.start_date = start_date
        if end_date is not None:
            instance.end_date = end_date

        instance.save()
        return instance

class ReviewPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPhoto
        fields = ('photo_id', 'image_url')

class ReviewSerializer(serializers.ModelSerializer):
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    photo_urls = serializers.ListField(
        child=serializers.URLField(max_length=500),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    photo_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    
    class Meta:
        model = Review
        fields = (
            'review_id',
            'user',
            'user_name',
            'user_email',
            'place',
            'rating',
            'comment',
            'is_approved',
            'created_at',
            'updated_at',
            'photos',
            'photo_urls',
            'photo_files',
        )
        read_only_fields = ('review_id', 'user', 'created_at', 'updated_at')
        
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value

    def validate_photo_files(self, value):
        files = value if isinstance(value, list) else [value]
        for file_obj in files:
            validate_profile_picture_file(file_obj)
        return value

    def _extract_photo_files(self, validated_data):
        photo_files = validated_data.pop('photo_files', [])
        if photo_files and not isinstance(photo_files, list):
            photo_files = [photo_files]

        request = self.context.get('request')
        if request:
            from_request = request.FILES.getlist('photo_files')
            if from_request:
                photo_files = from_request

        cleaned_files = []
        for file_obj in photo_files:
            if not file_obj:
                continue
            validate_profile_picture_file(file_obj)
            cleaned_files.append(file_obj)
        return cleaned_files

    def _store_uploaded_photo(self, uploaded_photo):
        extension = os.path.splitext(uploaded_photo.name or '')[1].lower()
        if not extension:
            extension = '.jpg'

        file_name = f"reviews/{uuid4().hex}{extension}"
        stored_path = default_storage.save(file_name, uploaded_photo)
        relative_url = default_storage.url(stored_path)

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    def _sync_photos(self, review, photo_urls, uploaded_files, replace=False):
        if replace:
            review.photos.all().delete()

        for photo_url in photo_urls:
            cleaned_url = str(photo_url).strip()
            if cleaned_url:
                ReviewPhoto.objects.create(review=review, image_url=cleaned_url)

        for uploaded_file in uploaded_files:
            image_url = self._store_uploaded_photo(uploaded_file)
            ReviewPhoto.objects.create(review=review, image_url=image_url)

    def create(self, validated_data):
        photo_urls = validated_data.pop('photo_urls', [])
        uploaded_files = self._extract_photo_files(validated_data)

        review = Review.objects.create(**validated_data)
        self._sync_photos(review, photo_urls, uploaded_files, replace=False)
        return review

    def update(self, instance, validated_data):
        photo_urls = validated_data.pop('photo_urls', None)
        uploaded_files = self._extract_photo_files(validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        should_replace_photos = (
            photo_urls is not None
            or bool(uploaded_files)
            or 'photo_files' in self.initial_data
        )
        if should_replace_photos:
            self._sync_photos(
                instance,
                photo_urls or [],
                uploaded_files,
                replace=True,
            )

        return instance
