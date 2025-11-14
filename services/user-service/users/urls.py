"""
URL routing for users app
"""

from django.urls import path

from .internal_views import InternalUserPreferenceView
from .views import (
    EmailVerificationView,
    HealthCheckView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TestNotificationPublishView,
    UserPreferenceView,
    UserProfileView,
    UserRegistrationView,
)

app_name = "users"

urlpatterns = [
    # User management
    path("users/", UserRegistrationView.as_view(), name="user-register"),
    path("users/profile/", UserProfileView.as_view(), name="user-profile"),
    path("users/preferences/", UserPreferenceView.as_view(), name="user-preferences"),
    path("users/<uuid:user_id>/preferences/", InternalUserPreferenceView.as_view(), name="internal-user-preferences"),
    # Authentication
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    # path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),  # Removed refresh token endpoint
    path("auth/verify-email/", EmailVerificationView.as_view(), name="auth-verify-email"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("notifications/test/", TestNotificationPublishView.as_view(), name="notifications-test"),
]
