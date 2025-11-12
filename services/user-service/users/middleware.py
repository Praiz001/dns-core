"""
Custom middleware
"""

import logging
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(MiddlewareMixin):
    """Middleware to add correlation ID to each request for tracing"""

    def process_request(self, request):
        """Add correlation ID to request"""
        correlation_id = request.META.get("HTTP_X_CORRELATION_ID")

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.correlation_id = correlation_id

        # Add to logger context
        logger.info(f"Request started: {request.method} {request.path}", extra={"correlation_id": correlation_id})

    def process_response(self, request, response):
        """Add correlation ID to response headers"""
        if hasattr(request, "correlation_id"):
            response["X-Correlation-ID"] = request.correlation_id

            logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code}",
                extra={"correlation_id": request.correlation_id},
            )

        return response
