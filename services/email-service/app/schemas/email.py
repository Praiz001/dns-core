"""
Email-related Pydantic schemas.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class EmailMessage(BaseModel):
    """Email message data structure."""
    to: EmailStr
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None
    reply_to: Optional[EmailStr] = None
    metadata: Optional[Dict[str, Any]] = None


class QueueMessage(BaseModel):
    """Message from RabbitMQ email queue."""
    notification_id: UUID
    user_id: UUID
    template_id: UUID
    variables: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    request_id: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class UserPreferences(BaseModel):
    """User notification preferences."""
    email_enabled: bool
    push_enabled: bool
    email: Optional[EmailStr] = None


class TemplateRenderRequest(BaseModel):
    """Template rendering request."""
    template_id: UUID
    variables: Dict[str, Any]


class TemplateRenderResponse(BaseModel):
    """Template rendering response."""
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None


class EmailDeliveryCreate(BaseModel):
    """Schema for creating email delivery record."""
    notification_id: UUID
    user_id: UUID
    recipient_email: EmailStr
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    provider: str
    metadata: Optional[Dict[str, Any]] = None


class EmailDeliveryResponse(BaseModel):
    """Email delivery response schema."""
    id: UUID
    notification_id: UUID
    user_id: UUID
    recipient_email: str
    subject: str
    status: str
    provider: str
    attempt_count: int
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationStatusUpdate(BaseModel):
    """Schema for updating notification status in API Gateway."""
    channel: str = "email"
    status: str
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
