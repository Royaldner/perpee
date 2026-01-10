"""Email template rendering utilities."""

from src.notifications.templates.renderer import (
    TemplateRenderer,
    render_back_in_stock,
    render_price_alert,
    render_product_error,
    render_store_flagged,
)

__all__ = [
    "TemplateRenderer",
    "render_price_alert",
    "render_back_in_stock",
    "render_product_error",
    "render_store_flagged",
]
