"""
Store API schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from src.api.schemas.common import BaseSchema


class StoreBase(BaseSchema):
    """Base store fields."""

    domain: str = Field(..., description="Store domain (primary key)")
    name: str = Field(..., description="Store display name")
    is_whitelisted: bool = Field(..., description="Whether store is pre-configured")
    is_active: bool = Field(..., description="Whether store is active")
    rate_limit_rpm: int = Field(..., description="Rate limit (requests per minute)")
    success_rate: float = Field(..., ge=0, le=1, description="Success rate (0-1)")
    last_success_at: datetime | None = Field(None, description="Last successful scrape")


class StoreResponse(StoreBase):
    """Full store response."""

    selectors: dict[str, Any] | None = Field(
        None,
        description="CSS selectors (hidden for security)",
    )
    created_at: datetime
    updated_at: datetime


class StoreListItem(BaseSchema):
    """Condensed store for list views."""

    domain: str
    name: str
    is_whitelisted: bool
    is_active: bool
    success_rate: float
    product_count: int = Field(0, description="Number of tracked products")


class StoreHealth(BaseSchema):
    """Store health information."""

    domain: str
    name: str
    success_rate: float = Field(..., ge=0, le=1)
    is_healthy: bool = Field(..., description="Whether store is healthy (>50% success)")
    product_count: int = Field(..., description="Number of tracked products")
    failed_products: int = Field(..., description="Products with failures")
    last_success_at: datetime | None = None
    last_failure_reason: str | None = None


class StoreStats(BaseSchema):
    """Store statistics."""

    total: int = Field(..., description="Total stores")
    whitelisted: int = Field(..., description="Pre-configured stores")
    healthy: int = Field(..., description="Healthy stores")
    unhealthy: int = Field(..., description="Unhealthy stores")


class SupportedStoresResponse(BaseSchema):
    """List of supported stores."""

    stores: list[StoreListItem]
    total: int
