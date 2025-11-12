"""
Django admin configuration
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import IdempotencyKey, User, UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin for user preferences"""

    list_display = ("id", "email", "push", "created_at", "updated_at")
    list_filter = ("email", "push", "created_at")
    search_fields = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom user model"""

    list_display = ("email", "name", "is_active", "is_staff", "email_verified", "created_at")
    list_filter = ("is_active", "is_staff", "is_superuser", "email_verified", "created_at")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("name", "push_token", "preferences")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Email Verification", {"fields": ("email_verified", "email_verification_token")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    """Admin for idempotency keys"""

    list_display = ("request_id", "endpoint", "status_code", "created_at", "expires_at")
    list_filter = ("endpoint", "status_code", "created_at")
    search_fields = ("request_id", "endpoint")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"
