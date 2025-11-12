"""
SendGrid Email Provider Implementation

Sends emails using SendGrid API.
"""

import httpx
from typing import Optional

from app.providers.base import IEmailProvider, EmailMessage, SendResult
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SendGridProvider(IEmailProvider):
    """SendGrid email provider implementation."""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        self.api_url = "https://api.sendgrid.com/v3/mail/send"
    
    async def send(self, message: EmailMessage) -> SendResult:
        """Send email via SendGrid API."""
        try:
            # Build SendGrid payload
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": message.to}],
                        "subject": message.subject
                    }
                ],
                "from": {
                    "email": message.from_email or self.from_email,
                    "name": message.from_name or self.from_name
                },
                "content": []
            }
            
            # Add content
            if message.body_text:
                payload["content"].append({
                    "type": "text/plain",
                    "value": message.body_text
                })
            
            if message.body_html:
                payload["content"].append({
                    "type": "text/html",
                    "value": message.body_html
                })
            
            # Add reply-to if provided
            if message.reply_to:
                payload["reply_to"] = {"email": message.reply_to}
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
            
            if response.status_code == 202:
                message_id = response.headers.get('X-Message-Id', 'unknown')
                logger.info(f"Email sent successfully via SendGrid to {message.to}")
                
                return SendResult(
                    success=True,
                    message_id=message_id,
                    provider="sendgrid"
                )
            else:
                error_msg = f"SendGrid API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return SendResult(
                    success=False,
                    provider="sendgrid",
                    error=error_msg
                )
                
        except httpx.TimeoutException as e:
            logger.error(f"SendGrid API timeout: {str(e)}")
            return SendResult(
                success=False,
                provider="sendgrid",
                error=f"Timeout error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via SendGrid: {str(e)}")
            return SendResult(
                success=False,
                provider="sendgrid",
                error=f"Unexpected error: {str(e)}"
            )
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "sendgrid"
