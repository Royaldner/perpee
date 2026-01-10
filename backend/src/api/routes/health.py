"""
Health check and statistics API routes.
"""

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.api.dependencies import get_db
from src.database.models import (
    Alert,
    Notification,
    NotificationStatus,
    Product,
    ProductStatus,
    Schedule,
    Store,
)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Docker and load balancers.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/stats")
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Dashboard statistics endpoint.
    Returns comprehensive stats about the system.
    """
    # Product stats
    total_products_query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    total_products = (await session.execute(total_products_query)).scalar_one()

    active_products_query = select(func.count(Product.id)).where(
        Product.deleted_at.is_(None),
        Product.status == ProductStatus.ACTIVE,
    )
    active_products = (await session.execute(active_products_query)).scalar_one()

    needs_attention_query = select(func.count(Product.id)).where(
        Product.deleted_at.is_(None),
        Product.status.in_([ProductStatus.NEEDS_ATTENTION, ProductStatus.PRICE_UNAVAILABLE]),
    )
    needs_attention = (await session.execute(needs_attention_query)).scalar_one()

    # Alert stats
    total_alerts_query = select(func.count(Alert.id)).where(Alert.deleted_at.is_(None))
    total_alerts = (await session.execute(total_alerts_query)).scalar_one()

    active_alerts_query = select(func.count(Alert.id)).where(
        Alert.deleted_at.is_(None),
        Alert.is_active.is_(True),
    )
    active_alerts = (await session.execute(active_alerts_query)).scalar_one()

    # Triggered today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    triggered_today_query = select(func.count(Alert.id)).where(
        Alert.is_triggered.is_(True),
        Alert.triggered_at >= today_start,
    )
    triggered_today = (await session.execute(triggered_today_query)).scalar_one()

    # Store stats
    total_stores_query = select(func.count(Store.domain))
    total_stores = (await session.execute(total_stores_query)).scalar_one()

    healthy_stores_query = select(func.count(Store.domain)).where(
        Store.is_active.is_(True),
        Store.success_rate > 0.5,
    )
    healthy_stores = (await session.execute(healthy_stores_query)).scalar_one()

    # Schedule stats
    active_schedules_query = select(func.count(Schedule.id)).where(
        Schedule.deleted_at.is_(None),
        Schedule.is_active.is_(True),
    )
    active_schedules = (await session.execute(active_schedules_query)).scalar_one()

    # Notification stats (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)

    sent_notifications_query = select(func.count(Notification.id)).where(
        Notification.status == NotificationStatus.SENT,
        Notification.created_at >= week_ago,
    )
    sent_notifications = (await session.execute(sent_notifications_query)).scalar_one()

    failed_notifications_query = select(func.count(Notification.id)).where(
        Notification.status == NotificationStatus.FAILED,
        Notification.created_at >= week_ago,
    )
    failed_notifications = (await session.execute(failed_notifications_query)).scalar_one()

    return {
        "products": {
            "total": total_products,
            "active": active_products,
            "needs_attention": needs_attention,
        },
        "alerts": {
            "total": total_alerts,
            "active": active_alerts,
            "triggered_today": triggered_today,
        },
        "stores": {
            "total": total_stores,
            "healthy": healthy_stores,
        },
        "schedules": {
            "active": active_schedules,
        },
        "notifications": {
            "sent_last_7_days": sent_notifications,
            "failed_last_7_days": failed_notifications,
        },
    }
