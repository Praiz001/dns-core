"""
Internal API views for service-to-service communication
"""

import logging

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import User
from .response_utils import ApiResponse
from .serializers import UserPreferenceSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class InternalUserPreferenceView(APIView):
    """Get user preferences without authentication - for internal service calls only"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, user_id):
        """Get user preferences by user ID"""
        # Try cache first
        cache_key = f"user_preferences:{user_id}"
        cached_prefs = cache.get(cache_key)

        if cached_prefs:
            return ApiResponse.success(data=cached_prefs, message="Preferences retrieved from cache")

        # Fetch from database
        try:
            user = User.objects.get(id=user_id)

            if user.preferences:
                prefs_data = UserPreferenceSerializer(user.preferences).data

                # Cache for 1 hour
                cache.set(cache_key, prefs_data, 3600)

                return ApiResponse.success(data=prefs_data, message="Preferences retrieved successfully")

            return ApiResponse.error(
                error="Preferences not found",
                message="Failed to retrieve preferences",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        except User.DoesNotExist:
            return ApiResponse.error(
                error="User not found", message="User does not exist", status_code=status.HTTP_404_NOT_FOUND
            )
