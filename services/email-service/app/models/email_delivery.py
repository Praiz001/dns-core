"""
Email Delivery Model

Tracks email delivery attempts and their status.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.db.base import Base, TimestampMixin


class EmailDelivery(Base, TimestampMixin):
    """Email delivery tracking model."""
    
    __tablename__ = "email_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Email details
    recipient_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    
    # Delivery status
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Status values: pending, sent, delivered, failed, bounced
    
    provider = Column(String(50), nullable=False)  # smtp, sendgrid
    provider_message_id = Column(String(255), nullable=True, index=True)
    
    # Retry tracking
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    
    # Timestamps
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    
    # Additional data
    extra_data = Column(JSONB, nullable=True)
    
    def __repr__(self):
        return f"<EmailDelivery(id={self.id}, status={self.status}, recipient={self.recipient_email})>"
    
    def is_deliverable(self) -> bool:
        """Check if email can be retried."""
        return self.attempt_count < self.max_attempts and self.status not in ["delivered", "bounced"]
