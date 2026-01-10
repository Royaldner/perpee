"""Notification system for Perpee."""

from src.notifications.channels.email import EmailChannel, EmailResult
from src.notifications.service import (
    AlertEvaluationResult,
    NotificationResult,
    NotificationService,
)
from src.notifications.templates import (
    TemplateRenderer,
    render_back_in_stock,
    render_price_alert,
    render_product_error,
    render_store_flagged,
)

__all__ = [
    # Email channel
    "EmailChannel",
    "EmailResult",
    # Service
    "NotificationService",
    "NotificationResult",
    "AlertEvaluationResult",
    # Templates
    "TemplateRenderer",
    "render_price_alert",
    "render_back_in_stock",
    "render_product_error",
    "render_store_flagged",
]
