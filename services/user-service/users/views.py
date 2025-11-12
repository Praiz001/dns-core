"""
Authentication and user management views
"""

import json
import logging
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

import pika
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from .decorators import idempotent_request
from .models import IdempotencyKey, User
from .response_utils import ApiResponse
from .serializers import (
    EmailVerificationSerializer,
    LoginSerializer,
    NotificationTestRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserPreferenceUpdateSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class UserRegistrationView(generics.CreateAPIView):
    """Register a new user"""

    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Create new user account"""
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Generate email verification token
            verification_token = secrets.token_urlsafe(32)
            user.email_verification_token = verification_token
            user.save()

            # TODO: Send verification email via message queue
            logger.info(f"User registered: {user.email}", extra={"user_id": str(user.id)})

            # Generate JWT access token only
            access = AccessToken.for_user(user)
            response_data = {
                "user": UserSerializer(user).data,
                "access_token": str(access),
                "verification_token": verification_token,  # Remove in production
            }
            return ApiResponse.created(data=response_data, message="User registered successfully")

        return ApiResponse.error(
            error=serializer.errors, message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST
        )


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """User login"""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Login successful",
                        "data": {
                            "user": {"user_id": "uuid", "name": "Test User", "email": "test@example.com"},
                            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        },
                    }
                },
            ),
            400: "Invalid input",
            401: "Invalid credentials",
        },
    )
    def post(self, request):
        """Authenticate user and return JWT tokens"""
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return ApiResponse.error(
                error=serializer.errors, message="Invalid input", status_code=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(email=email, password=password)

        if user is None:
            return ApiResponse.error(
                error="Invalid credentials", message="Authentication failed", status_code=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return ApiResponse.error(
                error="Account is disabled", message="Authentication failed", status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Generate access token only
        access = AccessToken.for_user(user)
        logger.info(f"User logged in: {user.email}", extra={"user_id": str(user.id)})
        return ApiResponse.success(
            data={
                "user": UserSerializer(user).data,
                "access_token": str(access),
            },
            message="Login successful",
        )


class UserProfileView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete user profile"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        """Return current user"""
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """Get user profile"""
        user = self.get_object()
        serializer = self.get_serializer(user)

        return ApiResponse.success(data=serializer.data, message="Profile retrieved successfully")

    def update(self, request, *args, **kwargs):
        """Update user profile"""
        user = self.get_object()
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # Invalidate cache
            cache.delete(f"user_preferences:{user.id}")

            logger.info(f"User profile updated: {user.email}", extra={"user_id": str(user.id)})

            return ApiResponse.success(data=UserSerializer(user).data, message="Profile updated successfully")

        return ApiResponse.error(
            error=serializer.errors, message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, *args, **kwargs):
        """Delete user account"""
        user = self.get_object()
        user_email = user.email
        user_id = str(user.id)

        # Soft delete - deactivate account
        user.is_active = False
        user.save()

        # Clear cache
        cache.delete(f"user_preferences:{user_id}")

        logger.info(f"User account deactivated: {user_email}", extra={"user_id": user_id})

        return ApiResponse.success(message="Account deactivated successfully")


class UserPreferenceView(APIView):
    """Update user notification preferences"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user preferences"""
        user = request.user

        # Try cache first
        cache_key = f"user_preferences:{user.id}"
        cached_prefs = cache.get(cache_key)

        if cached_prefs:
            return ApiResponse.success(data=cached_prefs, message="Preferences retrieved from cache")

        # Fetch from database
        if user.preferences:
            from .serializers import UserPreferenceSerializer

            prefs_data = UserPreferenceSerializer(user.preferences).data

            # Cache for 1 hour
            cache.set(cache_key, prefs_data, 3600)

            return ApiResponse.success(data=prefs_data, message="Preferences retrieved successfully")

        return ApiResponse.error(
            error="Preferences not found",
            message="Failed to retrieve preferences",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def patch(self, request):
        """Update user preferences"""
        user = request.user

        if not user.preferences:
            return ApiResponse.error(
                error="Preferences not found",
                message="Failed to update preferences",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserPreferenceUpdateSerializer(user.preferences, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # Invalidate cache
            cache_key = f"user_preferences:{user.id}"
            cache.delete(cache_key)

            logger.info(
                f"User preferences updated: {user.email}",
                extra={"user_id": str(user.id), "preferences": serializer.data},
            )

            return ApiResponse.success(data=serializer.data, message="Preferences updated successfully")

        return ApiResponse.error(
            error=serializer.errors, message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST
        )


@method_decorator(csrf_exempt, name="dispatch")
class EmailVerificationView(APIView):
    """Verify user email"""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailVerificationSerializer,
        responses={200: "Email verified successfully", 400: "Invalid or expired token"},
    )
    def post(self, request):
        """Verify email with token"""
        serializer = EmailVerificationSerializer(data=request.data)

        if not serializer.is_valid():
            return ApiResponse.error(
                error=serializer.errors, message="Invalid token", status_code=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data["token"]

        try:
            user = User.objects.get(email_verification_token=token)

            if user.email_verified:
                return ApiResponse.error(
                    error="Email already verified",
                    message="Verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            user.email_verified = True
            user.email_verification_token = None
            user.save()

            logger.info(f"Email verified: {user.email}", extra={"user_id": str(user.id)})

            return ApiResponse.success(message="Email verified successfully")

        except User.DoesNotExist:
            return ApiResponse.error(
                error="Invalid or expired token", message="Verification failed", status_code=status.HTTP_400_BAD_REQUEST
            )


@method_decorator(csrf_exempt, name="dispatch")
class PasswordResetRequestView(APIView):
    """Request password reset"""

    permission_classes = [AllowAny]

    permission_classes = [AllowAny]

    def post(self, request):
        """Send password reset email"""
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return ApiResponse.error(
                error=serializer.errors, message="Invalid email", status_code=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)

            # Generate reset token
            reset_token = secrets.token_urlsafe(32)

            # Store in cache with 1 hour expiry
            cache.set(f"password_reset:{reset_token}", user.id, 3600)

            # TODO: Send reset email via message queue
            logger.info(f"Password reset requested: {email}", extra={"user_id": str(user.id)})

            return ApiResponse.success(
                data={"reset_token": reset_token}, message="Password reset email sent"  # Remove in production
            )

        except User.DoesNotExist:
            # Don't reveal if user exists
            return ApiResponse.success(message="If the email exists, a reset link has been sent")


@method_decorator(csrf_exempt, name="dispatch")
class PasswordResetConfirmView(APIView):
    """Confirm password reset"""

    permission_classes = [AllowAny]

    def post(self, request):
        """Reset password with token"""
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if not serializer.is_valid():
            return ApiResponse.error(
                error=serializer.errors, message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        # Get user ID from cache
        user_id = cache.get(f"password_reset:{token}")

        if not user_id:
            return ApiResponse.error(
                error="Invalid or expired token",
                message="Password reset failed",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
            user.set_password(password)
            user.save()

            # Delete token from cache
            cache.delete(f"password_reset:{token}")

            logger.info(f"Password reset completed: {user.email}", extra={"user_id": str(user.id)})

            return ApiResponse.success(message="Password reset successfully")

        except User.DoesNotExist:
            return ApiResponse.error(
                error="User not found", message="Password reset failed", status_code=status.HTTP_404_NOT_FOUND
            )


class HealthCheckView(APIView):
    """Health check endpoint"""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return service health status"""
        from django.db import connection

        health_status = {
            "service": "user-service",
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "checks": {},
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"

        # Check cache
        try:
            cache.set("health_check", "ok", 10)
            cache.get("health_check")
            health_status["checks"]["cache"] = "healthy"
        except Exception as e:
            health_status["checks"]["cache"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"

        status_code = (
            status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return ApiResponse.success(data=health_status, message="Health check completed", status_code=status_code)


@method_decorator(csrf_exempt, name="dispatch")
class TestNotificationPublishView(APIView):
    """Publish a test notification message to RabbitMQ"""

    # Make this endpoint public (no authentication required)
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Publish a test notification message to RabbitMQ. If authenticated, uses your user id; if not, provide user_id in the body. In production, this endpoint may be disabled by ALLOW_TEST_NOTIFICATION_ENDPOINT.",
        request_body=NotificationTestRequestSerializer,
        consumes=["application/json"],
        responses={
            200: openapi.Response(
                description="Test notification published successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Test notification published",
                        "data": {
                            "message": "Test notification published",
                            "payload": {
                                "notification_type": "push",
                                "user_id": "uuid",
                                "template_code": "WELCOME_TEST",
                                "request_id": "uuid",
                                "priority": 1,
                            },
                        },
                    }
                },
            ),
            401: "Authentication required",
            500: "Publish failed",
        },
        # Public endpoint: disable auth in Swagger for this operation
        security=[],
    )
    def post(self, request):
        # Respect production toggle: return 404 when disabled
        if not settings.ALLOW_TEST_NOTIFICATION_ENDPOINT:
            return ApiResponse.error(
                error="Not found", message="Endpoint is disabled", status_code=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        # Validate optional request body
        body_serializer = NotificationTestRequestSerializer(data=request.data or {})
        body_serializer.is_valid(raise_exception=True)
        body = body_serializer.validated_data
        config = settings.RABBITMQ_CONFIG

        # Determine effective user_id and default name
        if getattr(user, "is_authenticated", False):
            effective_user_id = str(user.id)
            default_name = getattr(user, "name", None) or getattr(user, "email", None) or "User"
        else:
            provided_user_id = body.get("user_id")
            if not provided_user_id:
                return ApiResponse.error(
                    error="user_id is required when not authenticated",
                    message="Validation failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            effective_user_id = str(provided_user_id)
            default_name = "User"

        # Build message
        message = {
            "notification_type": "push",
            "user_id": effective_user_id,
            "template_code": body.get("template_code", "WELCOME_TEST"),
            "variables": {
                **body.get("variables", {}),
            },
            "request_id": str(uuid.uuid4()),
            "priority": body.get("priority", 1),
            "metadata": {
                "source": "test-endpoint",
                **body.get("metadata", {}),
            },
        }

        # Ensure a name variable exists
        if not message["variables"].get("name"):
            message["variables"]["name"] = default_name

        # Connect and publish
        try:
            credentials = pika.PlainCredentials(config["USER"], config["PASSWORD"])
            import ssl

            ssl_options = None
            if config.get("USE_SSL"):
                ssl_context = ssl.create_default_context()
                ssl_options = pika.SSLOptions(ssl_context)
            parameters = pika.ConnectionParameters(
                host=config["HOST"],
                port=config["PORT"],
                virtual_host=config["VHOST"],
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
                ssl_options=ssl_options,
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=config["QUEUE_PUSH"], durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=config["QUEUE_PUSH"],
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),  # make message persistent
            )
            connection.close()
            logger.info("Published test notification message", extra={"user_id": message.get("user_id")})
            return ApiResponse.success(data={"message": "Test notification published", "payload": message})
        except Exception as e:
            logger.error(f"Failed to publish test notification: {e}", exc_info=True)
            return ApiResponse.error(
                error=str(e), message="Publish failed", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
