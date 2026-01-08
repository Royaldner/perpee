"""
SQLModel database models for Perpee.
All models use soft delete (deleted_at) where appropriate.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

# ===========================================
# Enums
# ===========================================


class ProductStatus(str, Enum):
    """Product tracking status."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    NEEDS_ATTENTION = "needs_attention"
    PRICE_UNAVAILABLE = "price_unavailable"
    ARCHIVED = "archived"


class AlertType(str, Enum):
    """Types of price alerts."""

    TARGET_PRICE = "target_price"  # Price <= target AND in stock
    PERCENT_DROP = "percent_drop"  # Price dropped X% AND in stock
    ANY_CHANGE = "any_change"  # Price changed AND in stock
    BACK_IN_STOCK = "back_in_stock"  # in_stock changed false -> true


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ScrapeErrorType(str, Enum):
    """Types of scraping errors."""

    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    PARSE_FAILURE = "parse_failure"
    PRICE_VALIDATION = "price_validation"
    STRUCTURE_CHANGE = "structure_change"
    NOT_FOUND = "not_found"
    ROBOTS_BLOCKED = "robots_blocked"


class ExtractionStrategy(str, Enum):
    """Scraper extraction strategies."""

    JSON_LD = "json_ld"
    CSS_SELECTOR = "css_selector"
    XPATH = "xpath"
    LLM = "llm"


# ===========================================
# Base Model
# ===========================================


class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================
# Store Model
# ===========================================


class Store(SQLModel, table=True):
    """
    Store configuration with CSS selectors.
    Primary key is domain (e.g., 'amazon.ca').
    """

    __tablename__ = "stores"

    domain: str = Field(primary_key=True, max_length=255)
    name: str = Field(max_length=255)
    is_whitelisted: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # CSS/XPath selectors stored as JSON
    selectors: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Rate limiting
    rate_limit_rpm: int = Field(default=10)  # Requests per minute

    # Health tracking
    success_rate: float = Field(default=1.0)  # 0.0 to 1.0
    last_success_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    products: list["Product"] = Relationship(back_populates="store")
    schedules: list["Schedule"] = Relationship(back_populates="store")


# ===========================================
# Canonical Product Model
# ===========================================


class CanonicalProduct(SQLModel, table=True):
    """
    Canonical product for cross-store matching.
    Used to group same products from different stores.
    """

    __tablename__ = "canonical_products"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=500)
    brand: str | None = Field(default=None, max_length=255)
    upc: str | None = Field(default=None, max_length=50, index=True)
    category: str | None = Field(default=None, max_length=255)

    # Soft delete
    deleted_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    products: list["Product"] = Relationship(back_populates="canonical_product")


# ===========================================
# Product Model
# ===========================================


class Product(SQLModel, table=True):
    """
    Tracked product with current price and metadata.
    """

    __tablename__ = "products"

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(max_length=2048, index=True)
    store_domain: str = Field(foreign_key="stores.domain", max_length=255, index=True)

    # Product info
    name: str = Field(max_length=500)
    brand: str | None = Field(default=None, max_length=255)
    upc: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=2048)

    # Pricing
    current_price: float | None = Field(default=None)
    original_price: float | None = Field(default=None)  # MSRP / "Was" price
    currency: str = Field(default="CAD", max_length=3)
    in_stock: bool = Field(default=True)

    # Status tracking
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    consecutive_failures: int = Field(default=0)
    last_checked_at: datetime | None = Field(default=None)

    # Cross-store matching
    canonical_id: int | None = Field(default=None, foreign_key="canonical_products.id")

    # Soft delete
    deleted_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    store: Store | None = Relationship(back_populates="products")
    canonical_product: CanonicalProduct | None = Relationship(back_populates="products")
    price_history: list["PriceHistory"] = Relationship(back_populates="product")
    alerts: list["Alert"] = Relationship(back_populates="product")
    schedules: list["Schedule"] = Relationship(back_populates="product")
    scrape_logs: list["ScrapeLog"] = Relationship(back_populates="product")
    notifications: list["Notification"] = Relationship(back_populates="product")


# ===========================================
# Price History Model
# ===========================================


class PriceHistory(SQLModel, table=True):
    """
    Historical price records for a product.
    """

    __tablename__ = "price_history"

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)

    price: float
    original_price: float | None = Field(default=None)
    in_stock: bool = Field(default=True)

    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    product: Product | None = Relationship(back_populates="price_history")


# ===========================================
# Alert Model
# ===========================================


class Alert(SQLModel, table=True):
    """
    Price alert configuration for a product.
    """

    __tablename__ = "alerts"

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)

    alert_type: AlertType
    target_value: float | None = Field(default=None)  # For target_price or percent_drop
    min_change_threshold: float = Field(default=1.0)  # Min $1 or 1% change to trigger

    is_active: bool = Field(default=True)
    is_triggered: bool = Field(default=False)
    triggered_at: datetime | None = Field(default=None)

    # Soft delete
    deleted_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    product: Product | None = Relationship(back_populates="alerts")
    notifications: list["Notification"] = Relationship(back_populates="alert")


# ===========================================
# Schedule Model
# ===========================================


class Schedule(SQLModel, table=True):
    """
    Monitoring schedule for a product or store.
    """

    __tablename__ = "schedules"

    id: int | None = Field(default=None, primary_key=True)

    # Can be for a specific product or entire store
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    store_domain: str | None = Field(default=None, foreign_key="stores.domain", index=True)

    cron_expression: str = Field(max_length=100)  # e.g., "0 6 * * *"
    is_active: bool = Field(default=True)

    last_run_at: datetime | None = Field(default=None)
    next_run_at: datetime | None = Field(default=None)

    # Soft delete
    deleted_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    product: Product | None = Relationship(back_populates="schedules")
    store: Store | None = Relationship(back_populates="schedules")


# ===========================================
# Scrape Log Model
# ===========================================


class ScrapeLog(SQLModel, table=True):
    """
    Logging for scrape operations (debugging and health tracking).
    """

    __tablename__ = "scrape_logs"

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)

    success: bool
    strategy_used: ExtractionStrategy | None = Field(default=None)

    error_type: ScrapeErrorType | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=1000)

    response_time_ms: int | None = Field(default=None)
    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    product: Product | None = Relationship(back_populates="scrape_logs")


# ===========================================
# Notification Model
# ===========================================


class Notification(SQLModel, table=True):
    """
    Notification delivery tracking.
    """

    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)
    alert_id: int | None = Field(default=None, foreign_key="alerts.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)

    channel: NotificationChannel = Field(default=NotificationChannel.EMAIL)
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)

    # Notification content (stored as JSON)
    payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    sent_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=1000)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    alert: Alert | None = Relationship(back_populates="notifications")
    product: Product | None = Relationship(back_populates="notifications")
