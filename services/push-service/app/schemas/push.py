"""Pydantic Schemas for Push Service"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class NotificationMessage(BaseModel):
    """Message received from RabbitMQ queue"""
    notification_id: UUID
    user_id: UUID
    template_id: Optional[UUID] = None
    template_code: Optional[str] = None
    variables: Dict[str, Any]
    priority: int = 1
    metadata: Optional[Dict[str, Any]] = None


class PushDeliveryCreate(BaseModel):
    """Schema for creating push delivery record"""
    notification_id: UUID
    user_id: UUID
    device_token: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    provider: str
    status: str = "pending"


class PushDeliveryResponse(BaseModel):
    """Schema for push delivery response"""
    id: UUID
    notification_id: UUID
    user_id: UUID
    device_token: str
    title: str
    body: str
    status: str
    provider: str
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str
    timestamp: datetime
    dependencies: Dict[str, str]


class PushNotificationRequest(BaseModel):
    """Request schema for sending push notification"""
    user_id: str = Field(..., description="Target user ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body/message")
    data: Optional[Dict[str, Any]] = Field(None, description="Custom data payload")
    priority: Optional[str] = Field("normal", description="Priority: normal or high")
    badge: Optional[int] = Field(None, description="Badge count for iOS")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "title": "New Message",
                "body": "You have a new message!",
                "data": {"action": "open_chat", "chat_id": "456"},
                "priority": "high",
                "badge": 1
            }
        }


class PushNotificationResponse(BaseModel):
    """Response schema for push notification"""
    message_id: str = Field(..., description="Unique message identifier")
    status: str = Field(..., description="Status: queued, sent, delivered, failed")
    message: str = Field(..., description="Response message")


class DeliveryStatusResponse(BaseModel):
    """Response schema for delivery status"""
    message_id: str
    user_id: str
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    
    class Config:
        from_attributes = True
