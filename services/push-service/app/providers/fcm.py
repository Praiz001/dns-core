"""Firebase Cloud Messaging Provider"""
import httpx
from typing import Dict, Any

from app.providers.base import IPushProvider, PushMessage, SendResult
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FCMProvider(IPushProvider):
    """Firebase Cloud Messaging provider"""
    
    def __init__(self):
        self.server_key = settings.FCM_SERVER_KEY
        self.api_url = settings.FCM_API_URL
        
        if not self.server_key:
            logger.warning("FCM_SERVER_KEY not configured")
    
    async def send(self, message: PushMessage) -> SendResult:
        """Send push notification via FCM"""
        if not self.server_key:
            return SendResult(
                success=False,
                provider=self.get_provider_name(),
                error="FCM_SERVER_KEY not configured"
            )
        
        try:
            payload = {
                "to": message.device_token,
                "notification": {
                    "title": message.title,
                    "body": message.body,
                },
                "data": message.data or {},
                "priority": message.priority
            }
            
            # Add optional fields
            if message.image_url:
                payload["notification"]["image"] = message.image_url
            
            if message.click_action:
                payload["notification"]["click_action"] = message.click_action
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"key={self.server_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") == 1:
                        message_id = result.get("results", [{}])[0].get("message_id")
                        logger.info(f"FCM notification sent successfully: {message_id}")
                        return SendResult(
                            success=True,
                            message_id=message_id,
                            provider=self.get_provider_name()
                        )
                    else:
                        error_msg = result.get("results", [{}])[0].get("error", "Unknown error")
                        logger.error(f"FCM send failed: {error_msg}")
                        return SendResult(
                            success=False,
                            provider=self.get_provider_name(),
                            error=f"FCM error: {error_msg}"
                        )
                else:
                    logger.error(f"FCM API returned status {response.status_code}: {response.text}")
                    return SendResult(
                        success=False,
                        provider=self.get_provider_name(),
                        error=f"FCM API error: {response.status_code} - {response.text}"
                    )
        
        except httpx.TimeoutException as e:
            logger.error(f"FCM request timeout: {str(e)}")
            return SendResult(
                success=False,
                provider=self.get_provider_name(),
                error=f"Request timeout: {str(e)}"
            )
        except Exception as e:
            logger.error(f"FCM send exception: {str(e)}")
            return SendResult(
                success=False,
                provider=self.get_provider_name(),
                error=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "fcm"
