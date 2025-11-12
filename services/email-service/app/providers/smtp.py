"""
SMTP Email Provider Implementation

Sends emails using standard SMTP protocol.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.providers.base import IEmailProvider, EmailMessage, SendResult
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SMTPProvider(IEmailProvider):
    """SMTP email provider implementation."""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
    
    async def send(self, message: EmailMessage) -> SendResult:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = f"{message.from_name or self.from_name} <{message.from_email or self.from_email}>"
            msg['To'] = message.to
            
            if message.reply_to:
                msg['Reply-To'] = message.reply_to
            
            # Add body parts
            if message.body_text:
                text_part = MIMEText(message.body_text, 'plain')
                msg.attach(text_part)
            
            if message.body_html:
                html_part = MIMEText(message.body_html, 'html')
                msg.attach(html_part)
            
            # Connect and send
            logger.info(f"Connecting to SMTP server {self.host}:{self.port}")
            
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port)
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            message_id = msg.get('Message-ID', 'unknown')
            server.quit()
            
            logger.info(f"Email sent successfully via SMTP to {message.to}")
            
            return SendResult(
                success=True,
                message_id=message_id,
                provider="smtp"
            )
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {str(e)}")
            return SendResult(
                success=False,
                provider="smtp",
                error=f"SMTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via SMTP: {str(e)}")
            return SendResult(
                success=False,
                provider="smtp",
                error=f"Unexpected error: {str(e)}"
            )
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "smtp"
