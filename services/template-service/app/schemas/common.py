from pydantic import BaseModel
from typing import Optional, TypeVar, Generic

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int
    limit: int
    page: int
    total_pages: int
    has_next: bool
    has_previous: bool


class APIResponse(BaseModel, Generic[T]):
    """Standard API response format"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: str
    meta: Optional[PaginationMeta] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "error": None,
                "message": "Operation completed successfully",
                "meta": None
            }
        }