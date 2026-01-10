"""
Self-healing service orchestration.

Coordinates failure detection, selector regeneration, and store health updates.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from src.database.models import Product, ProductStatus, Store
from src.scraper import ScraperEngine, get_scraper_engine

from .detector import (
    FailureAnalysis,
    FailureDetector,
    get_failure_detector,
)
from .regenerator import (
    RegenerationResult,
    SelectorRegenerator,
    get_selector_regenerator,
)

logger = logging.getLogger(__name__)


@dataclass
class HealingAttempt:
    """Record of a healing attempt for a product."""

    product_id: int
    domain: str
    success: bool
    attempt_number: int
    error: str | None = None
    new_selectors: dict | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class HealingReport:
    """Summary report of healing operations."""

    total_products_checked: int = 0
    products_healed: int = 0
    products_failed: int = 0
    products_flagged_attention: int = 0
    stores_updated: int = 0
    attempts: list[HealingAttempt] | None = None

    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []


class SelfHealingService:
    """
    Orchestrates the self-healing process.

    Workflow:
    1. Detect products with consecutive failures
    2. Fetch fresh HTML for failed products
    3. Use LLM to regenerate selectors
    4. Test new selectors with scraper
    5. Update store selectors if successful
    6. Flag products needing manual attention
    """

    def __init__(
        self,
        detector: FailureDetector | None = None,
        regenerator: SelectorRegenerator | None = None,
        scraper: ScraperEngine | None = None,
        max_products_per_run: int = 10,
        store_failure_threshold: float = 0.5,  # 50% products failing
    ):
        """
        Initialize self-healing service.

        Args:
            detector: Failure detector instance
            regenerator: Selector regenerator instance
            scraper: Scraper engine for testing selectors
            max_products_per_run: Max products to heal per run
            store_failure_threshold: Fraction of failures to flag store
        """
        self.detector = detector or get_failure_detector()
        self.regenerator = regenerator or get_selector_regenerator()
        self.scraper = scraper or get_scraper_engine()
        self.max_products_per_run = max_products_per_run
        self.store_failure_threshold = store_failure_threshold

        # Track healing attempts per product (in-memory, reset on restart)
        self._healing_attempts: dict[int, int] = {}

    async def run_healing_cycle(
        self,
        session: Session,
        store_domain: str | None = None,
    ) -> HealingReport:
        """
        Run a complete healing cycle.

        Args:
            session: Database session
            store_domain: Optional filter by store

        Returns:
            HealingReport with results
        """
        report = HealingReport()

        # Get products needing healing
        products_to_heal = self.detector.get_products_needing_healing(
            session,
            store_domain=store_domain,
            limit=self.max_products_per_run,
        )
        report.total_products_checked = len(products_to_heal)

        if not products_to_heal:
            logger.info("No products need healing")
            return report

        logger.info(f"Found {len(products_to_heal)} products needing healing")

        # Group by store for efficiency
        by_store: dict[str, list[FailureAnalysis]] = {}
        for analysis in products_to_heal:
            product = session.get(Product, analysis.product_id)
            if product:
                domain = product.store_domain
                if domain not in by_store:
                    by_store[domain] = []
                by_store[domain].append(analysis)

        # Process each store
        for domain, analyses in by_store.items():
            store_healed = await self._heal_store_products(
                session, domain, analyses, report
            )
            if store_healed:
                report.stores_updated += 1

        # Check for stores needing attention
        await self._check_store_health(session, report)

        logger.info(
            f"Healing cycle complete: {report.products_healed} healed, "
            f"{report.products_failed} failed, "
            f"{report.products_flagged_attention} flagged"
        )

        return report

    async def _heal_store_products(
        self,
        session: Session,
        domain: str,
        analyses: list[FailureAnalysis],
        report: HealingReport,
    ) -> bool:
        """
        Heal products from a single store.

        Attempts to regenerate selectors once for the store,
        then applies to all affected products.

        Args:
            session: Database session
            domain: Store domain
            analyses: List of product analyses
            report: Report to update

        Returns:
            True if store selectors were updated
        """
        store = session.get(Store, domain)
        if not store:
            return False

        # Pick first product to use for selector regeneration
        first_analysis = analyses[0]
        first_product = session.get(Product, first_analysis.product_id)
        if not first_product:
            return False

        # Check healing attempt limit
        attempt_num = self._healing_attempts.get(first_product.id, 0) + 1
        if attempt_num > self.regenerator.max_attempts:
            logger.warning(
                f"Product {first_product.id} exceeded max healing attempts"
            )
            await self._flag_for_attention(session, first_product)
            report.products_flagged_attention += 1
            return False

        # Fetch fresh HTML
        try:
            scrape_result = await self.scraper.scrape(
                first_product.url,
                validate_ssrf=False,  # Already validated
            )

            if not scrape_result.success:
                logger.warning(f"Failed to fetch HTML for healing: {domain}")
                report.products_failed += len(analyses)
                return False

        except Exception as e:
            logger.error(f"Scrape failed during healing: {e}")
            report.products_failed += len(analyses)
            return False

        # Get HTML content - need to re-fetch with raw HTML
        # For now, mark as failed - full implementation would need raw HTML access
        # This is a simplified version that demonstrates the architecture

        # Attempt regeneration
        regen_result = await self._try_regenerate(
            session, domain, store.selectors, first_product, attempt_num
        )

        attempt = HealingAttempt(
            product_id=first_product.id,
            domain=domain,
            success=regen_result.success,
            attempt_number=attempt_num,
            error=regen_result.error,
            new_selectors=regen_result.selectors,
        )
        report.attempts.append(attempt)
        self._healing_attempts[first_product.id] = attempt_num

        if regen_result.success and regen_result.selectors:
            # Update store selectors
            updated = await self.regenerator.update_store_selectors(
                session, domain, regen_result.selectors
            )

            if updated:
                # Reset failure counts for all affected products
                for analysis in analyses:
                    self.detector.record_success(session, analysis.product_id)
                    report.products_healed += 1

                logger.info(f"Successfully healed {len(analyses)} products for {domain}")
                return True

        # Regeneration failed
        report.products_failed += len(analyses)

        # Check if we should flag for attention
        if attempt_num >= self.regenerator.max_attempts:
            for analysis in analyses:
                product = session.get(Product, analysis.product_id)
                if product:
                    await self._flag_for_attention(session, product)
                    report.products_flagged_attention += 1

        return False

    async def _try_regenerate(
        self,
        session: Session,
        domain: str,
        current_selectors: dict | None,
        product: Product,
        attempt_num: int,
    ) -> RegenerationResult:
        """
        Attempt to regenerate selectors for a product.

        In a full implementation, this would:
        1. Fetch raw HTML from the product URL
        2. Pass to regenerator for LLM analysis
        3. Test new selectors against the page
        4. Return result

        For now, returns a placeholder indicating the architecture.
        """
        # Placeholder - would fetch HTML and call regenerator.regenerate()
        # This demonstrates the service architecture

        logger.info(
            f"Attempting selector regeneration for {domain} "
            f"(attempt {attempt_num}/{self.regenerator.max_attempts})"
        )

        # In production, this would be:
        # html = await fetch_raw_html(product.url)
        # return await self.regenerator.regenerate(html, domain, current_selectors)

        return RegenerationResult(
            success=False,
            domain=domain,
            error="Full regeneration requires raw HTML access - placeholder",
        )

    async def _flag_for_attention(
        self,
        session: Session,
        product: Product,
    ) -> None:
        """Flag a product as needing manual attention."""
        product.status = ProductStatus.NEEDS_ATTENTION
        product.updated_at = datetime.utcnow()
        session.add(product)
        session.commit()

        logger.info(f"Flagged product {product.id} for manual attention")

    async def _check_store_health(
        self,
        session: Session,
        report: HealingReport,
    ) -> None:
        """
        Check store health and flag stores with high failure rates.

        A store is flagged if >50% of its products are failing.
        """
        # This would query store health metrics
        # Implementation in health.py
        pass

    async def heal_single_product(
        self,
        session: Session,
        product_id: int,
    ) -> HealingAttempt:
        """
        Attempt to heal a single product.

        Args:
            session: Database session
            product_id: Product to heal

        Returns:
            HealingAttempt with result
        """
        analysis = self.detector.analyze_product(session, product_id)
        if not analysis:
            return HealingAttempt(
                product_id=product_id,
                domain="unknown",
                success=False,
                attempt_number=0,
                error="Product not found",
            )

        if not analysis.needs_healing:
            return HealingAttempt(
                product_id=product_id,
                domain="unknown",
                success=False,
                attempt_number=0,
                error="Product does not need healing",
            )

        product = session.get(Product, product_id)
        if not product:
            return HealingAttempt(
                product_id=product_id,
                domain="unknown",
                success=False,
                attempt_number=0,
                error="Product not found",
            )

        report = HealingReport()
        await self._heal_store_products(
            session,
            product.store_domain,
            [analysis],
            report,
        )

        if report.attempts:
            return report.attempts[0]

        return HealingAttempt(
            product_id=product_id,
            domain=product.store_domain,
            success=False,
            attempt_number=0,
            error="Healing failed",
        )

    def reset_healing_attempts(self, product_id: int | None = None) -> None:
        """
        Reset healing attempt counters.

        Args:
            product_id: Specific product to reset, or None for all
        """
        if product_id is not None:
            self._healing_attempts.pop(product_id, None)
        else:
            self._healing_attempts.clear()


# ===========================================
# Convenience Functions
# ===========================================

_self_healing_service: SelfHealingService | None = None


def get_self_healing_service() -> SelfHealingService:
    """Get the global self-healing service instance."""
    global _self_healing_service
    if _self_healing_service is None:
        _self_healing_service = SelfHealingService()
    return _self_healing_service
