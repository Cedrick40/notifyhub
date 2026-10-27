from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Client, Notification
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
            return Notification.objects.none()  # schema generation has no real user
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
        return queryset

    @extend_schema(
        summary="List notifications",
        parameters=[
            OpenApiParameter("status", str, enum=Notification.Status.values, required=False),
            OpenApiParameter("channel", str, enum=Notification.Channel.values, required=False),
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
            return response

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