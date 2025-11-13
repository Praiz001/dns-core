"""
Custom exception handler
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent error responses"""

    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the exception
    logger.error(f"Exception: {exc}", exc_info=True, extra={"context": context})

    if response is not None:
        # Customize the response format
        custom_response = {
            "success": False,
            "message": "An error occurred",
            "error": str(exc),
        }

        # Add field-specific errors if available
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, dict):
                custom_response["data"] = exc.detail
            else:
                custom_response["error"] = str(exc.detail)

        response.data = custom_response
        return response

    # Handle unexpected exceptions
    return Response(
        {
            "success": False,
            "message": "Internal server error",
            "error": str(exc),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
