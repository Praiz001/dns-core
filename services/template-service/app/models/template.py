from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.models.base import Base


class Template(Base):
    """Template model for storing notification templates"""
    
    __tablename__ = "templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Template content
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)
    
    # Variables metadata
    variables = Column(JSON, nullable=True)  # List of required variables
    
    # Template type (email, push, sms)
    template_type = Column(String(50), nullable=False, default="email")
    
    # Language support
    language = Column(String(10), nullable=False, default="en")
    
    # Version control
    version = Column(Integer, nullable=False, default=1)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Template(id={self.id}, name={self.name}, type={self.template_type})>"