from django.urls import path

from .views import NotificationCreateView

urlpatterns = [
    path("notifications", NotificationCreateView.as_view(), name="notification-create"),
]