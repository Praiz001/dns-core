"""
Standardized API response utilities
"""

from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.response import Response


class ApiResponse:
    """Standardized API response format"""

    @staticmethod
    def success(
        data: Any = None, message: str = "Success", meta: Optional[Dict] = None, status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Return success response"""
        response_data = {
            "success": True,
            "message": message,
            "data": data,
        }

        if meta:
            response_data["meta"] = meta

        return Response(response_data, status=status_code)

    @staticmethod
    def error(
        error: str, message: str = "Error", data: Any = None, status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """Return error response"""
        response_data = {
            "success": False,
            "message": message,
            "error": error,
        }

        if data:
            response_data["data"] = data

        return Response(response_data, status=status_code)

    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully",
    ) -> Response:
        """Return created response"""
        return ApiResponse.success(data=data, message=message, status_code=status.HTTP_201_CREATED)

    @staticmethod
    def no_content(message: str = "Operation successful") -> Response:
        """Return no content response"""
        return ApiResponse.success(message=message, status_code=status.HTTP_204_NO_CONTENT)
