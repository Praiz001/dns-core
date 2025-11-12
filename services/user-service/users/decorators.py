"""
Custom decorators
"""

import functools
import logging
from datetime import timedelta

from django.utils import timezone

from .models import IdempotencyKey
from .response_utils import ApiResponse

logger = logging.getLogger(__name__)


def idempotent_request(expiry_hours=24):
    """
    Decorator to make an endpoint idempotent using request_id header
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            request_id = request.META.get("HTTP_X_REQUEST_ID")

            if not request_id:
                # No request ID provided, proceed normally
                return view_func(self, request, *args, **kwargs)

            # Check if this request has been processed before
            try:
                idempotency_key = IdempotencyKey.objects.get(request_id=request_id)

                # Check if expired
                if idempotency_key.is_expired():
                    # Expired, delete and reprocess
                    idempotency_key.delete()
                else:
                    # Return cached response
                    logger.info(
                        f"Returning cached response for request_id: {request_id}", extra={"request_id": request_id}
                    )
                    return ApiResponse.success(
                        data=idempotency_key.response_data,
                        message="Cached response (idempotent request)",
                        status_code=idempotency_key.status_code,
                    )
            except IdempotencyKey.DoesNotExist:
                pass

            # Process the request
            response = view_func(self, request, *args, **kwargs)

            # Store the response for future identical requests
            if response.status_code < 400:  # Only cache successful responses
                expires_at = timezone.now() + timedelta(hours=expiry_hours)

                IdempotencyKey.objects.create(
                    request_id=request_id,
                    endpoint=request.path,
                    response_data=response.data.get("data"),
                    status_code=response.status_code,
                    expires_at=expires_at,
                )

                logger.info(f"Stored idempotency key for request_id: {request_id}", extra={"request_id": request_id})

            return response

        return wrapper

    return decorator
