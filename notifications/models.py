import uuid
from django.db import models


class Client(models.Model):
    """Someone allowed to call our API (a producer service, or an operator)."""

    class Role(models.TextChoices):
        PRODUCER = "producer"
        OPERATOR = "operator"

    name = models.CharField(max_length=100, unique=True)
    api_key_hash = models.CharField(max_length=64, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PRODUCER)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return self.name


class Notification(models.Model):
    """A durable record of intent: 'this message must be attempted'."""

    class Status(models.TextChoices):
        QUEUED = "queued"
        PROCESSING = "processing"
        RETRYING = "retrying"
        SUCCEEDED = "succeeded"
        DEAD = "dead"
        CANCELLED = "cancelled"

    class Channel(models.TextChoices):
        EMAIL = "email"
        SMS = "sms"
        PUSH = "push"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="notifications")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    recipient = models.CharField(max_length=255)
    payload = models.JSONField()
    priority = models.PositiveSmallIntegerField(default=5)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    idempotency_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "idempotency_key"],
                name="uniq_client_idempotency_key",
            )
        ]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self):
        return f"{self.id} [{self.status}]"


class NotificationAttempt(models.Model):
    """One row per delivery try. This is our evidence trail."""

    class Outcome(models.TextChoices):
        SUCCESS = "success"
        TRANSIENT_FAILURE = "transient_failure"
        PERMANENT_FAILURE = "permanent_failure"

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="attempt_log"
    )
    attempt_no = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)
    error_detail = models.TextField(blank=True)

    class Meta:
        ordering = ["attempt_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "attempt_no"], name="uniq_notification_attempt_no"
            )
        ]


class AuditLog(models.Model):
    """Structured audit events for state-changing actions."""

    class Action(models.TextChoices):
        SUBMITTED = "submitted"
        ENQUEUED = "enqueued"
        STARTED = "started"
        RETRIED = "retried"
        SUCCEEDED = "succeeded"
        DEAD = "dead"
        REQUEUED = "requeued"
        CANCELLED = "cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    correlation_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notification", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.notification_id} at {self.created_at}"