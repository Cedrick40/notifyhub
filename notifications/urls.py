from django.urls import path

from .views import (
    MetricsView,
    NotificationCancelView,
    NotificationDetailView,
    NotificationListCreateView,
    NotificationRequeueView,
)

urlpatterns = [
    path("notifications", NotificationListCreateView.as_view(), name="notification-list-create"),
    path("notifications/<uuid:pk>", NotificationDetailView.as_view(), name="notification-detail"),
    path("notifications/<uuid:pk>/requeue", NotificationRequeueView.as_view(), name="notification-requeue"),
    path("notifications/<uuid:pk>/cancel", NotificationCancelView.as_view(), name="notification-cancel"),
    path("metrics", MetricsView.as_view(), name="metrics"),
]