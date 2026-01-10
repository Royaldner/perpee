"""
Product API schemas.
"""

from datetime import datetime

from pydantic import Field, HttpUrl

from src.api.schemas.common import BaseSchema, TimestampMixin
from src.database.models import ProductStatus


class ProductCreate(BaseSchema):
    """Schema for creating a product via URL."""

    url: HttpUrl = Field(..., description="Product URL to track")


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""

    status: ProductStatus | None = Field(None, description="Product status")
    name: str | None = Field(None, max_length=500, description="Product name")


class ProductBase(BaseSchema):
    """Base product fields."""

    id: int
    url: str
    store_domain: str
    name: str
    brand: str | None = None
    upc: str | None = None
    image_url: str | None = None
    current_price: float | None = None
    original_price: float | None = None
    currency: str = "CAD"
    in_stock: bool = True
    status: ProductStatus
    consecutive_failures: int = 0
    last_checked_at: datetime | None = None
    canonical_id: int | None = None


class ProductResponse(ProductBase, TimestampMixin):
    """Full product response."""

    pass


class ProductListItem(BaseSchema):
    """Condensed product for list views."""

    id: int
    url: str
    store_domain: str
    name: str
    brand: str | None = None
    image_url: str | None = None
    current_price: float | None = None
    original_price: float | None = None
    in_stock: bool
    status: ProductStatus
    last_checked_at: datetime | None = None


class ProductWithAlerts(ProductResponse):
    """Product with its alerts."""

    alerts: list["AlertResponse"] = []


class PriceHistoryItem(BaseSchema):
    """Price history entry."""

    id: int
    price: float
    original_price: float | None = None
    in_stock: bool
    scraped_at: datetime


class ProductPriceHistory(BaseSchema):
    """Product with price history."""

    product: ProductResponse
    history: list[PriceHistoryItem]


class ProductStats(BaseSchema):
    """Product statistics."""

    total: int = Field(..., description="Total products")
    active: int = Field(..., description="Active products")
    paused: int = Field(..., description="Paused products")
    needs_attention: int = Field(..., description="Products needing attention")
    by_store: dict[str, int] = Field(default_factory=dict, description="Products per store")


# Forward reference resolution
from src.api.schemas.alerts import AlertResponse  # noqa: E402

ProductWithAlerts.model_rebuild()
