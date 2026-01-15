"""
Email Service - Main business logic for processing email notifications.

Orchestrates the email sending workflow:
1. Fetch user preferences
2. Check if email is enabled
3. Render email template
4. Send email via provider
5. Update notification status
6. Log delivery
"""

from uuid import UUID
from datetime import datetime
from typing import Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config import settings
from app.schemas.email import (
    QueueMessage,
    EmailDeliveryCreate,
    NotificationStatusUpdate
)
from app.providers.base import IEmailProvider, EmailMessage
from app.providers.smtp import SMTPProvider
from app.providers.sendgrid import SendGridProvider
from app.services.external_api import ExternalAPIClient
from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.models.email_delivery import EmailDelivery
from app.utils.logger import get_logger
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = get_logger(__name__)

# Circuit breaker for email provider
email_provider_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAIL_MAX,
    timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
    name="email-provider"
)


class EmailService:
    """
    Service for processing email notifications.
    
    Implements the main business logic with:
    - User preference checking
    - Template rendering
    - Email sending with retry logic
    - Status tracking
    - Circuit breaker for resilience
    """
    
    def __init__(
        self,
        repository: EmailDeliveryRepository,
        api_client: ExternalAPIClient
    ):
        self.repository = repository
        self.api_client = api_client
        self.email_provider = self._create_email_provider()
    
    def _create_email_provider(self) -> IEmailProvider:
        """Factory method to create email provider based on configuration."""
        if settings.EMAIL_PROVIDER == "sendgrid":
            logger.info("Using SendGrid email provider")
            return SendGridProvider()
        else:
            logger.info("Using SMTP email provider")
            return SMTPProvider()
    
    async def process_email_notification(self, message: QueueMessage) -> bool:
        """
        Process email notification from queue.
        
        Args:
            message: Queue message with notification details
            
        Returns:
            True if processed successfully, False otherwise
        """
        logger.info(f"Processing email notification: {message.notification_id}")
        
        try:
            # Step 1: Fetch user preferences
            preferences = await self.api_client.get_user_preferences(message.user_id)
            
            if not preferences:
                logger.error(f"Failed to fetch preferences for user {message.user_id}")
                await self._update_gateway_status(
                    message.notification_id,
                    "failed",
                    error="User preferences not found"
                )
                return False
            
            # Step 2: Check if email is enabled for user
            if not preferences.email_enabled:
                logger.info(f"Email disabled for user {message.user_id}")
                await self._update_gateway_status(
                    message.notification_id,
                    "skipped",
                    error="Email notifications disabled for user"
                )
                return True  # Successfully processed (skipped)
            
            if not preferences.email:
                logger.error(f"No email address for user {message.user_id}")
                await self._update_gateway_status(
                    message.notification_id,
                    "failed",
                    error="User email address not found"
                )
                return False
            
            # Step 3: Render email template
            rendered = await self.api_client.render_template(
                message.template_id,
                message.variables
            )
            
            if not rendered:
                logger.error(f"Failed to render template {message.template_id}")
                await self._update_gateway_status(
                    message.notification_id,
                    "failed",
                    error="Template rendering failed"
                )
                return False
            
            # Step 4: Create delivery record
            delivery = EmailDelivery(
                notification_id=message.notification_id,
                user_id=message.user_id,
                recipient_email=preferences.email,
                subject=rendered.subject,
                body_html=rendered.body_html,
                body_text=rendered.body_text,
                provider=self.email_provider.get_provider_name(),
                status="pending",
                extra_data=message.metadata
            )
            
            delivery = await self.repository.create(delivery)
            
            # Step 5: Send email with retry logic
            send_result = await self._send_email_with_retry(
                delivery_id=delivery.id,
                recipient_email=preferences.email,
                subject=rendered.subject,
                body_html=rendered.body_html,
                body_text=rendered.body_text
            )
            
            if send_result:
                logger.info(f"Email sent successfully for notification {message.notification_id}")
                return True
            else:
                logger.error(f"Failed to send email for notification {message.notification_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing email notification: {str(e)}", exc_info=True)
            await self._update_gateway_status(
                message.notification_id,
                "failed",
                error=str(e)
            )
            return False
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=settings.RETRY_MULTIPLIER,
            min=settings.RETRY_MIN_WAIT,
            max=settings.RETRY_MAX_WAIT
        ),
        reraise=False
    )
    async def _send_email_with_retry(
        self,
        delivery_id: UUID,
        recipient_email: str,
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str]
    ) -> bool:
        """
        Send email with retry logic and circuit breaker.
        
        Uses tenacity for exponential backoff retry.
        Circuit breaker prevents overwhelming failed email provider.
        """
        try:
            # Increment attempt count
            await self.repository.increment_attempt(delivery_id)
            
            # Create email message
            email_msg = EmailMessage(
                to=recipient_email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=settings.EMAIL_FROM_ADDRESS,
                from_name=settings.EMAIL_FROM_NAME
            )
            
            # Send with circuit breaker
            async def send():
                return await self.email_provider.send(email_msg)
            
            result = await email_provider_breaker.call_async(send)
            
            if result.success:
                # Update delivery status
                await self.repository.update_status(
                    delivery_id,
                    "sent",
                    provider_message_id=result.message_id
                )
                
                # Update gateway status
                await self._update_gateway_status(
                    (await self.repository.get_by_id(delivery_id)).notification_id,
                    "sent",
                    provider_message_id=result.message_id
                )
                
                return True
            else:
                # Update delivery status
                await self.repository.update_status(
                    delivery_id,
                    "failed",
                    error_message=result.error
                )
                
                # This will trigger retry
                raise Exception(f"Email send failed: {result.error}")
                
        except CircuitBreakerError as e:
            logger.error(f"Email provider circuit breaker open: {str(e)}")
            await self.repository.update_status(
                delivery_id,
                "failed",
                error_message="Email provider unavailable (circuit breaker open)"
            )
            return False
            
        except Exception as e:
            logger.error(f"Error sending email (attempt will retry): {str(e)}")
            # tenacity will retry
            raise
    
    async def _update_gateway_status(
        self,
        notification_id: UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update notification status in API Gateway.
        
        Maps internal statuses to task-specified enum values:
        - sent -> delivered
        - failed -> failed
        - pending/skipped -> pending
        """
        # Map internal status to task enum (delivered, pending, failed)
        status_mapping = {
            "sent": "delivered",
            "delivered": "delivered",
            "failed": "failed",
            "pending": "pending",
            "skipped": "pending",
            "bounced": "failed"
        }
        
        gateway_status = status_mapping.get(status, "pending")
        
        status_update = NotificationStatusUpdate(
            channel="email",
            status=gateway_status,
            provider_message_id=provider_message_id,
            sent_at=datetime.utcnow() if gateway_status == "delivered" else None,
            error_message=error
        )
        
        await self.api_client.update_notification_status(
            notification_id,
            status_update
        )
    
    async def handle_webhook(
        self,
        provider_message_id: str,
        event: str,
        timestamp: int
    ) -> bool:
        """
        Handle webhook from email provider (e.g., SendGrid).
        
        Updates delivery status based on provider events.
        """
        try:
            delivery = await self.repository.get_by_provider_message_id(provider_message_id)
            
            if not delivery:
                logger.warning(f"Delivery not found for provider message ID: {provider_message_id}")
                return False
            
            # Map provider events to our statuses
            status_mapping = {
                "delivered": "delivered",
                "bounce": "bounced",
                "dropped": "failed",
                "deferred": "pending"
            }
            
            new_status = status_mapping.get(event, "pending")
            
            await self.repository.update_status(
                delivery.id,
                new_status
            )
            
            # Update gateway
            await self._update_gateway_status(
                delivery.notification_id,
                new_status,
                provider_message_id=provider_message_id
            )
            
            logger.info(f"Webhook processed: {event} for message {provider_message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return False
