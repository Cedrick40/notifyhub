import random
import smtplib
import time

from django.conf import settings
from django.core.mail import EmailMessage


class TransientError(Exception):
    """A temporary failure worth retrying (timeout, provider 5xx)."""


class PermanentError(Exception):
    """A failure that retrying cannot fix (invalid recipient)."""


def _simulate_provider_behaviour():
    time.sleep(random.uniform(0.05, 0.3))  # network latency
    roll = random.random()
    if roll < settings.FAKE_PERMANENT_RATE:
        raise PermanentError("Provider rejected the recipient (simulated)")
    if roll < settings.FAKE_PERMANENT_RATE + settings.FAKE_TRANSIENT_RATE:
        raise TransientError("Provider timed out (simulated)")


def _send_email(notification):
    payload = notification.payload
    message = EmailMessage(
        subject=payload["subject"],
        body=payload["body"],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notification.recipient],
        headers={"X-Notification-Id": str(notification.id)},
    )
    try:
        message.send(fail_silently=False)
    except (smtplib.SMTPException, OSError) as exc:
        raise TransientError(f"SMTP error: {exc}") from exc


def deliver(notification):
    """Attempt one delivery. Raises TransientError or PermanentError on failure."""
    _simulate_provider_behaviour()
    if notification.channel == "email":
        _send_email(notification)
    # sms and push: the simulation above is the entire fake provider