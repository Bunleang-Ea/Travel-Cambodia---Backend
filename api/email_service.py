import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when outbound email delivery fails."""


def send_transactional_email(*, subject, message, recipients):
    provider = str(getattr(settings, "EMAIL_PROVIDER", "smtp")).strip().lower()

    if provider == "brevo_api":
        _send_via_brevo_api(subject=subject, message=message, recipients=recipients)
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipients,
    )


def _resolve_brevo_sender():
    sender_email = str(getattr(settings, "BREVO_SENDER_EMAIL", "")).strip()
    sender_name = str(getattr(settings, "BREVO_SENDER_NAME", "")).strip()

    if not sender_email:
        parsed_name, parsed_email = parseaddr(getattr(settings, "DEFAULT_FROM_EMAIL", ""))
        sender_email = parsed_email.strip()
        if not sender_name:
            sender_name = parsed_name.strip()

    if not sender_email:
        raise EmailDeliveryError(
            "Brevo sender email is missing. Set DJANGO_BREVO_SENDER_EMAIL "
            "or DJANGO_DEFAULT_FROM_EMAIL."
        )

    sender = {"email": sender_email}
    if sender_name:
        sender["name"] = sender_name
    return sender


def _extract_brevo_error(response):
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        return (
            str(payload.get("message"))
            if payload.get("message")
            else str(payload.get("code") or payload)
        )
    return str(payload)


def _send_via_brevo_api(*, subject, message, recipients):
    api_key = str(getattr(settings, "BREVO_API_KEY", "")).strip()
    if not api_key:
        raise EmailDeliveryError("Brevo API key is missing. Set DJANGO_BREVO_API_KEY.")

    api_url = str(
        getattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
    ).strip()
    timeout = int(getattr(settings, "BREVO_API_TIMEOUT", 20))
    sender = _resolve_brevo_sender()

    payload = {
        "sender": sender,
        "to": [{"email": email} for email in recipients],
        "subject": subject,
        "textContent": message,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException:
        logger.exception("Brevo API request failed")
        raise EmailDeliveryError(
            "Unable to reach Brevo email API right now. Please try again later."
        )

    if response.ok:
        return

    error_detail = _extract_brevo_error(response)
    logger.error(
        "Brevo API send failed (status=%s): %s",
        response.status_code,
        error_detail,
    )

    if response.status_code in (401, 403):
        raise EmailDeliveryError(
            f"Brevo API authentication failed: {error_detail}. "
            "Check DJANGO_BREVO_API_KEY."
        )
    if response.status_code == 402:
        raise EmailDeliveryError(
            "Brevo account is not ready to send (activation/credits required)."
        )
    if response.status_code == 429:
        raise EmailDeliveryError(
            "Brevo rate limit reached. Please wait and try again."
        )
    if response.status_code == 400:
        raise EmailDeliveryError(
            f"Brevo rejected the email request: {error_detail}"
        )

    raise EmailDeliveryError(
        "Brevo email API returned an unexpected error. Please try again later."
    )
