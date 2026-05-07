"""
Input Validation & Sanitization Module
Phase A: Input Validation & Sanitization (Weeks 4-6 + 14-16)

This module provides comprehensive validation functions for:
- Email format validation enhancement
- Phone number format validation
- Full name length/character validation
- File upload validation (image size, type for profile pictures)
- OTP/password special character handling
"""

import re
import mimetypes
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


# ============================================================================
# EMAIL VALIDATION
# ============================================================================

def validate_email_format(email):
    """
    Enhanced email format validation with additional security checks.
    - RFC 5321 compliant
    - Blocks suspicious patterns
    - Enforces reasonable length limits
    """
    if not email or not isinstance(email, str):
        raise ValidationError('Email must be a valid string.')
    
    email = email.strip().lower()
    
    # Check length (RFC 5321 max 254 chars)
    if len(email) > 254:
        raise ValidationError('Email address is too long (max 254 characters).')
    
    if len(email) < 5:
        raise ValidationError('Email address is too short.')
    
    # Basic RFC 5322 simplified regex
    email_regex = r'^[a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$'
    
    if not re.match(email_regex, email):
        raise ValidationError('Enter a valid email address.')
    
    # Check for consecutive dots
    if '..' in email:
        raise ValidationError('Email address cannot contain consecutive dots.')
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'^\.', r'\.$',  # starts or ends with dot
        r'^@', r'@$',     # starts or ends with @
        r'test@', r'admin@', r'root@',  # common test patterns
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, email):
            raise ValidationError('Email address format is invalid.')
    
    return email


# ============================================================================
# PHONE NUMBER VALIDATION
# ============================================================================

def validate_phone_number(phone_number):
    """
    Phone number format validation supporting international formats.
    - Validates format: +, digits, spaces, hyphens, parentheses
    - Enforces minimum 7 and maximum 15 digits (E.164 standard)
    - Blocks suspicious patterns
    """
    if not phone_number or not isinstance(phone_number, str):
        raise ValidationError('Phone number must be a valid string.')
    
    phone_number = phone_number.strip()
    
    # Check length
    if len(phone_number) < 7 or len(phone_number) > 20:
        raise ValidationError('Phone number must be between 7 and 20 characters.')
    
    # Extract only digits to count them (E.164: min 7, max 15 digits)
    digits_only = re.sub(r'\D', '', phone_number)
    
    if len(digits_only) < 7:
        raise ValidationError('Phone number must contain at least 7 digits.')
    
    if len(digits_only) > 15:
        raise ValidationError('Phone number must contain at most 15 digits.')
    
    # Allow: +, digits, spaces, hyphens, parentheses, dots
    phone_regex = r'^[\+]?[\d\s\-\(\)\.]+$'
    
    if not re.match(phone_regex, phone_number):
        raise ValidationError('Phone number contains invalid characters.')
    
    # Check for consecutive special characters
    if re.search(r'[\s\-\(\)\.]{2,}', phone_number):
        raise ValidationError('Phone number format is invalid.')
    
    return phone_number


# ============================================================================
# FULL NAME VALIDATION
# ============================================================================

def validate_full_name(full_name):
    """
    Full name length and character validation.
    - Enforces length: minimum 2, maximum 150 characters
    - Allows letters, spaces, hyphens, apostrophes
    - Blocks special characters and numbers
    - Prevents whitespace-only names
    """
    if not full_name or not isinstance(full_name, str):
        raise ValidationError('Full name must be a valid string.')
    
    full_name = full_name.strip()
    
    # Check length
    if len(full_name) < 2:
        raise ValidationError('Full name must be at least 2 characters long.')
    
    if len(full_name) > 150:
        raise ValidationError('Full name must not exceed 150 characters.')
    
    # Check if only whitespace
    if not full_name.replace(' ', '').replace('-', '').replace("'", ''):
        raise ValidationError('Full name must contain at least one letter.')
    
    # Allow: letters (any case), spaces, hyphens, apostrophes, accented characters
    # Using Unicode letter category
    name_regex = r"^[\p{L}\s\-'\.]+$"
    
    # Fallback regex for Python (ASCII + common accents)
    name_regex = r"^[a-zA-ZÀ-ÿ\s\-'\.]+$"
    
    if not re.match(name_regex, full_name):
        raise ValidationError('Full name can only contain letters, spaces, hyphens, apostrophes, and dots.')
    
    # Check for consecutive spaces
    if '  ' in full_name:
        raise ValidationError('Full name cannot contain consecutive spaces.')
    
    # Check for suspicious patterns (multiple consecutive special chars)
    if re.search(r"[\-'\.]{2,}", full_name):
        raise ValidationError('Full name format is invalid.')
    
    return full_name


# ============================================================================
# FILE UPLOAD VALIDATION
# ============================================================================

def validate_profile_picture_file(file_obj):
    """
    Profile picture file upload validation.
    - File size: max 5 MB
    - Allowed types: JPEG, PNG, WebP
    - Validates actual file content (magic bytes)
    """
    if not file_obj:
        raise ValidationError('File is required.')
    
    # Check file size (5 MB limit)
    max_size = 5 * 1024 * 1024  # 5 MB in bytes
    
    if file_obj.size > max_size:
        raise ValidationError('File size must not exceed 5 MB.')
    
    if file_obj.size < 1024:  # At least 1 KB
        raise ValidationError('File size must be at least 1 KB.')
    
    # Check file extension
    allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
    file_extension = file_obj.name.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}.'
        )
    
    # Validate actual file content (magic bytes)
    file_obj.seek(0)
    file_header = file_obj.read(12)
    file_obj.seek(0)
    
    # Magic bytes for supported formats
    magic_bytes = {
        'jpeg': [b'\xff\xd8\xff'],  # JPEG starts with FF D8 FF
        'png': [b'\x89PNG\r\n\x1a\n'],  # PNG signature
        'webp': [b'RIFF', b'WEBP'],  # WebP signature
    }
    
    is_valid = False
    
    if file_extension in ['jpg', 'jpeg']:
        is_valid = any(file_header.startswith(magic) for magic in magic_bytes['jpeg'])
    elif file_extension == 'png':
        is_valid = file_header.startswith(magic_bytes['png'][0])
    elif file_extension == 'webp':
        is_valid = file_header.startswith(magic_bytes['webp'][0]) and b'WEBP' in file_header
    
    if not is_valid:
        raise ValidationError('File content does not match the declared format.')
    
    return file_obj


# ============================================================================
# OTP VALIDATION
# ============================================================================

def validate_otp_format(otp):
    """
    OTP format validation for password reset flow.
    - Must be exactly 6 digits
    - Only numeric characters
    - No leading zeros (optional - for readability)
    """
    if not otp or not isinstance(otp, str):
        raise ValidationError('OTP must be a valid string.')
    
    otp = otp.strip()
    
    # Check length - must be exactly 6
    if len(otp) != 6:
        raise ValidationError('OTP must be exactly 6 digits long.')
    
    # Check if all characters are digits
    if not otp.isdigit():
        raise ValidationError('OTP must contain only numeric digits.')
    
    return otp


# ============================================================================
# PASSWORD SPECIAL CHARACTER VALIDATION
# ============================================================================

def validate_password_special_characters(password):
    """
    Password special character validation.
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character from: !@#$%^&*()_+-=[]{}|;:,.<>?
    
    Note: This is a supplementary validator. Use alongside Django's
    default password validators for comprehensive security.
    """
    if not password or not isinstance(password, str):
        raise ValidationError('Password must be a valid string.')
    
    password = password.strip()
    
    # Check minimum length
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    
    # Check maximum length (prevent DoS)
    if len(password) > 128:
        raise ValidationError('Password must not exceed 128 characters.')
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one digit.')
    
    # Check for at least one special character
    special_chars_pattern = r'[!@#$%^&*()\-_+=\[\]{}|;:,.<>?]'
    if not re.search(special_chars_pattern, password):
        raise ValidationError(
            'Password must contain at least one special character from: '
            '!@#$%^&*()_+-=[]{}|;:,.<>?'
        )
    
    # Only check for EXTREMELY weak patterns - 4+ repeated identical characters
    if re.search(r'(.)\1{3,}', password):  # aaaa, 1111, etc.
        raise ValidationError('Password contains weak patterns (too many consecutive identical characters).')
    
    return password


# ============================================================================
# INPUT SANITIZATION HELPERS
# ============================================================================

def sanitize_string_input(value, field_name='field', max_length=None):
    """
    Sanitize generic string input.
    - Strips whitespace
    - Removes null bytes
    - Enforces max length if specified
    """
    if not isinstance(value, str):
        raise ValidationError(f'{field_name} must be a string.')
    
    value = value.strip()
    
    # Remove null bytes (security measure)
    if '\x00' in value:
        raise ValidationError(f'{field_name} contains invalid characters.')
    
    # Check max length
    if max_length and len(value) > max_length:
        raise ValidationError(f'{field_name} must not exceed {max_length} characters.')
    
    return value


def sanitize_email_input(email):
    """Sanitize email: strip whitespace and lowercase."""
    if not isinstance(email, str):
        raise ValidationError('Email must be a string.')
    
    email = email.strip().lower()
    
    # Remove null bytes
    if '\x00' in email:
        raise ValidationError('Email contains invalid characters.')
    
    return email


def sanitize_phone_input(phone):
    """Sanitize phone: strip whitespace only."""
    if not isinstance(phone, str):
        raise ValidationError('Phone number must be a string.')
    
    phone = phone.strip()
    
    # Remove null bytes
    if '\x00' in phone:
        raise ValidationError('Phone number contains invalid characters.')
    
    return phone


# ============================================================================
# COMBINED VALIDATION FUNCTIONS
# ============================================================================

def validate_user_email(email):
    """Combined email validation: sanitize + validate format."""
    sanitized = sanitize_email_input(email)
    return validate_email_format(sanitized)


def validate_user_phone(phone):
    """Combined phone validation: sanitize + validate format."""
    if phone:  # Phone is optional
        sanitized = sanitize_phone_input(phone)
        return validate_phone_number(sanitized)
    return phone


def validate_user_full_name(full_name):
    """Combined full name validation: sanitize + validate format."""
    if full_name:  # Full name is optional
        sanitized = sanitize_string_input(full_name, 'full_name', max_length=150)
        return validate_full_name(sanitized)
    return full_name
