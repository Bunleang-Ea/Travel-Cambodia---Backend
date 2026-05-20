from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import (
    PasswordResetOTP, SupportTicket, User, 
    Category, Location, Tag, Place, PlaceGallery, SavedPlace
)
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
            'is_active',
            'date_joined',
        )
        read_only_fields = ('id', 'roles', 'is_staff', 'is_active', 'date_joined')

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


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'phone_number')

    def validate_email(self, value):
        """Validate email format and check for duplicates."""
        validated_email = validate_email_format(value)
        # Check for existing user with this email
        if User.objects.filter(email=validated_email).exists():
            raise serializers.ValidationError('This email is already registered.')
        return validated_email

    def validate_password(self, value):
        """Validate password strength and special characters."""
        validate_password(value)
        # Additionally validate special character requirements
        validate_password_special_characters(value)
        return value

    def validate_full_name(self, value):
        """Validate and sanitize full name format."""
        validated = validate_user_full_name(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def validate_phone_number(self, value):
        """Validate and sanitize phone number format."""
        validated = validate_user_phone(value)
        return XSSSanitizer.sanitize_input(validated, allow_html=False)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


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
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.', code='authorization')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.', code='authorization')
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError('Must include "email" and "password".')


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email format and check if user exists."""
        validated_email = validate_email_format(value)
        if not User.objects.filter(email=validated_email).exists():
            raise serializers.ValidationError('No account found for this email address.')
        return validated_email


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        """Validate email format."""
        return validate_email_format(value)

    def validate_otp(self, value):
        """Validate OTP format (must be 6 digits)."""
        return validate_otp_format(value)

    def validate_new_password(self, value):
        """Validate password strength and special character requirements."""
        validate_password(value)
        validate_password_special_characters(value)
        return value

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

    def save(self):
        user = self.validated_data['user']
        otp_record = self.validated_data['otp_record']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        otp_record.used = True
        otp_record.save()
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

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

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

    class Meta:
        model = Place
        fields = '__all__'

class PlaceListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Place
        fields = ('place_id', 'name', 'description', 'average_rating', 'review_count', 'view_count', 'category_name', 'location_name', 'is_featured', 'publishing_status')
