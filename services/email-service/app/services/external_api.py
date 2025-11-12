"""
External API client for communicating with other microservices.

Implements HTTP clients with circuit breakers and retry logic for:
- User Service (user preferences)
- Template Service (template rendering)
- API Gateway (notification status updates)
"""

from typing import Optional, Dict, Any
from uuid import UUID
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config import settings
from app.schemas.email import (
    UserPreferences,
    TemplateRenderRequest,
    TemplateRenderResponse,
    NotificationStatusUpdate
)
from app.utils.logger import get_logger
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError
from app.utils.cache import cache

logger = get_logger(__name__)

# Circuit breakers for each external service
user_service_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAIL_MAX,
    timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
    name="user-service"
)

template_service_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAIL_MAX,
    timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
    name="template-service"
)

gateway_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAIL_MAX,
    timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
    name="api-gateway"
)


class ExternalAPIClient:
    """Client for external service communication."""
    
    def __init__(self):
        self.user_service_url = settings.USER_SERVICE_URL
        self.template_service_url = settings.TEMPLATE_SERVICE_URL
        self.api_gateway_url = settings.API_GATEWAY_URL
        self.timeout = settings.HTTP_TIMEOUT
    
    @retry(
        stop=stop_after_attempt(settings.HTTP_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=settings.RETRY_MULTIPLIER,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def get_user_preferences(self, user_id: UUID) -> Optional[UserPreferences]:
        """
        Fetch user notification preferences from User Service.
        
        Uses cache to reduce load on User Service.
        Circuit breaker prevents cascading failures.
        """
        cache_key = f"user_prefs:{user_id}"
        
        # Try cache first
        cached_prefs = await cache.get(cache_key)
        if cached_prefs:
            logger.debug(f"User preferences cache hit for user {user_id}")
            return UserPreferences(**cached_prefs)
        
        try:
            async def fetch_preferences():
                url = f"{self.user_service_url}/api/v1/users/{user_id}/preferences"
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success"):
                        return data.get("data")
                    return None
            
            # Call with circuit breaker
            pref_data = await user_service_breaker.call_async(fetch_preferences)
            
            if pref_data:
                preferences = UserPreferences(**pref_data)
                
                # Cache the result
                await cache.set(cache_key, pref_data, ttl=settings.CACHE_TTL)
                
                logger.info(f"Fetched user preferences for user {user_id}")
                return preferences
            
            return None
            
        except CircuitBreakerError:
            logger.warning(f"User Service circuit breaker open, using defaults for user {user_id}")
            # Return default preferences when circuit is open
            return UserPreferences(email_enabled=True, push_enabled=True)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching user preferences: {e.response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user preferences: {str(e)}")
            return None
    
    @retry(
        stop=stop_after_attempt(settings.HTTP_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=settings.RETRY_MULTIPLIER,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def render_template(
        self,
        template_id: UUID,
        variables: Dict[str, Any]
    ) -> Optional[TemplateRenderResponse]:
        """
        Render email template from Template Service.
        
        Circuit breaker prevents cascading failures.
        """
        try:
            async def render():
                url = f"{self.template_service_url}/api/v1/templates/render"
                payload = {
                    "template_id": str(template_id),
                    "variables": variables
                }
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success"):
                        return data.get("data")
                    return None
            
            # Call with circuit breaker
            rendered_data = await template_service_breaker.call_async(render)
            
            if rendered_data:
                rendered = TemplateRenderResponse(**rendered_data)
                logger.info(f"Rendered template {template_id}")
                return rendered
            
            return None
            
        except CircuitBreakerError:
            logger.error(f"Template Service circuit breaker open for template {template_id}")
            return None
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error rendering template: {e.response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return None
    
    @retry(
        stop=stop_after_attempt(settings.HTTP_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=settings.RETRY_MULTIPLIER,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def update_notification_status(
        self,
        notification_id: UUID,
        status_update: NotificationStatusUpdate
    ) -> bool:
        """
        Update notification status in API Gateway.
        
        Circuit breaker prevents cascading failures.
        """
        try:
            async def update_status():
                url = f"{self.api_gateway_url}/internal/notifications/{notification_id}"
                payload = status_update.model_dump(exclude_none=True)
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.patch(url, json=payload)
                    response.raise_for_status()
                    return True
            
            # Call with circuit breaker
            result = await gateway_breaker.call_async(update_status)
            logger.info(f"Updated notification {notification_id} status to {status_update.status}")
            return result
            
        except CircuitBreakerError:
            logger.warning(f"API Gateway circuit breaker open, status update queued")
            # In production, could queue this for later retry
            return False
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating notification status: {e.response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")
            return False
