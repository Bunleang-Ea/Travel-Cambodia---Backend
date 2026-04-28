from rest_framework import serializers
from .models import Place

class PlaceSerializer(serializers.ModelSerializer):
    # These lines tell Django: "Don't just give me Location ID 1. Give me the actual City Name!"
    location = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Place
        # We specify exactly which columns we want to send to the frontend React app
        fields = [
            'place_id', 
            'name', 
            'location', 
            'category', 
            'description', 
            'latitude', 
            'longitude', 
            'average_rating', 
            'tags'
        ]

from django.contrib.auth import get_user_model

# We use get_user_model() to securely reference our custom api.User
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
        # This security rule ensures passwords are NEVER sent back to the frontend in a response!
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # We silently pass the email into the username field to keep Django's AbstractUser happy
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
    
class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # write_only=True ensures we NEVER accidentally send a password back in a response
    password = serializers.CharField(write_only=True)