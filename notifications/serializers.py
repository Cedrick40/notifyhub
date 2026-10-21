import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from .models import Notification

REQUIRED_PAYLOAD_KEYS = {
    "email": ["subject", "body"],
    "sms": ["body"],
    "push": ["title", "body"],
}


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "channel", "recipient", "payload", "priority", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_priority(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("Priority must be between 1 and 10.")
        return value

    def validate(self, attrs):
        channel = attrs["channel"]
        recipient = attrs["recipient"]
        payload = attrs["payload"]

        if channel == Notification.Channel.EMAIL:
            try:
                validate_email(recipient)
            except DjangoValidationError:
                raise serializers.ValidationError({"recipient": "Enter a valid email address."})
        elif channel == Notification.Channel.SMS:
            if not re.fullmatch(r"\+?[0-9]{7,15}", recipient):
                raise serializers.ValidationError({"recipient": "Enter a valid phone number."})

        if not isinstance(payload, dict):
            raise serializers.ValidationError({"payload": "Payload must be a JSON object."})
        missing = [k for k in REQUIRED_PAYLOAD_KEYS[channel] if not str(payload.get(k, "")).strip()]
        if missing:
            raise serializers.ValidationError(
                {"payload": f"Missing required fields: {', '.join(missing)}."}
            )
        return attrs