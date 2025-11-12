"""
Common Pydantic schemas for API responses.
"""

from typing import Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool
    message: str
    data: Optional[T] = None
    errors: Optional[list] = None
    meta: Optional[PaginationMeta] = None
    
    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    database: str
    rabbitmq: str
    redis: str
