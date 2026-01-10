"""
Batch processing for scheduled scrapes.

Groups products by store for efficient browser reuse and rate limit compliance.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from sqlmodel import Session

from src.database.models import (
    PriceHistory,
    Product,
    ProductStatus,
    ScrapeLog,
    Store,
)
from src.healing import get_store_health_calculator
from src.scraper import ScraperEngine, ScrapeResult, get_scraper_engine

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of a batch scrape operation."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    by_store: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class BatchProcessor:
    """
    Processes product scrapes in batches by store.

    Benefits:
    - Reuses browser sessions per store
    - Respects per-store rate limits
    - Efficient memory usage with MemoryAdaptiveDispatcher
    - Groups products for batch API calls
    """

    def __init__(
        self,
        scraper: ScraperEngine | None = None,
        batch_size: int = 10,
        inter_batch_delay: float = 2.0,
    ):
        """
        Initialize batch processor.

        Args:
            scraper: Scraper engine instance
            batch_size: Products per batch within a store
            inter_batch_delay: Seconds between batches (rate limiting)
        """
        self.scraper = scraper or get_scraper_engine()
        self.batch_size = batch_size
        self.inter_batch_delay = inter_batch_delay
        self.health_calculator = get_store_health_calculator()

    async def process_products(
        self,
        session: Session,
        products: list[Product],
    ) -> dict:
        """
        Process a list of products, grouped by store.

        Args:
            session: Database session
            products: Products to process

        Returns:
            Summary dict with results
        """
        if not products:
            return {"total": 0, "successful": 0, "failed": 0, "skipped": 0}

        # Group by store
        by_store = self._group_by_store(products)

        result = BatchResult(total=len(products))

        # Process each store
        for domain, store_products in by_store.items():
            store_result = await self.process_store_batch(
                session, domain, store_products
            )
            result.successful += store_result["successful"]
            result.failed += store_result["failed"]
            result.skipped += store_result["skipped"]
            result.by_store[domain] = store_result

            # Delay between stores
            if len(by_store) > 1:
                await asyncio.sleep(self.inter_batch_delay)

        return {
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "by_store": result.by_store,
        }

    async def process_store_batch(
        self,
        session: Session,
        domain: str,
        products: list[Product],
    ) -> dict:
        """
        Process all products for a single store.

        Uses batch scraping for efficiency.

        Args:
            session: Database session
            domain: Store domain
            products: Products from this store

        Returns:
            Summary dict with results
        """
        logger.info(f"Processing batch of {len(products)} products for {domain}")

        successful = 0
        failed = 0
        skipped = 0

        # Check if store is active
        store = session.get(Store, domain)
        if not store or not store.is_active:
            logger.warning(f"Store {domain} is not active, skipping batch")
            return {
                "successful": 0,
                "failed": 0,
                "skipped": len(products),
            }

        # Process in batches
        for i in range(0, len(products), self.batch_size):
            batch = products[i : i + self.batch_size]
            urls = [p.url for p in batch]

            try:
                # Use batch scraping
                results = await self.scraper.scrape_batch(urls)

                # Process results
                for product, result in zip(batch, results, strict=True):
                    processed = self._process_result(session, product, result)
                    if processed == "success":
                        successful += 1
                    elif processed == "failed":
                        failed += 1
                    else:
                        skipped += 1

            except Exception as e:
                logger.error(f"Batch scrape failed for {domain}: {e}")
                failed += len(batch)
                continue

            # Commit after each batch
            session.commit()

            # Inter-batch delay within store
            if i + self.batch_size < len(products):
                await asyncio.sleep(self.inter_batch_delay / 2)

        # Update store health after batch
        self.health_calculator.record_scrape_success(session, domain)

        logger.info(
            f"Completed batch for {domain}: "
            f"{successful} successful, {failed} failed, {skipped} skipped"
        )

        return {
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
        }

    def _group_by_store(
        self,
        products: list[Product],
    ) -> dict[str, list[Product]]:
        """Group products by store domain."""
        by_store: dict[str, list[Product]] = defaultdict(list)
        for product in products:
            by_store[product.store_domain].append(product)
        return dict(by_store)

    def _process_result(
        self,
        session: Session,
        product: Product,
        result: ScrapeResult,
    ) -> str:
        """
        Process a single scrape result.

        Updates product and creates scrape log.

        Args:
            session: Database session
            product: Product that was scraped
            result: Scrape result

        Returns:
            "success", "failed", or "skipped"
        """
        now = datetime.utcnow()

        # Create scrape log
        scrape_log = ScrapeLog(
            product_id=product.id,
            success=result.success,
            strategy_used=result.strategy_used,
            error_type=result.error_type,
            error_message=result.error_message,
            response_time_ms=result.response_time_ms,
        )
        session.add(scrape_log)

        if result.success and result.product:
            # Check for price change
            old_price = product.current_price
            new_price = result.product.price

            # Update product
            product.current_price = new_price
            product.original_price = result.product.original_price
            product.in_stock = result.product.in_stock
            product.last_checked_at = now
            product.consecutive_failures = 0
            product.updated_at = now

            # Update name/brand if we got better data
            if result.product.name and not product.name:
                product.name = result.product.name
            if result.product.brand and not product.brand:
                product.brand = result.product.brand
            if result.product.image_url and not product.image_url:
                product.image_url = result.product.image_url

            session.add(product)

            # Record price history if changed
            if old_price is None or abs(old_price - new_price) > 0.01:
                price_history = PriceHistory(
                    product_id=product.id,
                    price=new_price,
                    original_price=result.product.original_price,
                    in_stock=result.product.in_stock,
                )
                session.add(price_history)

            return "success"

        else:
            # Record failure
            product.consecutive_failures += 1
            product.last_checked_at = now
            product.updated_at = now

            # Update status based on failures
            if product.consecutive_failures >= 3:
                product.status = ProductStatus.ERROR

            session.add(product)
            return "failed"

    async def process_single(
        self,
        session: Session,
        product: Product,
    ) -> str:
        """
        Process a single product.

        Args:
            session: Database session
            product: Product to process

        Returns:
            "success", "failed", or "skipped"
        """
        if product.status != ProductStatus.ACTIVE:
            return "skipped"

        result = await self.scraper.scrape(product.url)
        status = self._process_result(session, product, result)
        session.commit()

        return status


# ===========================================
# Convenience Functions
# ===========================================

_batch_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    """Get the global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
