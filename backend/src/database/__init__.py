"""
Database module - SQLModel models and session management.
"""

from src.database.models import (
    Alert,
    AlertType,
    CanonicalProduct,
    ExtractionStrategy,
    Notification,
    NotificationChannel,
    NotificationStatus,
    PriceHistory,
    Product,
    ProductStatus,
    Schedule,
    ScrapeErrorType,
    ScrapeLog,
    Store,
)
from src.database.session import (
    async_session_factory,
    create_db_and_tables,
    engine,
    get_session,
    get_session_dependency,
)

__all__ = [
    # Models
    "Alert",
    "AlertType",
    "CanonicalProduct",
    "ExtractionStrategy",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "PriceHistory",
    "Product",
    "ProductStatus",
    "Schedule",
    "ScrapeErrorType",
    "ScrapeLog",
    "Store",
    # Session
    "async_session_factory",
    "create_db_and_tables",
    "engine",
    "get_session",
    "get_session_dependency",
]
