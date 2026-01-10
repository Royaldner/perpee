"""API schemas for request/response validation."""

from src.api.schemas.alerts import (
    AlertCreate,
    AlertListItem,
    AlertResponse,
    AlertUpdate,
    AlertWithProduct,
)
from src.api.schemas.chat import (
    ChatMessage,
    MessageType,
    WebSocketMessage,
    create_error_message,
    create_response_message,
    create_thinking_message,
    create_tool_call_message,
    create_tool_result_message,
    create_welcome_message,
)
from src.api.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    paginate,
)
from src.api.schemas.products import (
    PriceHistoryItem,
    ProductCreate,
    ProductListItem,
    ProductPriceHistory,
    ProductResponse,
    ProductStats,
    ProductUpdate,
    ProductWithAlerts,
)
from src.api.schemas.schedules import (
    ScheduleCreate,
    ScheduleListItem,
    ScheduleResponse,
    ScheduleUpdate,
    ScheduleWithDetails,
)
from src.api.schemas.stores import (
    StoreHealth,
    StoreListItem,
    StoreResponse,
    StoreStats,
    SupportedStoresResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "paginate",
    # Products
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListItem",
    "ProductWithAlerts",
    "ProductPriceHistory",
    "PriceHistoryItem",
    "ProductStats",
    # Alerts
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertListItem",
    "AlertWithProduct",
    # Schedules
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleListItem",
    "ScheduleWithDetails",
    # Stores
    "StoreResponse",
    "StoreListItem",
    "StoreHealth",
    "StoreStats",
    "SupportedStoresResponse",
    # Chat
    "ChatMessage",
    "MessageType",
    "WebSocketMessage",
    "create_welcome_message",
    "create_thinking_message",
    "create_tool_call_message",
    "create_tool_result_message",
    "create_response_message",
    "create_error_message",
]
