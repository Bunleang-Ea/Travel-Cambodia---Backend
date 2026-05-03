"""
XSS (Cross-Site Scripting) prevention utilities.
Sanitizes user input and ensures output encoding.
"""

import html
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
        Ensure output is properly encoded.
        DRF automatically JSON-encodes output, which provides XSS protection.
        This method validates that responses contain safe data.

        Args:
            data: Response data

        Returns:
            Validated data
        """
        if isinstance(data, str):
            return html.escape(data)
        elif isinstance(data, dict):
            return {k: XSSSanitizer.sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [XSSSanitizer.sanitize_output(item) for item in data]
        return data
