"""
Custom throttle classes for API endpoint rate limiting.
Prevents brute force attacks and abuse of sensitive endpoints.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


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
    Rate limiting for password reset requests to prevent abuse and enumeration attacks.
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
