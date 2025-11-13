"""Push Notification Service"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pybreaker import CircuitBreaker
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.config import settings
from app.providers.base import IPushProvider, PushMessage
from app.models.push_delivery import PushDelivery
from app.schemas.push import NotificationMessage
from app.utils.logger import get_logger
from app.utils.database import get_session

logger = get_logger(__name__)

# Circuit breaker for FCM calls
fcm_breaker = CircuitBreaker(
    fail_max=settings.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=settings.CIRCUIT_BREAKER_TIMEOUT
)


class PushService:
    """Service for processing push notifications"""
    
    def __init__(self, push_provider: IPushProvider):
        self.push_provider = push_provider
        self.user_service_url = settings.USER_SERVICE_URL
        self.template_service_url = settings.TEMPLATE_SERVICE_URL
        self.gateway_url = settings.API_GATEWAY_URL
    
    async def process_notification(self, data: Dict[str, Any]):
        """
        Process push notification
        
        Steps:
        1. Fetch user preferences
        2. Check if push is enabled
        3. Get device token(s)
        4. Render template
        5. Send push notification
        6. Log delivery
        7. Update gateway status
        """
        notification_id = data["notification_id"]
        user_id = data["user_id"]
        
        try:
            logger.info(f"Processing push notification {notification_id} for user {user_id}")
            
            # 1. Fetch user preferences
            preferences = await self._get_user_preferences(user_id)
            
            if not preferences.get("push_enabled", False):
                logger.info(f"Push notifications disabled for user {user_id}")
                await self._update_gateway_status(
                    notification_id,
                    "skipped",
                    "Push notifications disabled for user"
                )
                return
            
            # 2. Get user push token
            push_token = await self._get_user_push_token(user_id)
            
            if not push_token:
                logger.warning(f"No push token found for user {user_id}")
                await self._update_gateway_status(
                    notification_id,
                    "failed",
                    "No push token registered"
                )
                return
            
            # 3. Render template
            template_id = data.get("template_id")
            template_code = data.get("template_code")
            
            if not template_id and not template_code:
                logger.error("No template_id or template_code provided")
                await self._update_gateway_status(
                    notification_id,
                    "failed",
                    "No template provided"
                )
                return
            
            rendered = await self._render_template(
                template_id or template_code,
                data["variables"]
            )
            
            # 4. Send push notification with retry
            push_message = PushMessage(
                device_token=push_token,
                title=rendered.get("title", rendered.get("subject", "Notification")),
                body=rendered.get("body", rendered.get("body_text", "")),
                data=data.get("metadata", {}),
                priority="high" if data.get("priority", 1) == 1 else "normal"
            )
            
            result = await self._send_push_with_retry(push_message)
            
            # 5. Log delivery
            async with get_session() as session:
                delivery = PushDelivery(
                    notification_id=UUID(notification_id),
                    user_id=UUID(user_id),
                    device_token=push_token,
                    title=push_message.title,
                    body=push_message.body,
                    data=push_message.data,
                    provider=self.push_provider.get_provider_name(),
                    status="sent" if result.success else "failed",
                    provider_message_id=result.message_id,
                    error_message=result.error,
                    sent_at=datetime.utcnow() if result.success else None
                )
                session.add(delivery)
                await session.commit()
            
            # 6. Update gateway status
            if result.success:
                logger.info(f"Push notification sent successfully: {notification_id}")
                await self._update_gateway_status(
                    notification_id,
                    "sent",
                    None
                )
            else:
                logger.error(f"Push notification failed: {notification_id} - {result.error}")
                await self._update_gateway_status(
                    notification_id,
                    "failed",
                    result.error
                )
            
        except Exception as e:
            logger.error(f"Error processing notification {notification_id}: {str(e)}", exc_info=True)
            await self._update_gateway_status(
                notification_id,
                "failed",
                str(e)
            )
            raise
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Fetch user preferences from User Service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_service_url}/api/v1/users/{user_id}/preferences",
                    timeout=5.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Error fetching user preferences: {str(e)}")
            raise
    
    async def _get_user_push_token(self, user_id: str) -> Optional[str]:
        """Fetch user push token from User Service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_service_url}/api/v1/users/{user_id}/push-token",
                    timeout=5.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("data", {}).get("token")
        except httpx.HTTPError as e:
            logger.error(f"Error fetching push token: {str(e)}")
            return None
    
    async def _render_template(self, template_identifier: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render template via Template Service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.template_service_url}/api/v1/templates/render",
                    json={
                        "template_id": template_identifier,
                        "variables": variables
                    },
                    timeout=5.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Error rendering template: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT
        )
    )
    async def _send_push_with_retry(self, push_message: PushMessage):
        """Send push notification with retry and circuit breaker"""
        return await fcm_breaker.call_async(
            self.push_provider.send,
            push_message
        )
    
    async def _update_gateway_status(
        self,
        notification_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update notification status in Gateway"""
        try:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{self.gateway_url}/internal/notifications/{notification_id}",
                    json={
                        "channel": "push",
                        "status": status,
                        "error_message": error_message,
                        "sent_at": datetime.utcnow().isoformat() if status == "sent" else None
                    },
                    timeout=5.0
                )
                logger.info(f"Updated gateway status for {notification_id}: {status}")
        except httpx.HTTPError as e:
            logger.error(f"Error updating gateway status: {str(e)}")
            # Don't raise - this is a non-critical operation
