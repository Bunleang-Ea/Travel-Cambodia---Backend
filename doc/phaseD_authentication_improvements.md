# Phase D: Authentication Improvements (Weeks 7-10)

## Overview
This phase focuses on implementing advanced authentication security features to enhance user account protection, prevent abuse, and provide better session management. These features are critical for production deployments.

---

## 1. Token Expiration & Refresh Mechanism

### Current State
- Basic token authentication in place via `rest_framework.authtoken`
- No token expiration or refresh flow
- Tokens persist indefinitely

### Requirements
- Access tokens expire after 15 minutes
- Refresh tokens valid for 7 days
- Clients can refresh without re-authenticating
- Revoked tokens must be invalidated immediately

### Implementation

#### 1.1 Install Dependencies
```bash
pip install djangorestframework-simplejwt==5.3.2
```

#### 1.2 Update Settings (core/settings.py)
```python
from datetime import timedelta

INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',  # Fallback
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
}
```

#### 1.3 Add Models (accounts/models.py)
```python
from rest_framework_simplejwt.tokens import Token

class TokenBlacklist(models.Model):
    """Track blacklisted tokens for revocation"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blacklisted_tokens'
    )
    token = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(
        max_length=50,
        choices=[
            ('logout', 'User Logout'),
            ('password_change', 'Password Changed'),
            ('suspicious', 'Suspicious Activity'),
        ]
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'blacklisted_at']),
        ]

    def __str__(self):
        return f'Blacklisted token for {self.user.email} ({self.reason})'
```

#### 1.4 Update Views (accounts/views.py)
```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['full_name'] = user.full_name
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class TokenBlacklistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Blacklist token on logout"""
        token = request.auth
        if token:
            TokenBlacklist.objects.create(
                user=request.user,
                token=str(token),
                reason='logout'
            )
        return Response({'detail': 'Successfully logged out.'})
```

#### 1.5 Update URLs (accounts/urls.py)
```python
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView, TokenBlacklistView

urlpatterns = [
    # JWT endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
]
```

---

## 2. Multiple Device Login Management

### Current State
- No tracking of active sessions or devices
- Users can have unlimited concurrent tokens

### Requirements
- Track each device/session separately
- Limit concurrent active sessions per user (e.g., max 3 devices)
- Allow users to view and revoke sessions from specific devices
- Automatic session expiration after inactivity (30 days)

### Implementation

#### 2.1 Add Models (accounts/models.py)
```python
class DeviceSession(models.Model):
    """Track active sessions and devices"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_sessions'
    )
    device_name = models.CharField(max_length=255)  # "iPhone 12", "Chrome Windows"
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('web', 'Web Browser'),
            ('desktop', 'Desktop App'),
        ]
    )
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    token_hash = models.CharField(max_length=255, unique=True)  # Hash of JWT
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.device_name}'
```

#### 2.2 Add Serializers (accounts/serializers.py)
```python
class DeviceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceSession
        fields = ['id', 'device_name', 'device_type', 'ip_address', 'created_at', 'last_activity', 'is_active']
        read_only_fields = ['created_at', 'last_activity']
```

#### 2.3 Add Views (accounts/views.py)
```python
class DeviceSessionListView(ListCreateAPIView):
    """List all active sessions and create new session on login"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceSessionSerializer
    
    def get_queryset(self):
        return DeviceSession.objects.filter(user=self.request.user, is_active=True)

class DeviceSessionDetailView(RetrieveAPIView):
    """Get details of a specific session"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceSessionSerializer
    
    def get_queryset(self):
        return DeviceSession.objects.filter(user=self.request.user)

class RevokeDeviceSessionView(APIView):
    """Revoke a specific device session"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, session_id):
        try:
            session = DeviceSession.objects.get(
                id=session_id,
                user=request.user
            )
            session.is_active = False
            session.save()
            # Add token to blacklist
            TokenBlacklist.objects.create(
                user=request.user,
                token=session.token_hash,
                reason='device_revoke'
            )
            return Response({'detail': 'Device session revoked.'})
        except DeviceSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class RevokeAllOtherSessionsView(APIView):
    """Revoke all other sessions except current"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        current_token = request.auth
        sessions = DeviceSession.objects.filter(
            user=request.user,
            is_active=True
        ).exclude(token_hash=str(current_token))
        
        count = 0
        for session in sessions:
            session.is_active = False
            session.save()
            count += 1
            TokenBlacklist.objects.create(
                user=request.user,
                token=session.token_hash,
                reason='revoke_others'
            )
        
        return Response({
            'detail': f'Revoked {count} other session(s).'
        })
```

#### 2.4 Update URLs
```python
path('sessions/', DeviceSessionListView.as_view(), name='device_sessions'),
path('sessions/<int:session_id>/', DeviceSessionDetailView.as_view(), name='device_session_detail'),
path('sessions/<int:session_id>/revoke/', RevokeDeviceSessionView.as_view(), name='revoke_session'),
path('sessions/revoke-others/', RevokeAllOtherSessionsView.as_view(), name='revoke_all_others'),
```

---

## 3. Login Activity Logging

### Current State
- No login/logout history tracking
- No audit trail for authentication events

### Requirements
- Log every login attempt (success and failure)
- Log logout events
- Log device, IP, timestamp
- Retain logs for 90 days
- API endpoint to view login history

### Implementation

#### 3.1 Add Models (accounts/models.py)
```python
class LoginActivityLog(models.Model):
    """Track login and logout events"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_activities',
        null=True,
        blank=True  # For failed logins
    )
    email = models.EmailField()  # For tracking failed login attempts
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('logout', 'Logout'),
        ]
    )
    failure_reason = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('invalid_email', 'Invalid Email'),
            ('invalid_password', 'Invalid Password'),
            ('account_inactive', 'Account Inactive'),
            ('account_locked', 'Account Locked'),
        ]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]
    
    def __str__(self):
        return f'{self.email} - {self.status} - {self.timestamp}'
```

#### 3.2 Add Serializers (accounts/serializers.py)
```python
class LoginActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginActivityLog
        fields = [
            'id', 'email', 'ip_address', 'device_name',
            'status', 'failure_reason', 'timestamp'
        ]
        read_only_fields = fields
```

#### 3.3 Add Views (accounts/views.py)
```python
class LoginActivityListView(ListAPIView):
    """View personal login history"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoginActivitySerializer
    
    def get_queryset(self):
        # Get logs from last 90 days
        cutoff = timezone.now() - timedelta(days=90)
        return LoginActivityLog.objects.filter(
            user=self.request.user,
            timestamp__gte=cutoff
        )

class AdminLoginActivityListView(ListAPIView):
    """Admin view of all login activities"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = LoginActivitySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user', 'status', 'email']
    ordering_fields = ['timestamp']
    
    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=90)
        return LoginActivityLog.objects.filter(timestamp__gte=cutoff)
```

#### 3.4 Update Login Views
```python
def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_device_name(user_agent):
    """Parse user-agent to get device name"""
    # Simple parsing - use user_agents library for production
    if 'Mobile' in user_agent:
        return 'Mobile'
    elif 'Tablet' in user_agent:
        return 'Tablet'
    else:
        return 'Desktop'

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_name = get_device_name(user_agent)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            
            # Log successful login
            LoginActivityLog.objects.create(
                user=user,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                device_name=device_name,
                status='success'
            )
            
            # Create device session
            token_hash = hash(str(token))
            DeviceSession.objects.create(
                user=user,
                device_name=device_name,
                device_type='web',  # Detect from user_agent
                user_agent=user_agent,
                ip_address=ip_address,
                token_hash=token_hash
            )
            
            data = UserSerializer(user).data
            data['token'] = token.key
            return Response(data)
        else:
            # Log failed login
            email = request.data.get('email', 'unknown')
            LoginActivityLog.objects.create(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                device_name=device_name,
                status='failed',
                failure_reason='invalid_credentials'
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

#### 3.4 Update URLs
```python
path('activities/login/', LoginActivityListView.as_view(), name='login_activities'),
path('admin/activities/login/', AdminLoginActivityListView.as_view(), name='admin_login_activities'),
```

---

## 4. Suspicious Activity Detection

### Current State
- No rate limiting on login attempts
- No detection of unusual access patterns

### Requirements
- Lock account after N failed login attempts (e.g., 5 in 15 minutes)
- Detect logins from new IP addresses
- Detect logins at unusual times
- Send alerts to user email
- Admin dashboard for suspicious activities
- Progressive rate limiting (increasing delays)

### Implementation

#### 4.1 Add Models (accounts/models.py)
```python
class SuspiciousActivity(models.Model):
    """Track and flag suspicious activities"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suspicious_activities',
        null=True,
        blank=True
    )
    email = models.EmailField()
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('failed_attempts', 'Multiple Failed Login Attempts'),
            ('new_location', 'Login from New Location'),
            ('unusual_time', 'Login at Unusual Time'),
            ('impossible_travel', 'Impossible Travel'),
            ('multiple_ips', 'Multiple IPs Same Device'),
        ]
    )
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True)  # City, Country
    severity = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ]
    )
    is_resolved = models.BooleanField(default=False)
    user_confirmed_safe = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    details = models.JSONField(default=dict)

    class Meta:
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['user', 'is_resolved']),
        ]

    def __str__(self):
        return f'{self.email} - {self.activity_type}'


class FailedLoginAttempt(models.Model):
    """Track failed login attempts for rate limiting"""
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['email', 'timestamp']),
        ]
```

#### 4.2 Add Serializers (accounts/serializers.py)
```python
class SuspiciousActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousActivity
        fields = [
            'id', 'activity_type', 'severity', 'ip_address',
            'location', 'detected_at', 'is_resolved'
        ]
        read_only_fields = ['detected_at']

class ConfirmActivitySafeSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
```

#### 4.3 Add Views (accounts/views.py)
```python
from django.core.mail import send_mail
import hashlib

class SuspiciousActivityListView(ListAPIView):
    """View suspicious activities on user account"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SuspiciousActivitySerializer
    
    def get_queryset(self):
        return SuspiciousActivity.objects.filter(user=self.request.user)

class ConfirmActivitySafeView(APIView):
    """User confirms suspicious activity is safe"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, activity_id):
        try:
            activity = SuspiciousActivity.objects.get(id=activity_id)
            serializer = ConfirmActivitySafeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Verify token (would be sent in email)
            token = serializer.validated_data['token']
            # Validate token logic here
            
            activity.user_confirmed_safe = True
            activity.is_resolved = True
            activity.resolved_at = timezone.now()
            activity.save()
            
            return Response({'detail': 'Activity confirmed as safe.'})
        except SuspiciousActivity.DoesNotExist:
            return Response(
                {'error': 'Activity not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class AdminSuspiciousActivityListView(ListAPIView):
    """Admin view of all suspicious activities"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SuspiciousActivitySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user', 'activity_type', 'severity']
    ordering_fields = ['detected_at']
    
    def get_queryset(self):
        return SuspiciousActivity.objects.all()


class RateLimiter:
    """Handle rate limiting for login attempts"""
    MAX_ATTEMPTS = 5
    TIME_WINDOW_MINUTES = 15
    LOCKOUT_MINUTES = 30
    
    @staticmethod
    def check_rate_limit(email, ip_address):
        """Check if account should be rate limited"""
        cutoff = timezone.now() - timedelta(minutes=RateLimiter.TIME_WINDOW_MINUTES)
        attempts = FailedLoginAttempt.objects.filter(
            email=email,
            timestamp__gte=cutoff
        ).count()
        
        if attempts >= RateLimiter.MAX_ATTEMPTS:
            return False, f"Too many failed attempts. Try again in {RateLimiter.LOCKOUT_MINUTES} minutes."
        
        return True, None
    
    @staticmethod
    def record_failed_attempt(email, ip_address):
        """Record a failed login attempt"""
        FailedLoginAttempt.objects.create(email=email, ip_address=ip_address)
    
    @staticmethod
    def clean_old_attempts():
        """Delete attempts older than lockout window"""
        cutoff = timezone.now() - timedelta(minutes=RateLimiter.LOCKOUT_MINUTES)
        FailedLoginAttempt.objects.filter(timestamp__lt=cutoff).delete()


class DetectSuspiciousActivity:
    """Detect suspicious login patterns"""
    
    @staticmethod
    def check_new_location(user, ip_address):
        """Detect login from new location"""
        recent_ips = LoginActivityLog.objects.filter(
            user=user,
            status='success'
        ).values_list('ip_address', flat=True).distinct()
        
        if ip_address not in recent_ips and recent_ips.exists():
            return True
        return False
    
    @staticmethod
    def check_impossible_travel(user, ip_address):
        """Detect impossible travel between locations"""
        last_login = LoginActivityLog.objects.filter(
            user=user,
            status='success'
        ).latest('timestamp')
        
        if (timezone.now() - last_login.timestamp).total_seconds() < 3600:
            # Less than 1 hour since last login
            if last_login.ip_address != ip_address:
                # Would need geolocation API to verify impossible travel
                return True
        return False
    
    @staticmethod
    def create_alert(user, email, activity_type, ip_address, severity):
        """Create suspicious activity record and send alert"""
        activity = SuspiciousActivity.objects.create(
            user=user,
            email=email,
            activity_type=activity_type,
            ip_address=ip_address,
            severity=severity
        )
        
        # Send email alert
        send_mail(
            subject='Suspicious Activity Detected on Your Account',
            message=f'Activity: {activity_type}\nIP: {ip_address}\n\n'
                   f'If this was you, click the link to confirm. Otherwise, reset your password immediately.',
            from_email=None,
            recipient_list=[email],
        )
        
        return activity
```

#### 4.4 Update Login View with Rate Limiting
```python
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get('email')
        ip_address = get_client_ip(request)
        
        # Check rate limiting
        allowed, message = RateLimiter.check_rate_limit(email, ip_address)
        if not allowed:
            return Response(
                {'error': message},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check for suspicious activities
            if DetectSuspiciousActivity.check_new_location(user, ip_address):
                DetectSuspiciousActivity.create_alert(
                    user=user,
                    email=user.email,
                    activity_type='new_location',
                    ip_address=ip_address,
                    severity='medium'
                )
            
            # Continue with normal login flow...
        else:
            RateLimiter.record_failed_attempt(email, ip_address)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

#### 4.5 Update URLs
```python
path('activities/suspicious/', SuspiciousActivityListView.as_view(), name='suspicious_activities'),
path('activities/suspicious/<int:activity_id>/confirm-safe/', ConfirmActivitySafeView.as_view(), name='confirm_activity_safe'),
path('admin/activities/suspicious/', AdminSuspiciousActivityListView.as_view(), name='admin_suspicious_activities'),
```

---

## 5. Remember-Me Functionality (Optional)

### Current State
- Standard token-based authentication only
- No persistent login option

### Requirements
- Optional "remember me" checkbox on login
- Generate long-lived refresh tokens (30 days) for "remember me"
- Client stores refresh token securely
- Separate validation for remember-me tokens

### Implementation

#### 5.1 Add Models (accounts/models.py)
```python
class RememberMeToken(models.Model):
    """Long-lived tokens for 'remember me' functionality"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='remember_me_tokens'
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    @classmethod
    def create_token(cls, user, ip_address, user_agent, lifetime_days=30):
        """Generate a new remember-me token"""
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=lifetime_days)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def is_valid(self, ip_address=None, user_agent=None):
        """Validate token (optionally check IP/UA consistency)"""
        if not self.is_active or timezone.now() > self.expires_at:
            return False
        # Optionally verify same IP/UA
        return True
```

#### 5.2 Add Serializers (accounts/serializers.py)
```python
class LoginSerializerWithRememberMe(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password.')
        
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid email or password.')
        
        if not user.is_active:
            raise serializers.ValidationError('Account is inactive.')
        
        data['user'] = user
        return data
```

#### 5.3 Add Views (accounts/views.py)
```python
class LoginWithRememberMeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializerWithRememberMe(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        remember_me = serializer.validated_data.get('remember_me', False)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Standard token
        token, _ = Token.objects.get_or_create(user=user)
        
        # Remember-me token if requested
        remember_token = None
        if remember_me:
            rm_token = RememberMeToken.create_token(user, ip_address, user_agent)
            remember_token = rm_token.token
        
        data = UserSerializer(user).data
        data['token'] = token.key
        if remember_token:
            data['remember_token'] = remember_token
        
        return Response(data)

class RefreshWithRememberMeView(APIView):
    """Refresh login using remember-me token"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('remember_token')
        if not token:
            return Response(
                {'error': 'remember_token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rm_token = RememberMeToken.objects.get(token=token)
        except RememberMeToken.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired remember token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not rm_token.is_valid():
            rm_token.is_active = False
            rm_token.save()
            return Response(
                {'error': 'Remember token expired'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = rm_token.user
        token, _ = Token.objects.get_or_create(user=user)
        
        data = UserSerializer(user).data
        data['token'] = token.key
        return Response(data)
```

#### 5.4 Update URLs
```python
path('login-remember/', LoginWithRememberMeView.as_view(), name='login_remember_me'),
path('refresh-remember/', RefreshWithRememberMeView.as_view(), name='refresh_remember_me'),
```

---

## Testing Strategy

### Unit Tests (accounts/tests.py)
```python
class TokenExpirationTests(TestCase):
    def test_access_token_expires(self):
        # Verify token expiration after 15 minutes
        pass
    
    def test_refresh_token_valid(self):
        # Verify refresh token refreshes access token
        pass

class DeviceSessionTests(TestCase):
    def test_create_device_session_on_login(self):
        pass
    
    def test_revoke_device_session(self):
        pass
    
    def test_max_concurrent_sessions(self):
        pass

class SuspiciousActivityTests(TestCase):
    def test_detect_new_location(self):
        pass
    
    def test_rate_limit_failed_attempts(self):
        pass
    
    def test_account_lockout_after_attempts(self):
        pass

class RememberMeTests(TestCase):
    def test_generate_remember_token(self):
        pass
    
    def test_token_expiration(self):
        pass
```

---

## Security Considerations

1. **Token Storage (Client-side)**
   - Access tokens: Store in memory (not localStorage)
   - Refresh tokens: HTTPOnly cookies or secure storage
   - Remember-me tokens: Encrypted persistent storage only

2. **Token Transmission**
   - Always use HTTPS in production
   - Include CSRF protection for form-based submissions
   - Use Authorization header for API requests

3. **Rate Limiting**
   - Implement server-side rate limiting with django-ratelimit
   - Progressive delays (exponential backoff)
   - Captcha after threshold for web

4. **Geolocation**
   - Use GeoIP2 or similar for IP-based location detection
   - Consider privacy implications
   - Allow user whitelisting of locations

5. **Audit Logging**
   - Immutable log records
   - Include context (IP, device, location, timestamp)
   - Regular review and alerts

---

## Deployment Checklist

- [ ] Update `requirements.txt` with new dependencies
- [ ] Create and run migrations for new models
- [ ] Configure JWT settings in production settings
- [ ] Set up email backend for alerts
- [ ] Configure GeoIP database (for location detection)
- [ ] Set up log rotation and archival
- [ ] Test token expiration and refresh flows
- [ ] Test rate limiting and account lockout
- [ ] Test device session management
- [ ] Document API endpoints in Swagger/OpenAPI
- [ ] Test in staging environment
- [ ] Monitor login failures and alerts post-deployment

---

## API Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/accounts/login/` | None | Login with credentials |
| POST | `/api/accounts/token/` | None | Obtain JWT tokens |
| POST | `/api/accounts/token/refresh/` | None | Refresh access token |
| POST | `/api/accounts/logout/` | Required | Logout and blacklist token |
| GET | `/api/accounts/sessions/` | Required | List active sessions |
| POST | `/api/accounts/sessions/<id>/revoke/` | Required | Revoke specific session |
| POST | `/api/accounts/sessions/revoke-others/` | Required | Revoke all other sessions |
| GET | `/api/accounts/activities/login/` | Required | View login history |
| GET | `/api/accounts/activities/suspicious/` | Required | View suspicious activities |
| POST | `/api/accounts/activities/suspicious/<id>/confirm-safe/` | None | Confirm activity is safe |

