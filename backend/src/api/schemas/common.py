"""
Common API schemas used across endpoints.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseSchema):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")


class MessageResponse(BaseSchema):
    """Simple message response."""

    message: str


class PaginationMeta(BaseSchema):
    """Pagination metadata."""

    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    meta: PaginationMeta


class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


class SoftDeleteMixin(BaseSchema):
    """Mixin for soft-deletable models."""

    deleted_at: datetime | None = None


def paginate(
    items: list[Any],
    total: int,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    """
    Create pagination response data.

    Args:
        items: List of items for current page.
        total: Total number of items.
        page: Current page number.
        per_page: Items per page.

    Returns:
        Dict with items and pagination meta.
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
    }
