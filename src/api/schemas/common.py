"""
Common API schemas.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class BaseResponse(BaseModel):
    """Base response schema."""

    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    """Error response schema."""

    success: bool = False
    error_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    """Paginated response schema."""

    items: list
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime
