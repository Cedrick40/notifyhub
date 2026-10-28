from rest_framework import permissions

from .models import Client


class IsOperator(permissions.BasePermission):
    message = "Operator role required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "role", None) == Client.Role.OPERATOR:
            return True
        self.message = "Operator role required."
        return False


class IsProducerOrOperator(permissions.BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False))

