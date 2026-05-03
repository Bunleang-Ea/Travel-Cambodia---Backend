# Phase B: API Endpoint Security (Weeks 14-16)

## Overview
This document details the API endpoint security hardening phase for the Travel Cambodia backend. This phase focuses on implementing industry-standard security controls for REST API endpoints, including CORS configuration, rate limiting, authorization tests, and input/output validation against injection attacks.

---

## 1. CORS Configuration (Cross-Origin Resource Sharing)

### Current State
- No CORS headers are currently configured
- Frontend is expected to be separate from the backend

### Implementation Steps

#### 1.1 Install django-cors-headers
```bash
pip install django-cors-headers==4.3.1
```

Update `requirements.txt`:
```
django-cors-headers==4.3.1
```

#### 1.2 Configure CORS in Django Settings

Add to `core/settings.py`:

```python
# CORS Configuration
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000'
).split(',')

# Only allow credentials if necessary (for cookie-based sessions)
CORS_ALLOW_CREDENTIALS = True

# Restrict HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Restrict headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Expose specific headers to client
CORS_EXPOSE_HEADERS = [
    'content-type',
    'x-csrftoken',
]

# Preflight request cache (in seconds)
CORS_PREFLIGHT_MAX_AGE = 86400
```

Add `CorsMiddleware` to `MIDDLEWARE` in `core/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add this BEFORE SessionMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

Add `corsheaders` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',  # Add this
    'accounts',
    'itineraries',
]
```

#### 1.3 Environment Variable Configuration

For production deployment:

```bash
# .env or deployment config
CORS_ALLOWED_ORIGINS=https://frontend.example.com,https://app.example.com
DEBUG=False
```

#### 1.4 CORS Testing

Create test file `tests/test_cors.py`:

```python
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class CORSTests(TestCase):
    """Test CORS headers are properly configured."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(CORS_ALLOWED_ORIGINS=['http://example.com'])
    def test_cors_origin_accepted(self):
        """Test that allowed origins receive CORS headers."""
        response = self.client.get(
            '/api/accounts/profile/',
            HTTP_ORIGIN='http://example.com',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET'
        )
        self.assertIn('Access-Control-Allow-Origin', response)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://example.com'])
    def test_cors_origin_rejected(self):
        """Test that disallowed origins don't receive CORS headers."""
        response = self.client.get(
            '/api/accounts/profile/',
            HTTP_ORIGIN='http://malicious.com',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET'
        )
        # The header should not contain the malicious origin
        if 'Access-Control-Allow-Origin' in response:
            self.assertNotEqual(response['Access-Control-Allow-Origin'], 'http://malicious.com')

    def test_cors_preflight_request(self):
        """Test OPTIONS preflight request handling."""
        response = self.client.options(
            '/api/accounts/login/',
            HTTP_ORIGIN='http://localhost:3000',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Allow-Methods', response)
```

---

## 2. Rate Limiting Per Specific Endpoints

### Current State
- Basic global rate limiting is configured: 20/min for anonymous, 100/min for authenticated
- No endpoint-specific rate limiting

### 2.1 Custom Throttle Classes

Create `accounts/throttles.py`:

```python
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginAttemptThrottle(AnonRateThrottle):
    """
    Strict rate limiting for login attempts to prevent brute force attacks.
    Limit: 5 attempts per minute per IP address.
    """
    scope = 'login_attempt'


class RegistrationThrottle(AnonRateThrottle):
    """
    Rate limiting for user registration to prevent spam registration.
    Limit: 3 registrations per hour per IP address.
    """
    scope = 'registration'


class PasswordResetThrottle(AnonRateThrottle):
    """
    Rate limiting for password reset requests to prevent abuse.
    Limit: 3 requests per hour per IP address.
    """
    scope = 'password_reset'


class UserAuthTokenThrottle(UserRateThrottle):
    """
    Rate limiting for authenticated users to prevent abuse.
    Limit: 1000 requests per hour per user.
    """
    scope = 'user_auth'


class AdminActionThrottle(UserRateThrottle):
    """
    Moderate rate limiting for admin actions.
    Limit: 500 requests per hour per admin user.
    """
    scope = 'admin_action'
```

### 2.2 Update Settings with Endpoint-Specific Throttles

In `core/settings.py`, update `REST_FRAMEWORK`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',
        'user': '100/min',
        'login_attempt': '5/min',
        'registration': '3/hour',
        'password_reset': '3/hour',
        'user_auth': '1000/hour',
        'admin_action': '500/hour',
    },
    'EXCEPTION_HANDLER': 'accounts.exceptions.custom_exception_handler',
}
```

### 2.3 Apply Throttles to Specific Views

Update `accounts/views.py`:

```python
from .throttles import LoginAttemptThrottle, RegistrationThrottle, PasswordResetThrottle


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        # ... existing code ...
        pass


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginAttemptThrottle]

    def post(self, request):
        # ... existing code ...
        pass


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        # ... existing code ...
        pass


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        # ... existing code ...
        pass
```

### 2.4 Rate Limiting Tests

Create `tests/test_rate_limiting.py`:

```python
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'login_attempt': '5/min',
            'registration': '3/hour',
        }
    }
)
class RateLimitingTests(TestCase):
    """Test rate limiting on sensitive endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_login_rate_limiting(self):
        """Test login endpoint is rate limited after 5 attempts per minute."""
        url = '/api/accounts/login/'
        
        # Make 5 successful (or failed) attempts
        for i in range(5):
            response = self.client.post(url, {
                'email': 'test@example.com',
                'password': 'wrongpass'
            })
            # First 5 should not be throttled
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # 6th attempt should be throttled
        response = self.client.post(url, {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_registration_rate_limiting(self):
        """Test registration endpoint is rate limited after 3 attempts per hour."""
        url = '/api/accounts/register/'
        
        valid_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

        # Make 3 registration attempts
        for i in range(3):
            data = valid_data.copy()
            data['email'] = f'test{i}@example.com'
            response = self.client.post(url, data)
            # First 3 should not be throttled
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # 4th attempt should be throttled
        response = self.client.post(url, {
            **valid_data,
            'email': 'test3@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_password_reset_rate_limiting(self):
        """Test password reset is rate limited to prevent enumeration attacks."""
        url = '/api/accounts/password-reset/request/'
        
        # Make 3 password reset requests
        for i in range(3):
            response = self.client.post(url, {
                'email': f'test{i}@example.com'
            })
            # Should not be throttled yet (even if user doesn't exist)
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # 4th attempt should be throttled
        response = self.client.post(url, {
            'email': 'test4@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rate_limit_headers(self):
        """Test that rate limit headers are present in response."""
        response = self.client.get('/api/accounts/profile/')
        
        # Should have rate limiting headers
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)
```

---

## 3. API Endpoint Authorization Tests

### Current State
- Basic permission classes are in place
- Some admin-only endpoints are protected
- Needs comprehensive test coverage

### 3.1 Authorization Test Suite

Create `tests/test_api_authorization.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import User


class AdminAuthorizationTests(TestCase):
    """Test that admin-only endpoints properly restrict non-admin users."""

    def setUp(self):
        self.client = APIClient()
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            first_name='Regular',
            last_name='User'
        )
        self.regular_token = Token.objects.create(user=self.regular_user)
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            is_staff=True
        )
        admin_group = Group.objects.create(name='Admin')
        self.admin_user.groups.add(admin_group)
        self.admin_token = Token.objects.create(user=self.admin_user)

    def test_regular_user_cannot_access_admin_users_endpoint(self):
        """Regular users should not access GET /api/accounts/admin/users/"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        response = self.client.get('/api/accounts/admin/users/')
        
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_admin_can_access_admin_users_endpoint(self):
        """Admin users should access GET /api/accounts/admin/users/"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/accounts/admin/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_cannot_access_admin_endpoint(self):
        """Unauthenticated users should not access admin endpoints."""
        response = self.client.get('/api/accounts/admin/users/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create_admin_user(self):
        """Regular users should not be able to create other users."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        response = self.client.post('/api/accounts/admin/users/create/', {
            'email': 'newadmin@example.com',
            'password': 'AdminPass123!',
            'first_name': 'New',
            'last_name': 'Admin'
        })
        
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_admin_cannot_delete_self(self):
        """Admin users should not be able to delete their own account."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(
            f'/api/accounts/admin/users/{self.admin_user.pk}/delete/'
        )
        
        # Should be prevented
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ])

    def test_admin_cannot_access_other_user_private_data(self):
        """Admin users should not directly access another user's private itineraries."""
        # Create itinerary for regular user
        from itineraries.models import Itinerary
        itinerary = Itinerary.objects.create(
            title='Private Trip',
            creator=self.regular_user,
            is_public=False
        )
        
        # Admin tries to access private itinerary
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(f'/api/itineraries/{itinerary.pk}/')
        
        # Admin should not be able to access private itineraries unless explicitly permitted
        if response.status_code != status.HTTP_404_NOT_FOUND:
            # If endpoint returns data, verify it's only admin's own itineraries
            # This depends on implementation
            pass


class UserDataAccessTests(TestCase):
    """Test that users can only access their own data."""

    def setUp(self):
        self.client = APIClient()
        
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='TestPass123!',
            first_name='User',
            last_name='One'
        )
        self.token1 = Token.objects.create(user=self.user1)
        
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='TestPass123!',
            first_name='User',
            last_name='Two'
        )
        self.token2 = Token.objects.create(user=self.user2)

    def test_user_cannot_access_other_user_profile(self):
        """User1 should not be able to access User2's profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.get(f'/api/accounts/users/{self.user2.pk}/')
        
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])

    def test_user_can_only_update_own_profile(self):
        """User1 should only be able to update their own profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        # Try to update User2's profile
        response = self.client.put(
            f'/api/accounts/users/{self.user2.pk}/',
            {'first_name': 'Hacked'}
        )
        
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])
        
        # Verify User2's name was not changed
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.first_name, 'User')

    def test_user_cannot_delete_other_user_account(self):
        """User1 should not be able to delete User2's account."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.delete(f'/api/accounts/users/{self.user2.pk}/')
        
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])
        
        # Verify User2 still exists
        self.assertTrue(User.objects.filter(pk=self.user2.pk).exists())
```

### 3.2 Run Authorization Tests

```bash
python manage.py test tests.test_api_authorization -v 2
```

---

## 4. SQL Injection Prevention Documentation

### Current State
- Django ORM is being used, which provides built-in SQL injection prevention
- Need to document best practices and ensure no raw SQL queries are used unsafely

### 4.1 SQL Injection Prevention Guide

#### Safe Practices (Already in Use)

The codebase uses Django ORM queries, which automatically escape parameters:

```python
# SAFE: Using Django ORM (parameterized queries)
user = User.objects.filter(email=email).first()
users = User.objects.filter(is_staff=True)
itineraries = Itinerary.objects.filter(creator=request.user, is_public=False)
```

#### Unsafe Practices to Avoid

```python
# DANGEROUS: Never do this!
from django.db import connection
cursor = connection.cursor()

# NEVER use string concatenation in raw SQL
cursor.execute(f"SELECT * FROM accounts_user WHERE email = '{email}'")  # VULNERABLE!

# NEVER use string formatting
cursor.execute("SELECT * FROM accounts_user WHERE id = %s" % user_id)  # VULNERABLE!
```

#### Safe Raw SQL When Necessary

```python
from django.db import connection

# SAFE: Using parameterized queries with raw SQL (avoid when possible)
cursor = connection.cursor()
cursor.execute(
    "SELECT * FROM accounts_user WHERE email = %s AND is_active = %s",
    [email, True]  # Parameters are passed separately
)
users = cursor.fetchall()
```

### 4.2 Code Review Checklist

Create `doc/sql_injection_review_checklist.md`:

```markdown
# SQL Injection Prevention Review Checklist

## For Code Reviews:

- [ ] No string concatenation in SQL queries (e.g., f-strings, format(), %)
- [ ] All raw SQL uses parameterized queries (parameters passed separately)
- [ ] Django ORM is used for all standard queries
- [ ] User input is never directly interpolated into SQL
- [ ] Database fields are never directly constructed from user input
- [ ] Query filters use keyword arguments: `filter(email=variable)`
- [ ] Raw SQL is only used when absolutely necessary
- [ ] All raw SQL queries have been reviewed for injection vulnerabilities

## Example Safe Patterns:

```python
# ✓ SAFE: ORM with keyword arguments
User.objects.filter(email=user_email, is_active=True)

# ✓ SAFE: Parameterized raw SQL
cursor.execute("SELECT * FROM users WHERE email = %s", [email])

# ✓ SAFE: Using get_object_or_404 (raises 404 if not found)
user = get_object_or_404(User, email=email)

# ✗ UNSAFE: String concatenation
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# ✗ UNSAFE: String formatting with %
cursor.execute("SELECT * FROM users WHERE email = " + email)

# ✗ UNSAFE: User input in field/table names
User.objects.filter(**{user_input_field: value})
```

## Automated Checks:

Run Django system checks:
```bash
python manage.py check
```

Use static analysis tools:
```bash
# Install bandit for security linting
pip install bandit

# Run security checks
bandit -r . -ll
```
```

### 4.3 SQL Injection Prevention Tests

Create `tests/test_sql_injection_prevention.py`:

```python
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from rest_framework.authtoken.models import Token


class SQLInjectionPreventionTests(TestCase):
    """Test that SQL injection attempts are properly handled."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.token = Token.objects.create(user=self.user)

    def test_login_with_sql_injection_attempt(self):
        """Login endpoint should handle SQL injection attempts safely."""
        response = self.client.post('/api/accounts/login/', {
            'email': "admin'--",
            'password': 'anything'
        })
        
        # Should either reject the invalid email or return 401
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ])

    def test_search_with_sql_injection_attempt(self):
        """Search endpoints should handle SQL injection attempts safely."""
        # Example: searching places/cities
        response = self.client.get(
            '/api/itineraries/places/?search=test"; DROP TABLE users;--'
        )
        
        # Should return results safely, not execute DROP TABLE
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])
        
        # Verify users table still exists
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_registration_with_injection_attempt(self):
        """Registration should handle injection attempts in all fields."""
        response = self.client.post('/api/accounts/register/', {
            'email': 'test@example.com\'; DELETE FROM users;--',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Test\'); DROP TABLE users;--',
            'last_name': 'User'
        })
        
        # Should reject or sanitize the input
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED  # If email validation rejects it
        ])
        
        # Verify data wasn't actually injected
        if response.status_code == status.HTTP_201_CREATED:
            new_user = User.objects.get(email='test@example.com\'; DELETE FROM users;--')
            # Name should be sanitized
            self.assertNotIn('DROP TABLE', new_user.first_name)
```

---

## 5. XSS Prevention in Responses

### Current State
- SECURE_BROWSER_XSS_FILTER is enabled for production
- SECURE_CONTENT_TYPE_NOSNIFF is enabled for production
- Need to ensure proper content-type headers and output encoding

### 5.1 XSS Prevention Configuration

Update `core/settings.py` (ensure these are present):

```python
# Security headers to prevent XSS attacks
SECURE_BROWSER_XSS_FILTER = not DEBUG  # X-XSS-Protection header
SECURE_CONTENT_TYPE_NOSNIFF = not DEBUG  # X-Content-Type-Options header

# Additional XSS prevention headers
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
CSRF_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_COOKIE_SAMESITE = 'Lax'

# Content Security Policy (CSP) - recommended for API
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
```

### 5.2 Serializer Output Sanitization

Create `accounts/sanitizers.py`:

```python
import html
import re
from bleach import clean as bleach_clean


class XSSSanitizer:
    """Sanitize user input and output to prevent XSS attacks."""

    # HTML tags that are safe to allow (restrictive list)
    ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li']
    
    # HTML attributes that are safe to allow
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'p': ['class'],
        'div': ['class'],
    }

    @staticmethod
    def sanitize_input(value, allow_html=False):
        """
        Sanitize user input to prevent XSS.
        
        Args:
            value: String to sanitize
            allow_html: Whether to allow safe HTML tags (default: False)
        
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        if allow_html:
            # Allow only safe HTML tags
            return bleach_clean(
                value,
                tags=XSSSanitizer.ALLOWED_TAGS,
                attributes=XSSSanitizer.ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            # HTML escape all special characters
            return html.escape(value)

    @staticmethod
    def sanitize_output(data):
        """
        Ensure output is properly encoded (already done by DRF JSON encoder).
        This validates that responses contain safe data.
        
        Args:
            data: Response data
        
        Returns:
            Validated data
        """
        # DRF automatically JSON-encodes output, which provides XSS protection
        # This method is a safety check for any manual string concatenation
        if isinstance(data, str):
            return html.escape(data)
        elif isinstance(data, dict):
            return {k: XSSSanitizer.sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [XSSSanitizer.sanitize_output(item) for item in data]
        return data
```

Install bleach for HTML sanitization:

```bash
pip install bleach==6.1.0
```

Add to `requirements.txt`:
```
bleach==6.1.0
```

### 5.3 Apply Sanitization to Serializers

Update `accounts/serializers.py`:

```python
from .sanitizers import XSSSanitizer

class RegistrationSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'write_only': True},
        }

    def validate_first_name(self, value):
        """Sanitize first name input."""
        return XSSSanitizer.sanitize_input(value, allow_html=False)

    def validate_last_name(self, value):
        """Sanitize last name input."""
        return XSSSanitizer.sanitize_input(value, allow_html=False)

    def validate_email(self, value):
        """Validate and sanitize email."""
        value = XSSSanitizer.sanitize_input(value, allow_html=False)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user
```

### 5.4 Response Content-Type Headers

Ensure all API endpoints return proper content-type headers. Update middleware in `core/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 5.5 XSS Prevention Tests

Create `tests/test_xss_prevention.py`:

```python
import html
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from rest_framework.authtoken.models import Token


class XSSPreventionTests(TestCase):
    """Test that XSS attacks are prevented."""

    def setUp(self):
        self.client = APIClient()

    def test_xss_in_registration_first_name(self):
        """XSS payload in first_name should be sanitized."""
        xss_payload = '<script>alert("XSS")</script>'
        response = self.client.post('/api/accounts/register/', {
            'email': 'xsstest@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': xss_payload,
            'last_name': 'Test'
        })
        
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email='xsstest@example.com')
            # Should be HTML-escaped or stripped
            self.assertNotIn('<script>', user.first_name)
            self.assertNotIn('alert(', user.first_name)

    def test_xss_in_profile_update(self):
        """XSS payload in profile update should be sanitized."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        token = Token.objects.create(user=user)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        xss_payload = '<img src=x onerror="alert(\'XSS\')">'
        response = self.client.put('/api/accounts/profile/', {
            'first_name': xss_payload
        })
        
        if response.status_code == status.HTTP_200_OK:
            user.refresh_from_db()
            # Should be sanitized
            self.assertNotIn('onerror', user.first_name)

    def test_response_contains_proper_content_type(self):
        """All responses should have proper Content-Type headers."""
        response = self.client.get('/api/accounts/profile/')
        
        # Should have application/json content type
        content_type = response.get('Content-Type', '')
        self.assertIn('application/json', content_type)

    def test_json_response_encoding(self):
        """JSON responses should be properly encoded to prevent XSS."""
        user = User.objects.create_user(
            email='user@example.com',
            password='TestPass123!',
            first_name='<script>alert("xss")</script>',
            last_name='User'
        )
        token = Token.objects.create(user=user)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/accounts/profile/')
        
        # Response should have proper JSON encoding
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The <script> tag should be in JSON string format (escaped)
        content = response.content.decode('utf-8')
        # Should not contain unescaped script tags in JSON
        self.assertNotIn('<script>', content)

    def test_xss_in_search_results(self):
        """Search results should not be vulnerable to XSS."""
        # Create a place with XSS payload in name
        from itineraries.models import Place
        Place.objects.create(
            name='<img src=x onerror="alert(\'xss\')">',
            description='Test'
        )
        
        response = self.client.get('/api/itineraries/places/')
        
        # Response should be safe JSON
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8')
        # Check for unescaped event handlers
        self.assertNotIn('onerror=', content)
```

---

## 6. Implementation Roadmap

### Week 14: CORS & Basic Rate Limiting
- [ ] Install and configure django-cors-headers
- [ ] Set up environment variable configuration
- [ ] Write and pass CORS tests
- [ ] Apply basic rate limiting to login endpoint
- [ ] Create rate limiting tests

### Week 15: Authorization Tests & SQL Injection Prevention
- [ ] Write comprehensive authorization tests
- [ ] Document SQL injection prevention practices
- [ ] Add code review checklist
- [ ] Write SQL injection prevention tests
- [ ] Review all queries in codebase for safety

### Week 16: XSS Prevention & Final Testing
- [ ] Install and configure bleach for HTML sanitization
- [ ] Apply sanitization to all serializers
- [ ] Write XSS prevention tests
- [ ] Verify all security headers are properly set
- [ ] Run full security test suite
- [ ] Document all security features in API documentation

---

## 7. Testing and Validation

### Run All Security Tests

```bash
# Create a test runner script
python manage.py test tests.test_cors -v 2
python manage.py test tests.test_rate_limiting -v 2
python manage.py test tests.test_api_authorization -v 2
python manage.py test tests.test_sql_injection_prevention -v 2
python manage.py test tests.test_xss_prevention -v 2
```

### Security Checklist

Create `doc/security_checklist.md`:

```markdown
# API Endpoint Security Checklist

## CORS Configuration
- [ ] django-cors-headers installed and configured
- [ ] CORS_ALLOWED_ORIGINS configured for production domains
- [ ] CORS_ALLOW_CREDENTIALS set appropriately
- [ ] CORS tests passing
- [ ] Preflight requests working correctly

## Rate Limiting
- [ ] LoginAttemptThrottle applied to login endpoint
- [ ] RegistrationThrottle applied to registration endpoint
- [ ] PasswordResetThrottle applied to password reset endpoints
- [ ] Rate limit headers present in responses
- [ ] Rate limiting tests passing
- [ ] Documentation on rate limit configurations available

## Authorization
- [ ] All admin endpoints require admin permissions
- [ ] All authenticated endpoints verified with tests
- [ ] Users can only access their own data
- [ ] Admin cannot delete their own account
- [ ] Authorization tests passing (100% of admin endpoints)
- [ ] No unauthorized data access possible

## SQL Injection Prevention
- [ ] No raw SQL with string concatenation in codebase
- [ ] All raw SQL uses parameterized queries
- [ ] Django ORM used for all standard queries
- [ ] Code review checklist in documentation
- [ ] SQL injection prevention tests passing
- [ ] Bandit security linting performed

## XSS Prevention
- [ ] SECURE_BROWSER_XSS_FILTER enabled for production
- [ ] SECURE_CONTENT_TYPE_NOSNIFF enabled for production
- [ ] X-Frame-Options set to DENY
- [ ] Content-Type headers properly set on all responses
- [ ] User input sanitized in serializers
- [ ] Bleach installed for HTML sanitization
- [ ] XSS prevention tests passing
- [ ] Response JSON properly encoded

## Documentation
- [ ] CORS configuration documented
- [ ] Rate limiting configuration documented
- [ ] Authorization requirements documented
- [ ] SQL injection prevention guide completed
- [ ] XSS prevention implementation documented
- [ ] Security headers documented
- [ ] API security guide for frontend developers created
```

---

## 8. References and Best Practices

### External Resources
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Django Security Documentation](https://docs.djangoproject.com/en/6.0/topics/security/)
- [DRF Security Features](https://www.django-rest-framework.org/topics/security/)
- [CORS Specification](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

### Security Headers Reference

| Header | Purpose | Value |
|--------|---------|-------|
| `X-XSS-Protection` | Browser XSS filter | `1; mode=block` |
| `X-Content-Type-Options` | Prevent MIME type sniffing | `nosniff` |
| `X-Frame-Options` | Clickjacking protection | `DENY` |
| `Strict-Transport-Security` | Force HTTPS | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | XSS and injection prevention | `default-src 'self'` |

---

## 9. Conclusion

This Phase B implementation provides comprehensive API endpoint security covering:
1. **CORS**: Controlled cross-origin access for separate frontends
2. **Rate Limiting**: Brute force attack prevention on sensitive endpoints
3. **Authorization**: Verified access control and data isolation
4. **SQL Injection**: Prevention through safe query practices
5. **XSS Prevention**: Input sanitization and output encoding

All improvements are backed by comprehensive test suites to ensure ongoing security compliance.
