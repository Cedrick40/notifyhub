from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from notifications import views as notification_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/", include("notifications.urls")),
    path("v1/health", notification_views.HealthView.as_view(), name="health"),
    path("health", notification_views.HealthView.as_view(), name="health-root"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]