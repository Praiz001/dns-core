"""
Webhook Pydantic schemas.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime


class SendGridWebhook(BaseModel):
    """SendGrid webhook event schema."""
    email: EmailStr
    event: str
    timestamp: int
    sg_message_id: str
    sg_event_id: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    response: Optional[str] = None
    
    class Config:
        extra = "allow"


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    received: bool
    processed: bool
    message: str
