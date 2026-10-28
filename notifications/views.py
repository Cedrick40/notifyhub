from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status, views
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .audit import log_audit
from .models import Client, Notification, NotificationAttempt
from .permissions import IsOperator
from .tasks import enqueue_notification
from .serializers import (
    NotificationCreateSerializer,
    NotificationDetailSerializer,
    NotificationSummarySerializer,
)


def visible_notifications(client):
    """Producers see only their own jobs; operators see everything."""
    queryset = Notification.objects.all()
    if client.role != Client.Role.OPERATOR:
        queryset = queryset.filter(client=client)
    return queryset


class NotificationListCreateView(generics.ListAPIView):
    serializer_class = NotificationSummarySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        queryset = visible_notifications(self.request.user)
        params = self.request.query_params

        status_value = params.get("status")
        if status_value:
            if status_value not in Notification.Status.values:
                raise ValidationError(
                    {"status": f"Must be one of: {', '.join(Notification.Status.values)}."}
                )
            queryset = queryset.filter(status=status_value)

        channel = params.get("channel")
        if channel:
            if channel not in Notification.Channel.values:
                raise ValidationError(
                    {"channel": f"Must be one of: {', '.join(Notification.Channel.values)}."}
                )
            queryset = queryset.filter(channel=channel)

        created_after = params.get("created_after") or params.get("from") or params.get("date_from") or params.get("start_date")
        if created_after:
            try:
                from django.utils.dateparse import parse_datetime, parse_date
                from datetime import datetime, time
                from django.utils import timezone

                dt = parse_datetime(created_after)
                if dt is None:
                    d = parse_date(created_after)
                    if d:
                        dt = datetime.combine(d, time.min)
                if dt:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)
                    queryset = queryset.filter(created_at__gte=dt)
            except Exception:
                pass

        created_before = params.get("created_before") or params.get("to") or params.get("date_to") or params.get("end_date")
        if created_before:
            try:
                from django.utils.dateparse import parse_datetime, parse_date
                from datetime import datetime, time
                from django.utils import timezone

                dt = parse_datetime(created_before)
                if dt is None:
                    d = parse_date(created_before)
                    if d:
                        dt = datetime.combine(d, time.max)
                if dt:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)
                    queryset = queryset.filter(created_at__lte=dt)
            except Exception:
                pass

        date_only = params.get("date")
        if date_only and len(date_only) == 10:
            try:
                from django.utils.dateparse import parse_date
                from datetime import datetime, time
                from django.utils import timezone

                d = parse_date(date_only)
                if d:
                    start = datetime.combine(d, time.min)
                    end = datetime.combine(d, time.max)
                    if timezone.is_naive(start):
                        start = timezone.make_aware(start)
                    if timezone.is_naive(end):
                        end = timezone.make_aware(end)
                    queryset = queryset.filter(created_at__range=(start, end))
            except Exception:
                pass
        return queryset

    @extend_schema(
        summary="List notifications",
        parameters=[
            OpenApiParameter("status", str, enum=Notification.Status.values, required=False),
            OpenApiParameter("channel", str, enum=Notification.Channel.values, required=False),
            OpenApiParameter("created_after", str, required=False, description="ISO datetime/date filter"),
            OpenApiParameter("created_before", str, required=False, description="ISO datetime/date filter"),
            OpenApiParameter("date", str, required=False, description="Date filter YYYY-MM-DD"),
            OpenApiParameter("from", str, required=False, description="Date/datetime filter"),
            OpenApiParameter("to", str, required=False, description="Date/datetime filter"),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Submit a notification",
        request=NotificationCreateSerializer,
        responses={202: NotificationCreateSerializer},
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Unique per logical notification, 1 to 100 characters. Repeating it returns the original job.",
            )
        ],
    )
    def post(self, request):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 100:
            raise ValidationError({"Idempotency-Key": "Required header, 1 to 100 characters."})

        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = request.user

        try:
            with transaction.atomic():
                notification = serializer.save(client=client, idempotency_key=key)
                transaction.on_commit(lambda: enqueue_notification(str(notification.id)))
        except IntegrityError:
            notification = Notification.objects.get(client=client, idempotency_key=key)
            response = Response(
                NotificationCreateSerializer(notification).data,
                status=status.HTTP_202_ACCEPTED,
            )
            response["Idempotent-Replayed"] = "true"
            log_audit("submitted", notification=notification, client=client, request=request, metadata={"idempotent": True})
            return response

        log_audit("submitted", notification=notification, client=client, request=request, metadata={"idempotent": False})
        return Response(
            NotificationCreateSerializer(notification).data,
            status=status.HTTP_202_ACCEPTED,
        )


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationDetailSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return visible_notifications(self.request.user).prefetch_related("attempt_log")

    @extend_schema(summary="Get one notification with its attempt history")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NotificationRequeueView(views.APIView):
    permission_classes = [IsOperator]

    @extend_schema(summary="Requeue a dead notification (operator only)")
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if notification.status != Notification.Status.DEAD:
            raise ValidationError({"status": "Only dead notifications can be requeued."})

        with transaction.atomic():
            notification.status = Notification.Status.QUEUED
            notification.attempt_count = 0
            notification.locked_until = None
            notification.next_attempt_at = None
            notification.last_error = ""
            notification.save(
                update_fields=[
                    "status",
                    "attempt_count",
                    "locked_until",
                    "next_attempt_at",
                    "last_error",
                    "updated_at",
                ]
            )
            transaction.on_commit(lambda n=notification: enqueue_notification(str(n.id)))

        log_audit("requeued", notification=notification, client=request.user, request=request)
        return Response(
            {"id": str(notification.id), "status": notification.status},
            status=status.HTTP_200_OK,
        )


class NotificationCancelView(views.APIView):
    permission_classes = [IsOperator]

    @extend_schema(summary="Cancel a notification (operator only)")
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if notification.status in [Notification.Status.SUCCEEDED, Notification.Status.CANCELLED]:
            raise ValidationError({"status": "Notification cannot be cancelled in its current state."})

        with transaction.atomic():
            notification.status = Notification.Status.CANCELLED
            notification.locked_until = None
            notification.next_attempt_at = None
            notification.save(update_fields=["status", "locked_until", "next_attempt_at", "updated_at"])

        log_audit("cancelled", notification=notification, client=request.user, request=request)
        return Response(
            {"id": str(notification.id), "status": notification.status},
            status=status.HTTP_200_OK,
        )


class MetricsView(views.APIView):
    permission_classes = [IsOperator]

    @extend_schema(summary="Metrics endpoint (operator only)")
    def get(self, request):
        now = timezone.now()
        total = Notification.objects.count()
        by_status = dict(
            Notification.objects.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        queue_depth = Notification.objects.filter(status__in=[Notification.Status.QUEUED, Notification.Status.RETRYING]).count()
        processing = Notification.objects.filter(status=Notification.Status.PROCESSING).count()
        dead = by_status.get(Notification.Status.DEAD, 0)
        succeeded = by_status.get(Notification.Status.SUCCEEDED, 0)
        failed_permanent = NotificationAttempt.objects.filter(outcome=NotificationAttempt.Outcome.PERMANENT_FAILURE).count()
        failed_transient = NotificationAttempt.objects.filter(outcome=NotificationAttempt.Outcome.TRANSIENT_FAILURE).count()
        total_attempts = NotificationAttempt.objects.count()
        retry_count = NotificationAttempt.objects.filter(attempt_no__gt=1).count()

        # rough latency estimate from finished attempts
        from django.db.models import Avg, F
        latency = NotificationAttempt.objects.filter(finished_at__isnull=False).aggregate(
            avg_latency=Avg(F("finished_at") - F("started_at"))
        )
        avg_latency_seconds = None
        if latency.get("avg_latency"):
            try:
                avg_latency_seconds = latency["avg_latency"].total_seconds()
            except Exception:
                avg_latency_seconds = None

        data = {
            "queue_depth": queue_depth,
            "processing": processing,
            "dead": dead,
            "succeeded": succeeded,
            "total_notifications": total,
            "by_status": by_status,
            "outcome_counts": {
                "success": succeeded,
                "transient_failure": failed_transient,
                "permanent_failure": failed_permanent,
                "total_attempts": total_attempts,
            },
            "retry_counts": {
                "retries": retry_count,
                "attempts_gt_1": retry_count,
            },
            "delivery_latency": {
                "avg_seconds": avg_latency_seconds,
            },
            "timestamp": now.isoformat(),
        }
        return Response(data)


class HealthView(views.APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(summary="Health check")
    def get(self, request):
        return Response({"status": "ok"})

