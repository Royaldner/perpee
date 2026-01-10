"""
Store health metrics calculation.

Tracks success rates and identifies stores needing attention.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlmodel import Session, func, select

from src.database.models import Product, ProductStatus, ScrapeLog, Store

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_HEALTH_WINDOW_DAYS = 7  # Calculate health over 7 days
DEFAULT_FAILURE_THRESHOLD = 0.5  # 50% failure rate flags store
DEFAULT_MIN_SCRAPES = 5  # Minimum scrapes to calculate health


@dataclass
class StoreHealth:
    """Health metrics for a single store."""

    domain: str
    name: str
    total_products: int
    active_products: int
    failing_products: int
    success_rate: float  # 0.0 to 1.0
    total_scrapes: int
    successful_scrapes: int
    is_healthy: bool
    last_success_at: datetime | None = None
    needs_attention: bool = False


@dataclass
class HealthReport:
    """Overall health report across all stores."""

    calculated_at: datetime
    total_stores: int
    healthy_stores: int
    unhealthy_stores: int
    stores_needing_attention: int
    overall_success_rate: float
    store_health: list[StoreHealth]


class StoreHealthCalculator:
    """
    Calculates and tracks store health metrics.

    Health is based on:
    - 7-day scrape success rate
    - Number of failing products
    - Last successful scrape time
    """

    def __init__(
        self,
        window_days: int = DEFAULT_HEALTH_WINDOW_DAYS,
        failure_threshold: float = DEFAULT_FAILURE_THRESHOLD,
        min_scrapes: int = DEFAULT_MIN_SCRAPES,
    ):
        """
        Initialize health calculator.

        Args:
            window_days: Days to look back for health calculation
            failure_threshold: Failure rate that flags store as unhealthy
            min_scrapes: Minimum scrapes needed to calculate health
        """
        self.window_days = window_days
        self.failure_threshold = failure_threshold
        self.min_scrapes = min_scrapes

    def calculate_store_health(
        self,
        session: Session,
        domain: str,
    ) -> StoreHealth | None:
        """
        Calculate health metrics for a single store.

        Args:
            session: Database session
            domain: Store domain

        Returns:
            StoreHealth or None if store not found
        """
        store = session.get(Store, domain)
        if not store:
            return None

        # Calculate time window
        cutoff = datetime.utcnow() - timedelta(days=self.window_days)

        # Count products
        total_products = self._count_products(session, domain)
        active_products = self._count_products(
            session, domain, status=ProductStatus.ACTIVE
        )
        failing_products = self._count_failing_products(session, domain)

        # Calculate scrape success rate
        scrape_stats = self._calculate_scrape_stats(session, domain, cutoff)

        # Determine health status
        success_rate = scrape_stats["success_rate"]
        is_healthy = success_rate >= (1 - self.failure_threshold)

        # Check if needs attention
        needs_attention = (
            not is_healthy
            or failing_products > total_products * self.failure_threshold
        )

        return StoreHealth(
            domain=domain,
            name=store.name,
            total_products=total_products,
            active_products=active_products,
            failing_products=failing_products,
            success_rate=success_rate,
            total_scrapes=scrape_stats["total"],
            successful_scrapes=scrape_stats["successful"],
            is_healthy=is_healthy,
            last_success_at=store.last_success_at,
            needs_attention=needs_attention,
        )

    def calculate_all_health(
        self,
        session: Session,
        active_only: bool = True,
    ) -> HealthReport:
        """
        Calculate health for all stores.

        Args:
            session: Database session
            active_only: Only include active stores

        Returns:
            HealthReport with all store metrics
        """
        # Get all stores
        stmt = select(Store)
        if active_only:
            stmt = stmt.where(Store.is_active.is_(True))

        stores = session.exec(stmt).all()

        store_health: list[StoreHealth] = []
        total_success = 0
        total_scrapes = 0

        for store in stores:
            health = self.calculate_store_health(session, store.domain)
            if health:
                store_health.append(health)
                total_success += health.successful_scrapes
                total_scrapes += health.total_scrapes

        # Calculate overall metrics
        healthy_stores = sum(1 for h in store_health if h.is_healthy)
        unhealthy_stores = len(store_health) - healthy_stores
        needs_attention = sum(1 for h in store_health if h.needs_attention)
        overall_rate = total_success / total_scrapes if total_scrapes > 0 else 1.0

        return HealthReport(
            calculated_at=datetime.utcnow(),
            total_stores=len(store_health),
            healthy_stores=healthy_stores,
            unhealthy_stores=unhealthy_stores,
            stores_needing_attention=needs_attention,
            overall_success_rate=overall_rate,
            store_health=store_health,
        )

    def update_store_health(
        self,
        session: Session,
        domain: str,
    ) -> bool:
        """
        Update stored health metrics for a store.

        Args:
            session: Database session
            domain: Store domain

        Returns:
            True if update successful
        """
        health = self.calculate_store_health(session, domain)
        if not health:
            return False

        store = session.get(Store, domain)
        if not store:
            return False

        # Update store success rate
        store.success_rate = health.success_rate
        store.updated_at = datetime.utcnow()

        session.add(store)
        session.commit()

        logger.info(
            f"Updated health for {domain}: "
            f"{health.success_rate:.1%} success rate"
        )

        return True

    def update_all_health(
        self,
        session: Session,
        active_only: bool = True,
    ) -> int:
        """
        Update health metrics for all stores.

        Args:
            session: Database session
            active_only: Only update active stores

        Returns:
            Number of stores updated
        """
        stmt = select(Store)
        if active_only:
            stmt = stmt.where(Store.is_active.is_(True))

        stores = session.exec(stmt).all()
        updated = 0

        for store in stores:
            if self.update_store_health(session, store.domain):
                updated += 1

        return updated

    def get_unhealthy_stores(
        self,
        session: Session,
    ) -> list[StoreHealth]:
        """
        Get list of unhealthy stores.

        Args:
            session: Database session

        Returns:
            List of unhealthy StoreHealth
        """
        report = self.calculate_all_health(session)
        return [h for h in report.store_health if not h.is_healthy]

    def get_stores_needing_attention(
        self,
        session: Session,
    ) -> list[StoreHealth]:
        """
        Get stores that need manual attention.

        Args:
            session: Database session

        Returns:
            List of StoreHealth needing attention
        """
        report = self.calculate_all_health(session)
        return [h for h in report.store_health if h.needs_attention]

    def _count_products(
        self,
        session: Session,
        domain: str,
        status: ProductStatus | None = None,
    ) -> int:
        """Count products for a store."""
        stmt = (
            select(func.count(Product.id))
            .where(Product.store_domain == domain)
            .where(Product.deleted_at.is_(None))
        )

        if status is not None:
            stmt = stmt.where(Product.status == status)

        result = session.exec(stmt).one()
        return result or 0

    def _count_failing_products(
        self,
        session: Session,
        domain: str,
    ) -> int:
        """Count products with errors or needing attention."""
        stmt = (
            select(func.count(Product.id))
            .where(Product.store_domain == domain)
            .where(Product.deleted_at.is_(None))
            .where(
                Product.status.in_([
                    ProductStatus.ERROR,
                    ProductStatus.NEEDS_ATTENTION,
                ])
            )
        )

        result = session.exec(stmt).one()
        return result or 0

    def _calculate_scrape_stats(
        self,
        session: Session,
        domain: str,
        cutoff: datetime,
    ) -> dict:
        """Calculate scrape statistics for a store."""
        # Get product IDs for this store
        product_stmt = (
            select(Product.id)
            .where(Product.store_domain == domain)
            .where(Product.deleted_at.is_(None))
        )
        product_ids = list(session.exec(product_stmt).all())

        if not product_ids:
            return {"total": 0, "successful": 0, "success_rate": 1.0}

        # Count total scrapes
        total_stmt = (
            select(func.count(ScrapeLog.id))
            .where(ScrapeLog.product_id.in_(product_ids))
            .where(ScrapeLog.scraped_at >= cutoff)
        )
        total = session.exec(total_stmt).one() or 0

        # Count successful scrapes
        success_stmt = (
            select(func.count(ScrapeLog.id))
            .where(ScrapeLog.product_id.in_(product_ids))
            .where(ScrapeLog.scraped_at >= cutoff)
            .where(ScrapeLog.success.is_(True))
        )
        successful = session.exec(success_stmt).one() or 0

        # Calculate rate
        if total < self.min_scrapes:
            # Not enough data, assume healthy
            success_rate = 1.0
        else:
            success_rate = successful / total if total > 0 else 1.0

        return {
            "total": total,
            "successful": successful,
            "success_rate": success_rate,
        }

    def record_scrape_success(
        self,
        session: Session,
        domain: str,
    ) -> None:
        """
        Record a successful scrape for a store.

        Updates last_success_at timestamp.

        Args:
            session: Database session
            domain: Store domain
        """
        store = session.get(Store, domain)
        if store:
            store.last_success_at = datetime.utcnow()
            store.updated_at = datetime.utcnow()
            session.add(store)
            session.commit()


# ===========================================
# Convenience Functions
# ===========================================

_store_health_calculator: StoreHealthCalculator | None = None


def get_store_health_calculator() -> StoreHealthCalculator:
    """Get the global store health calculator instance."""
    global _store_health_calculator
    if _store_health_calculator is None:
        _store_health_calculator = StoreHealthCalculator()
    return _store_health_calculator
