from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.mail import send_mail
from django.utils import timezone
import random
from datetime import timedelta
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Place, OTPVerification
# Add LoginSerializer to your existing import list
from .serializers import PlaceSerializer, UserRegistrationSerializer, OTPVerifySerializer, LoginSerializer
from django.contrib.auth import get_user_model
User = get_user_model()

@api_view(['GET'])
def get_all_places(request):
    # 1. Grab all published places from the SQL Database
    places = Place.objects.filter(publishing_status='Published')
    
    # 2. Translate them into JSON using the Serializer we just built
    # many=True is required because we are translating a list of multiple places
    serializer = PlaceSerializer(places, many=True)
    
    # 3. Send the JSON back to the frontend
    return Response(serializer.data)

@api_view(['POST'])
def register_user(request):
    # 1. Pass the incoming React data to our new serializer
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        # 2. Save the user (The serializer automatically hashes the password)
        user = serializer.save()

        # 3. Generate a random 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # 4. Set expiration time to 10 minutes from exactly right now
        expiry_time = timezone.now() + timedelta(minutes=10)

        # 5. Save the OTP to the database, linked to this specific user
        OTPVerification.objects.create(
            user=user,
            otp_code=otp_code,
            expired_at=expiry_time
        )

        # 6. "Send" the Email (This will print in your terminal!)
        send_mail(
            subject="Verify Your Travel Cambodia Account",
            message=f"Welcome {user.first_name}! Your verification code is: {otp_code}. It expires in 10 minutes.",
            from_email="noreply@travelcambodia.com",
            recipient_list=[user.email],
            fail_silently=False,
        )

        # 7. Tell the frontend it was a success!
        return Response({
            "message": "User registered successfully. Please check your email for the OTP.",
            "email": user.email
        }, status=status.HTTP_201_CREATED)

    # If the email is already taken, or data is missing, return a 400 Error
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def verify_otp(request):
    serializer = OTPVerifySerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        
        try:
            # 1. Find the user
            user = User.objects.get(email=email)
            
            # 2. Check if they are already verified
            if user.is_verified:
                return Response({"message": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)
                
            # 3. Find the valid, unused OTP for this user
            # We use .first() because a user might have requested multiple codes; we check the most recent valid one
            valid_otp = OTPVerification.objects.filter(
                user=user,
                otp_code=otp_code,
                is_used=False,
                expired_at__gt=timezone.now() # __gt means "Greater Than" right now
            ).first()
            
            if valid_otp:
                # 4. Success! Mark OTP as used and User as verified
                valid_otp.is_used = True
                valid_otp.save()
                
                user.is_verified = True
                user.save()
                
                return Response({"message": "Account successfully verified!"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_user(request):
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # 1. Django's built-in secure authentication check
        # (Remember: behind the scenes we mapped email to username!)
        user = authenticate(username=email, password=password)

        if user is not None:
            # 2. Check if they actually verified their email
            if not user.is_verified:
                return Response(
                    {"error": "Please verify your email with the OTP sent to you before logging in."}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            # 3. Success! Generate the JWT VIP Wristbands
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Login successful!',
                'email': user.email,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
            
        else:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
            
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)