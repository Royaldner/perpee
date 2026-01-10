"""
Scheduled job definitions for Perpee.

Defines all recurring jobs for price monitoring, cleanup, and health checks.
"""

import logging
from datetime import datetime, timedelta

from sqlmodel import select

from src.database.models import (
    Notification,
    Product,
    ProductStatus,
    ScrapeLog,
)
from src.database.session import get_session
from src.healing import get_self_healing_service, get_store_health_calculator
from src.scraper import get_scraper_engine

from .batching import get_batch_processor

logger = logging.getLogger(__name__)


# ===========================================
# Job IDs (constants for referencing jobs)
# ===========================================

JOB_DAILY_SCRAPE = "daily_scrape"
JOB_HEALTH_CHECK = "health_check"
JOB_CLEANUP = "cleanup"
JOB_HEALING = "healing"

# Prefix for dynamic jobs
JOB_PREFIX_PRODUCT = "product_"
JOB_PREFIX_STORE = "store_"


# ===========================================
# Daily Scrape Job
# ===========================================


async def daily_scrape_job() -> dict:
    """
    Default daily price check for all active products.

    Runs at 6 AM UTC by default with random jitter.
    Groups products by store for efficient batch processing.

    Returns:
        Summary of scrape results
    """
    logger.info("Starting daily scrape job")
    start_time = datetime.utcnow()

    batch_processor = get_batch_processor()

    async with get_session() as session:
        # Get all active products
        stmt = (
            select(Product)
            .where(Product.deleted_at.is_(None))
            .where(Product.status == ProductStatus.ACTIVE)
        )
        products = list(session.exec(stmt).all())

        if not products:
            logger.info("No active products to scrape")
            return {"status": "completed", "products_checked": 0}

        # Process in batches by store
        results = await batch_processor.process_products(session, products)

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Daily scrape completed: {results['successful']}/{results['total']} "
            f"successful in {duration:.1f}s"
        )

        return {
            "status": "completed",
            "products_checked": results["total"],
            "successful": results["successful"],
            "failed": results["failed"],
            "duration_seconds": duration,
        }


# ===========================================
# Product-specific Scrape Job
# ===========================================


async def product_scrape_job(product_id: int) -> dict:
    """
    Scrape a specific product on its custom schedule.

    Args:
        product_id: Product to scrape

    Returns:
        Scrape result summary
    """
    logger.info(f"Starting product scrape job for product {product_id}")

    scraper = get_scraper_engine()

    async with get_session() as session:
        product = session.get(Product, product_id)

        if not product or product.deleted_at is not None:
            logger.warning(f"Product {product_id} not found or deleted")
            return {"status": "skipped", "reason": "product_not_found"}

        if product.status != ProductStatus.ACTIVE:
            logger.info(f"Skipping inactive product {product_id}")
            return {"status": "skipped", "reason": "product_inactive"}

        # Scrape the product
        result = await scraper.scrape(product.url)

        # Log the result
        scrape_log = ScrapeLog(
            product_id=product_id,
            success=result.success,
            strategy_used=result.strategy_used,
            error_type=result.error_type,
            error_message=result.error_message,
            response_time_ms=result.response_time_ms,
        )
        session.add(scrape_log)

        if result.success and result.product:
            # Update product data
            product.current_price = result.product.price
            product.original_price = result.product.original_price
            product.in_stock = result.product.in_stock
            product.last_checked_at = datetime.utcnow()
            product.consecutive_failures = 0
            session.add(product)
        else:
            # Record failure
            product.consecutive_failures += 1
            product.last_checked_at = datetime.utcnow()
            session.add(product)

        session.commit()

        return {
            "status": "completed" if result.success else "failed",
            "product_id": product_id,
            "success": result.success,
            "price": result.product.price if result.product else None,
        }


# ===========================================
# Store Batch Scrape Job
# ===========================================


async def store_batch_job(store_domain: str) -> dict:
    """
    Scrape all products for a specific store.

    Args:
        store_domain: Store domain to scrape

    Returns:
        Batch result summary
    """
    logger.info(f"Starting store batch job for {store_domain}")

    batch_processor = get_batch_processor()

    async with get_session() as session:
        # Get all active products for this store
        stmt = (
            select(Product)
            .where(Product.store_domain == store_domain)
            .where(Product.deleted_at.is_(None))
            .where(Product.status == ProductStatus.ACTIVE)
        )
        products = list(session.exec(stmt).all())

        if not products:
            logger.info(f"No active products for store {store_domain}")
            return {"status": "completed", "products_checked": 0}

        results = await batch_processor.process_store_batch(
            session, store_domain, products
        )

        return {
            "status": "completed",
            "store": store_domain,
            "products_checked": results["total"],
            "successful": results["successful"],
            "failed": results["failed"],
        }


# ===========================================
# Health Calculation Job
# ===========================================


async def health_calculation_job() -> dict:
    """
    Calculate and update store health metrics.

    Runs daily to update success rates and identify unhealthy stores.

    Returns:
        Health check summary
    """
    logger.info("Starting health calculation job")

    health_calculator = get_store_health_calculator()

    async with get_session() as session:
        updated = health_calculator.update_all_health(session)

        # Get stores needing attention
        unhealthy = health_calculator.get_stores_needing_attention(session)

        logger.info(
            f"Health calculation complete: {updated} stores updated, "
            f"{len(unhealthy)} needing attention"
        )

        return {
            "status": "completed",
            "stores_updated": updated,
            "stores_needing_attention": len(unhealthy),
            "unhealthy_stores": [s.domain for s in unhealthy],
        }


# ===========================================
# Self-Healing Job
# ===========================================


async def healing_job() -> dict:
    """
    Run self-healing cycle for failing products.

    Attempts to regenerate selectors for products with consecutive failures.

    Returns:
        Healing summary
    """
    logger.info("Starting healing job")

    healing_service = get_self_healing_service()

    async with get_session() as session:
        report = await healing_service.run_healing_cycle(session)

        logger.info(
            f"Healing job complete: {report.products_healed} healed, "
            f"{report.products_failed} failed"
        )

        return {
            "status": "completed",
            "products_checked": report.total_products_checked,
            "products_healed": report.products_healed,
            "products_failed": report.products_failed,
            "products_flagged": report.products_flagged_attention,
        }


# ===========================================
# Cleanup Job
# ===========================================


async def cleanup_job(
    scrape_log_days: int = 30,
    notification_days: int = 90,
) -> dict:
    """
    Clean up old data per retention policy.

    Args:
        scrape_log_days: Days to keep scrape logs (default 30)
        notification_days: Days to keep notifications (default 90)

    Returns:
        Cleanup summary
    """
    logger.info("Starting cleanup job")

    async with get_session() as session:
        now = datetime.utcnow()

        # Delete old scrape logs
        scrape_cutoff = now - timedelta(days=scrape_log_days)
        scrape_stmt = select(ScrapeLog).where(ScrapeLog.scraped_at < scrape_cutoff)
        old_logs = list(session.exec(scrape_stmt).all())
        for log in old_logs:
            session.delete(log)
        scrape_deleted = len(old_logs)

        # Delete old notifications
        notification_cutoff = now - timedelta(days=notification_days)
        notification_stmt = select(Notification).where(
            Notification.created_at < notification_cutoff
        )
        old_notifications = list(session.exec(notification_stmt).all())
        for notification in old_notifications:
            session.delete(notification)
        notification_deleted = len(old_notifications)

        session.commit()

        logger.info(
            f"Cleanup complete: {scrape_deleted} scrape logs, "
            f"{notification_deleted} notifications deleted"
        )

        return {
            "status": "completed",
            "scrape_logs_deleted": scrape_deleted,
            "notifications_deleted": notification_deleted,
        }


# ===========================================
# Job Registration Helper
# ===========================================


def register_default_jobs(scheduler) -> None:
    """
    Register all default scheduled jobs.

    Args:
        scheduler: SchedulerService instance
    """
    # Daily scrape at 6 AM UTC with 30-minute jitter
    scheduler.add_job(
        daily_scrape_job,
        job_id=JOB_DAILY_SCRAPE,
        cron_expression="0 6 * * *",
        jitter=1800,  # 30 minutes
    )

    # Health check at 7 AM UTC daily
    scheduler.add_job(
        health_calculation_job,
        job_id=JOB_HEALTH_CHECK,
        cron_expression="0 7 * * *",
    )

    # Self-healing at 8 AM UTC daily
    scheduler.add_job(
        healing_job,
        job_id=JOB_HEALING,
        cron_expression="0 8 * * *",
    )

    # Cleanup weekly on Sunday at midnight
    scheduler.add_job(
        cleanup_job,
        job_id=JOB_CLEANUP,
        cron_expression="0 0 * * 0",
    )

    logger.info("Registered default scheduled jobs")


def register_product_job(
    scheduler,
    product_id: int,
    cron_expression: str,
) -> str:
    """
    Register a custom schedule for a product.

    Args:
        scheduler: SchedulerService instance
        product_id: Product ID
        cron_expression: CRON schedule

    Returns:
        Job ID
    """
    job_id = f"{JOB_PREFIX_PRODUCT}{product_id}"
    return scheduler.add_job(
        product_scrape_job,
        job_id=job_id,
        cron_expression=cron_expression,
        kwargs={"product_id": product_id},
    )


def register_store_job(
    scheduler,
    store_domain: str,
    cron_expression: str,
) -> str:
    """
    Register a custom schedule for a store.

    Args:
        scheduler: SchedulerService instance
        store_domain: Store domain
        cron_expression: CRON schedule

    Returns:
        Job ID
    """
    job_id = f"{JOB_PREFIX_STORE}{store_domain}"
    return scheduler.add_job(
        store_batch_job,
        job_id=job_id,
        cron_expression=cron_expression,
        kwargs={"store_domain": store_domain},
    )
