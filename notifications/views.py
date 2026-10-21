from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationCreateSerializer


class NotificationCreateView(APIView):
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
                # Step 7: transaction.on_commit(lambda: send_notification.delay(str(notification.id)))
        except IntegrityError:
            # The unique constraint fired: this client already used this key.
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