"""
Repository pattern for database CRUD operations.
"""

from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from src.database.models import (
    Alert,
    AlertType,
    CanonicalProduct,
    Notification,
    NotificationStatus,
    PriceHistory,
    Product,
    ProductStatus,
    Schedule,
    ScrapeLog,
    Store,
)

T = TypeVar("T", bound=SQLModel)


# ===========================================
# Generic CRUD Operations
# ===========================================


async def get_by_id(session: AsyncSession, model: type[T], id: int) -> T | None:
    """Get a record by ID."""
    return await session.get(model, id)


async def get_all(
    session: AsyncSession,
    model: type[T],
    *,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> list[T]:
    """Get all records with pagination."""
    query = select(model)

    # Filter out soft-deleted records if model has deleted_at
    if hasattr(model, "deleted_at") and not include_deleted:
        query = query.where(model.deleted_at.is_(None))

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def create(session: AsyncSession, obj: T) -> T:
    """Create a new record."""
    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    return obj


async def update(session: AsyncSession, obj: T, data: dict[str, Any]) -> T:
    """Update a record with given data."""
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.utcnow()

    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    return obj


async def soft_delete(session: AsyncSession, obj: T) -> T:
    """Soft delete a record by setting deleted_at."""
    if hasattr(obj, "deleted_at"):
        obj.deleted_at = datetime.utcnow()
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.utcnow()
        session.add(obj)
        await session.flush()
    return obj


async def hard_delete(session: AsyncSession, obj: T) -> None:
    """Permanently delete a record."""
    await session.delete(obj)
    await session.flush()


# ===========================================
# Store Operations
# ===========================================


async def get_store_by_domain(session: AsyncSession, domain: str) -> Store | None:
    """Get store by domain."""
    return await session.get(Store, domain)


async def get_whitelisted_stores(session: AsyncSession) -> list[Store]:
    """Get all whitelisted stores."""
    query = select(Store).where(Store.is_whitelisted.is_(True), Store.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


async def upsert_store(session: AsyncSession, store: Store) -> Store:
    """Insert or update a store."""
    existing = await get_store_by_domain(session, store.domain)
    if existing:
        for key, value in store.model_dump(exclude={"domain"}).items():
            if value is not None:
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        await session.flush()
        return existing
    else:
        session.add(store)
        await session.flush()
        await session.refresh(store)
        return store


# ===========================================
# Product Operations
# ===========================================


async def get_product_by_url(session: AsyncSession, url: str) -> Product | None:
    """Get product by URL."""
    query = select(Product).where(Product.url == url, Product.deleted_at.is_(None))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_products_by_store(
    session: AsyncSession,
    store_domain: str,
    *,
    status: ProductStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Product]:
    """Get products for a specific store."""
    query = select(Product).where(
        Product.store_domain == store_domain,
        Product.deleted_at.is_(None),
    )

    if status:
        query = query.where(Product.status == status)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_active_products(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Product]:
    """Get all active products for monitoring."""
    query = (
        select(Product)
        .where(
            Product.status == ProductStatus.ACTIVE,
            Product.deleted_at.is_(None),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_products_needing_attention(session: AsyncSession) -> list[Product]:
    """Get products that need user attention."""
    query = select(Product).where(
        Product.status.in_([ProductStatus.NEEDS_ATTENTION, ProductStatus.PRICE_UNAVAILABLE]),
        Product.deleted_at.is_(None),
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def increment_product_failures(session: AsyncSession, product: Product) -> Product:
    """Increment failure count and update status if needed."""
    product.consecutive_failures += 1
    product.updated_at = datetime.utcnow()

    # After 3 consecutive failures, mark as needs_attention
    if product.consecutive_failures >= 3:
        product.status = ProductStatus.NEEDS_ATTENTION

    session.add(product)
    await session.flush()
    return product


async def reset_product_failures(session: AsyncSession, product: Product) -> Product:
    """Reset failure count after successful scrape."""
    product.consecutive_failures = 0
    product.status = ProductStatus.ACTIVE
    product.last_checked_at = datetime.utcnow()
    product.updated_at = datetime.utcnow()

    session.add(product)
    await session.flush()
    return product


# ===========================================
# Price History Operations
# ===========================================


async def add_price_history(
    session: AsyncSession,
    product_id: int,
    price: float,
    original_price: float | None = None,
    in_stock: bool = True,
) -> PriceHistory:
    """Add a price history record."""
    history = PriceHistory(
        product_id=product_id,
        price=price,
        original_price=original_price,
        in_stock=in_stock,
    )
    session.add(history)
    await session.flush()
    await session.refresh(history)
    return history


async def get_price_history(
    session: AsyncSession,
    product_id: int,
    *,
    days: int | None = None,
    limit: int = 100,
) -> list[PriceHistory]:
    """Get price history for a product."""
    query = select(PriceHistory).where(PriceHistory.product_id == product_id)

    if days:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.where(PriceHistory.scraped_at >= cutoff)

    query = query.order_by(PriceHistory.scraped_at.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_latest_price(session: AsyncSession, product_id: int) -> PriceHistory | None:
    """Get the most recent price history record."""
    query = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.scraped_at.desc())
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


# ===========================================
# Alert Operations
# ===========================================


async def get_active_alerts_for_product(session: AsyncSession, product_id: int) -> list[Alert]:
    """Get all active alerts for a product."""
    query = select(Alert).where(
        Alert.product_id == product_id,
        Alert.is_active.is_(True),
        Alert.deleted_at.is_(None),
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_alerts_by_type(
    session: AsyncSession,
    alert_type: AlertType,
    *,
    active_only: bool = True,
) -> list[Alert]:
    """Get alerts by type."""
    query = select(Alert).where(Alert.alert_type == alert_type, Alert.deleted_at.is_(None))

    if active_only:
        query = query.where(Alert.is_active.is_(True))

    result = await session.execute(query)
    return list(result.scalars().all())


async def trigger_alert(session: AsyncSession, alert: Alert) -> Alert:
    """Mark an alert as triggered."""
    alert.is_triggered = True
    alert.triggered_at = datetime.utcnow()
    alert.updated_at = datetime.utcnow()

    session.add(alert)
    await session.flush()
    return alert


# ===========================================
# Schedule Operations
# ===========================================


async def get_active_schedules(session: AsyncSession) -> list[Schedule]:
    """Get all active schedules."""
    query = select(Schedule).where(Schedule.is_active.is_(True), Schedule.deleted_at.is_(None))
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_schedules_for_product(session: AsyncSession, product_id: int) -> list[Schedule]:
    """Get schedules for a specific product."""
    query = select(Schedule).where(
        Schedule.product_id == product_id,
        Schedule.deleted_at.is_(None),
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_schedule_run(
    session: AsyncSession,
    schedule: Schedule,
    next_run_at: datetime,
) -> Schedule:
    """Update schedule after a run."""
    schedule.last_run_at = datetime.utcnow()
    schedule.next_run_at = next_run_at
    schedule.updated_at = datetime.utcnow()

    session.add(schedule)
    await session.flush()
    return schedule


# ===========================================
# Scrape Log Operations
# ===========================================


async def add_scrape_log(session: AsyncSession, log: ScrapeLog) -> ScrapeLog:
    """Add a scrape log entry."""
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


async def get_scrape_logs_for_product(
    session: AsyncSession,
    product_id: int,
    *,
    limit: int = 50,
) -> list[ScrapeLog]:
    """Get recent scrape logs for a product."""
    query = (
        select(ScrapeLog)
        .where(ScrapeLog.product_id == product_id)
        .order_by(ScrapeLog.scraped_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def cleanup_old_scrape_logs(session: AsyncSession, days: int = 30) -> int:
    """Delete scrape logs older than specified days. Returns count deleted."""
    from datetime import timedelta

    from sqlalchemy import delete

    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = delete(ScrapeLog).where(ScrapeLog.scraped_at < cutoff)
    result = await session.execute(stmt)
    return result.rowcount


# ===========================================
# Notification Operations
# ===========================================


async def add_notification(session: AsyncSession, notification: Notification) -> Notification:
    """Add a notification record."""
    session.add(notification)
    await session.flush()
    await session.refresh(notification)
    return notification


async def get_pending_notifications(session: AsyncSession) -> list[Notification]:
    """Get all pending notifications."""
    query = select(Notification).where(Notification.status == NotificationStatus.PENDING)
    result = await session.execute(query)
    return list(result.scalars().all())


async def mark_notification_sent(session: AsyncSession, notification: Notification) -> Notification:
    """Mark notification as sent."""
    notification.status = NotificationStatus.SENT
    notification.sent_at = datetime.utcnow()
    notification.updated_at = datetime.utcnow()

    session.add(notification)
    await session.flush()
    return notification


async def mark_notification_failed(
    session: AsyncSession,
    notification: Notification,
    error_message: str,
) -> Notification:
    """Mark notification as failed."""
    notification.status = NotificationStatus.FAILED
    notification.error_message = error_message
    notification.updated_at = datetime.utcnow()

    session.add(notification)
    await session.flush()
    return notification


async def cleanup_old_notifications(session: AsyncSession, days: int = 90) -> int:
    """Delete notifications older than specified days. Returns count deleted."""
    from datetime import timedelta

    from sqlalchemy import delete

    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = delete(Notification).where(Notification.created_at < cutoff)
    result = await session.execute(stmt)
    return result.rowcount


# ===========================================
# Canonical Product Operations
# ===========================================


async def get_canonical_by_upc(session: AsyncSession, upc: str) -> CanonicalProduct | None:
    """Get canonical product by UPC."""
    query = select(CanonicalProduct).where(
        CanonicalProduct.upc == upc,
        CanonicalProduct.deleted_at.is_(None),
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_products_for_canonical(
    session: AsyncSession,
    canonical_id: int,
) -> list[Product]:
    """Get all products linked to a canonical product (for price comparison)."""
    query = select(Product).where(
        Product.canonical_id == canonical_id,
        Product.deleted_at.is_(None),
    )
    result = await session.execute(query)
    return list(result.scalars().all())


# ===========================================
# Statistics
# ===========================================


async def get_product_count(session: AsyncSession) -> int:
    """Get total count of active products."""
    query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    result = await session.execute(query)
    return result.scalar_one()


async def get_store_stats(session: AsyncSession, store_domain: str) -> dict[str, Any]:
    """Get statistics for a store."""
    # Product count
    product_count_query = select(func.count(Product.id)).where(
        Product.store_domain == store_domain,
        Product.deleted_at.is_(None),
    )
    product_count = (await session.execute(product_count_query)).scalar_one()

    # Active alerts count
    alert_count_query = (
        select(func.count(Alert.id))
        .join(Product)
        .where(
            Product.store_domain == store_domain,
            Alert.is_active.is_(True),
            Alert.deleted_at.is_(None),
        )
    )
    alert_count = (await session.execute(alert_count_query)).scalar_one()

    return {
        "product_count": product_count,
        "alert_count": alert_count,
    }
