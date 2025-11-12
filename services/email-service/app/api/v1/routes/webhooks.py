"""
Webhook endpoints for email provider callbacks.

Handles delivery status updates from email providers like SendGrid.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas.webhook import SendGridWebhook, WebhookResponse
from app.schemas.common import APIResponse
from app.services.email_service import EmailService
from app.services.external_api import ExternalAPIClient
from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.db.session import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/webhooks/email", response_model=APIResponse[WebhookResponse])
async def email_webhook(
    events: List[SendGridWebhook],
    db: AsyncSession = Depends(get_db)
):
    """
    Handle email delivery webhooks from SendGrid.
    
    SendGrid sends events like:
    - delivered: Email was successfully delivered
    - bounce: Email bounced
    - dropped: Email was dropped (spam, invalid, etc.)
    - deferred: Email delivery was temporarily deferred
    """
    try:
        logger.info(f"Received {len(events)} webhook events")
        
        # Create service dependencies
        repository = EmailDeliveryRepository(db)
        api_client = ExternalAPIClient()
        email_service = EmailService(repository, api_client)
        
        processed_count = 0
        
        for event in events:
            try:
                # Process webhook
                success = await email_service.handle_webhook(
                    provider_message_id=event.sg_message_id,
                    event=event.event,
                    timestamp=event.timestamp
                )
                
                if success:
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing webhook event: {str(e)}")
                # Continue processing other events
                continue
        
        logger.info(f"Processed {processed_count}/{len(events)} webhook events")
        
        response_data = WebhookResponse(
            received=True,
            processed=processed_count == len(events),
            message=f"Processed {processed_count} out of {len(events)} events"
        )
        
        return APIResponse(
            success=True,
            message="Webhook events received",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.get("/webhooks/email/test")
async def test_webhook():
    """Test endpoint to verify webhook endpoint is accessible."""
    return {
        "message": "Email webhook endpoint is active",
        "service": "email-service"
    }
