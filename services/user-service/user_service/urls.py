"""
URL Configuration for user_service
"""

from django.contrib import admin
from django.urls import include, path

from rest_framework import permissions

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="User Service API",
        default_version="v1",
        description="User management and authentication service for the Notification System",
        contact=openapi.Contact(email="support@notificationsystem.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("users.urls")),
    path("api-auth/", include("rest_framework.urls")),  # enables session login/logout for Swagger
    path("health/", include("health_check.urls")),
    # API Documentation
    path("api/swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
