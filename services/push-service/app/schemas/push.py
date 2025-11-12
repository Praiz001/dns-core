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
