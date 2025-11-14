"""Database Models"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class PushDelivery(Base):
    """Push notification delivery record"""
    __tablename__ = "push_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    device_token = Column(String(500), nullable=False)
    
    # Notification content
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    
    # Delivery status
    status = Column(String(20), nullable=False, default="pending")  # pending, sent, failed
    provider = Column(String(50), nullable=False)
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
