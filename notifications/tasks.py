import logging
import random
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Notification, NotificationAttempt
from .providers import PermanentError, TransientError, deliver

logger = logging.getLogger(__name__)
Status = Notification.Status
Outcome = NotificationAttempt.Outcome


def backoff_seconds(attempt_no: int) -> float:
    """Exponential backoff with full jitter: a random wait below a growing ceiling."""
    ceiling = min(
        settings.NOTIFY_RETRY_CAP_SECONDS,
        settings.NOTIFY_RETRY_BASE_SECONDS * 2 ** attempt_no,
    )
    return max(1.0, random.uniform(0, ceiling))


def claim_notification(notification_id):
    """Atomically take the job. Returns (notification, attempt) or (None, None)."""
    now = timezone.now()
    due = (
        Q(status__in=[Status.QUEUED, Status.RETRYING])
        & (Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
    ) | Q(status=Status.PROCESSING, locked_until__lt=now)  # a dead worker's expired lease

    with transaction.atomic():
        notification = (
            Notification.objects.select_for_update(skip_locked=True)
            .filter(due, pk=notification_id)
            .first()
        )
        if notification is None:
            return None, None
        notification.status = Status.PROCESSING
        notification.attempt_count += 1
        notification.locked_until = now + timedelta(seconds=settings.NOTIFY_LEASE_SECONDS)
        notification.save(update_fields=["status", "attempt_count", "locked_until", "updated_at"])
        attempt = NotificationAttempt.objects.create(
            notification=notification,
            attempt_no=notification.attempt_count,
            started_at=now,
        )
    return notification, attempt


def _finish(notification, attempt, outcome, error, new_status, delay=None):
    now = timezone.now()
    with transaction.atomic():
        attempt.outcome = outcome
        attempt.error_detail = error
        attempt.finished_at = now
        attempt.save(update_fields=["outcome", "error_detail", "finished_at"])

        notification.status = new_status
        notification.last_error = error
        notification.locked_until = None
        notification.next_attempt_at = now + timedelta(seconds=delay) if delay else None
        notification.save(
            update_fields=["status", "last_error", "locked_until", "next_attempt_at", "updated_at"]
        )


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True, max_retries=50)
def send_notification(self, notification_id):
    notification, attempt = claim_notification(notification_id)
    if notification is None:
        return "skipped"  # already handled, not due yet, or another worker holds it

    try:
        deliver(notification)
    except PermanentError as exc:
        _finish(notification, attempt, Outcome.PERMANENT_FAILURE, str(exc), Status.DEAD)
        return "dead"
    except TransientError as exc:
        if notification.attempt_count >= notification.max_attempts:
            _finish(notification, attempt, Outcome.TRANSIENT_FAILURE, str(exc), Status.DEAD)
            return "dead"
        delay = backoff_seconds(notification.attempt_count)
        _finish(notification, attempt, Outcome.TRANSIENT_FAILURE, str(exc), Status.RETRYING, delay)
        raise self.retry(countdown=delay)
    else:
        _finish(notification, attempt, Outcome.SUCCESS, "", Status.SUCCEEDED)
        return "succeeded"


def enqueue_notification(notification_id: str):
    """Hand a job to the queue. The job is already safe in Postgres, so a queue outage must not break the request."""
    try:
        send_notification.delay(notification_id)
    except Exception:
        logger.exception("Could not enqueue %s; the reconciler will recover it", notification_id)