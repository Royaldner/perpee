"""API route modules."""

from src.api.routes.alerts import router as alerts_router
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.api.routes.products import router as products_router
from src.api.routes.schedules import router as schedules_router
from src.api.routes.stores import router as stores_router

__all__ = [
    "alerts_router",
    "chat_router",
    "health_router",
    "products_router",
    "schedules_router",
    "stores_router",
]
