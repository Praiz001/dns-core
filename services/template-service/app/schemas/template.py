from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class TemplateBase(BaseModel):
    """Base template schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique template name")
    description: Optional[str] = Field(None, description="Template description")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject line")
    body_html: str = Field(..., min_length=1, description="HTML body template")
    body_text: str = Field(..., min_length=1, description="Plain text body template")
    variables: Optional[List[str]] = Field(default=[], description="List of required variables")
    template_type: str = Field(default="email", description="Template type (email, push, sms)")
    language: str = Field(default="en", pattern="^[a-z]{2}$", description="Language code (ISO 639-1)")
    
    @field_validator('template_type')
    @classmethod
    def validate_template_type(cls, v):
        allowed_types = ['email', 'push', 'sms']
        if v not in allowed_types:
            raise ValueError(f'template_type must be one of {allowed_types}')
        return v


class TemplateCreate(TemplateBase):
    """Schema for creating a template"""
    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body_html: Optional[str] = Field(None, min_length=1)
    body_text: Optional[str] = Field(None, min_length=1)
    variables: Optional[List[str]] = None
    template_type: Optional[str] = None
    language: Optional[str] = Field(None, pattern="^[a-z]{2}$")
    is_active: Optional[bool] = None
    
    @field_validator('template_type')
    @classmethod
    def validate_template_type(cls, v):
        if v is not None:
            allowed_types = ['email', 'push', 'sms']
            if v not in allowed_types:
                raise ValueError(f'template_type must be one of {allowed_types}')
        return v


class TemplateResponse(TemplateBase):
    """Schema for template response"""
    id: UUID
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RenderRequest(BaseModel):
    """Schema for template render request"""
    template_id: UUID = Field(..., description="Template ID to render")
    variables: Dict[str, Any] = Field(..., description="Variables to substitute in template")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "variables": {
                    "user_name": "John Doe",
                    "order_id": "ORD-12345",
                    "amount": "$99.99"
                }
            }
        }


class RenderResponse(BaseModel):
    """Schema for rendered template response"""
    subject: str
    body_html: str
    body_text: str
    template_id: UUID
    variables_used: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject": "Order Confirmation #ORD-12345",
                "body_html": "<h1>Hi John Doe!</h1><p>Your order #ORD-12345...</p>",
                "body_text": "Hi John Doe! Your order #ORD-12345...",
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "variables_used": {
                    "user_name": "John Doe",
                    "order_id": "ORD-12345"
                }
            }
        }


class TemplateList(BaseModel):
    """Schema for paginated template list"""
    templates: List[TemplateResponse]
    total: int
    page: int
    limit: int