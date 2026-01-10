"""
Failure detection and classification for self-healing.

Classifies scrape failures and determines when self-healing should be triggered.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from sqlmodel import Session, select

from src.database.models import Product, ProductStatus, ScrapeErrorType, ScrapeLog


class FailureCategory(str, Enum):
    """Categories of failures that may benefit from self-healing."""

    # Healable failures - can attempt selector regeneration
    PARSE_FAILURE = "parse_failure"  # Failed to extract data
    STRUCTURE_CHANGE = "structure_change"  # Website structure changed
    PRICE_VALIDATION = "price_validation"  # Extracted price invalid

    # Non-healable failures - require manual intervention
    BLOCKED = "blocked"  # CAPTCHA, login wall, rate limit
    NOT_FOUND = "not_found"  # 404, product removed
    NETWORK = "network"  # Connection issues
    TIMEOUT = "timeout"  # Request timeout
    ROBOTS_BLOCKED = "robots_blocked"  # Blocked by robots.txt

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class FailureAnalysis:
    """Result of failure analysis for a product."""

    product_id: int
    category: FailureCategory
    consecutive_failures: int
    needs_healing: bool
    needs_attention: bool
    last_error: str | None = None
    last_failure_at: datetime | None = None


# Mapping from ScrapeErrorType to FailureCategory
ERROR_TYPE_TO_CATEGORY: dict[ScrapeErrorType, FailureCategory] = {
    ScrapeErrorType.PARSE_FAILURE: FailureCategory.PARSE_FAILURE,
    ScrapeErrorType.STRUCTURE_CHANGE: FailureCategory.STRUCTURE_CHANGE,
    ScrapeErrorType.PRICE_VALIDATION: FailureCategory.PRICE_VALIDATION,
    ScrapeErrorType.BLOCKED: FailureCategory.BLOCKED,
    ScrapeErrorType.NOT_FOUND: FailureCategory.NOT_FOUND,
    ScrapeErrorType.NETWORK_ERROR: FailureCategory.NETWORK,
    ScrapeErrorType.TIMEOUT: FailureCategory.TIMEOUT,
    ScrapeErrorType.ROBOTS_BLOCKED: FailureCategory.ROBOTS_BLOCKED,
}

# Categories that can potentially be healed by selector regeneration
HEALABLE_CATEGORIES = {
    FailureCategory.PARSE_FAILURE,
    FailureCategory.STRUCTURE_CHANGE,
    FailureCategory.PRICE_VALIDATION,
}

# Default thresholds
DEFAULT_FAILURE_THRESHOLD = 3  # Consecutive failures before healing
DEFAULT_ATTENTION_THRESHOLD = 3  # Days of 404s before needs_attention
MAX_HEALING_ATTEMPTS = 3  # Max healing attempts per product


class FailureDetector:
    """
    Detects and classifies scrape failures for self-healing.

    Responsibilities:
    - Classify failure types from scrape errors
    - Track consecutive failures per product
    - Determine when self-healing should be triggered
    - Flag products needing manual attention
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        attention_days: int = DEFAULT_ATTENTION_THRESHOLD,
        max_healing_attempts: int = MAX_HEALING_ATTEMPTS,
    ):
        """
        Initialize failure detector.

        Args:
            failure_threshold: Consecutive failures before triggering healing
            attention_days: Days of 404s before flagging needs_attention
            max_healing_attempts: Max healing attempts before giving up
        """
        self.failure_threshold = failure_threshold
        self.attention_days = attention_days
        self.max_healing_attempts = max_healing_attempts

    def classify_error(self, error_type: ScrapeErrorType | None) -> FailureCategory:
        """
        Classify a scrape error into a failure category.

        Args:
            error_type: The scrape error type

        Returns:
            FailureCategory for the error
        """
        if error_type is None:
            return FailureCategory.UNKNOWN
        return ERROR_TYPE_TO_CATEGORY.get(error_type, FailureCategory.UNKNOWN)

    def is_healable(self, category: FailureCategory) -> bool:
        """
        Check if a failure category can be healed by selector regeneration.

        Args:
            category: The failure category

        Returns:
            True if category is healable
        """
        return category in HEALABLE_CATEGORIES

    def analyze_product(
        self,
        session: Session,
        product_id: int,
    ) -> FailureAnalysis | None:
        """
        Analyze a product's failure status.

        Args:
            session: Database session
            product_id: Product ID to analyze

        Returns:
            FailureAnalysis or None if product not found
        """
        # Get product
        product = session.get(Product, product_id)
        if not product or product.deleted_at is not None:
            return None

        # Get most recent failed scrape log
        stmt = (
            select(ScrapeLog)
            .where(ScrapeLog.product_id == product_id)
            .where(ScrapeLog.success.is_(False))
            .order_by(ScrapeLog.scraped_at.desc())
            .limit(1)
        )
        last_failure = session.exec(stmt).first()

        # Determine failure category
        category = FailureCategory.UNKNOWN
        last_error = None
        last_failure_at = None

        if last_failure:
            category = self.classify_error(last_failure.error_type)
            last_error = last_failure.error_message
            last_failure_at = last_failure.scraped_at

        # Determine if healing should be triggered
        needs_healing = (
            product.consecutive_failures >= self.failure_threshold
            and self.is_healable(category)
            and product.status != ProductStatus.NEEDS_ATTENTION
        )

        # Check if product needs manual attention (e.g., 404 for multiple days)
        needs_attention = self._check_needs_attention(
            session, product, category
        )

        return FailureAnalysis(
            product_id=product_id,
            category=category,
            consecutive_failures=product.consecutive_failures,
            needs_healing=needs_healing,
            needs_attention=needs_attention,
            last_error=last_error,
            last_failure_at=last_failure_at,
        )

    def _check_needs_attention(
        self,
        session: Session,
        product: Product,
        category: FailureCategory,
    ) -> bool:
        """
        Check if product needs manual attention.

        A product needs attention if:
        - 404 errors for more than attention_days consecutive days
        - Non-healable failures exceeding threshold
        - Already marked as needs_attention

        Args:
            session: Database session
            product: Product to check
            category: Current failure category

        Returns:
            True if needs attention
        """
        if product.status == ProductStatus.NEEDS_ATTENTION:
            return True

        # For 404s, check how long they've been occurring
        if category == FailureCategory.NOT_FOUND:
            cutoff = datetime.utcnow() - timedelta(days=self.attention_days)
            stmt = (
                select(ScrapeLog)
                .where(ScrapeLog.product_id == product.id)
                .where(ScrapeLog.error_type == ScrapeErrorType.NOT_FOUND)
                .where(ScrapeLog.scraped_at >= cutoff)
                .order_by(ScrapeLog.scraped_at.asc())
                .limit(1)
            )
            first_404 = session.exec(stmt).first()
            if first_404:
                # Has been 404 for at least attention_days
                return True

        # Non-healable failures exceeding threshold
        if (
            not self.is_healable(category)
            and category != FailureCategory.UNKNOWN
            and product.consecutive_failures >= self.failure_threshold
        ):
            return True

        return False

    def get_products_needing_healing(
        self,
        session: Session,
        store_domain: str | None = None,
        limit: int = 50,
    ) -> list[FailureAnalysis]:
        """
        Get products that need self-healing.

        Args:
            session: Database session
            store_domain: Optional filter by store
            limit: Max products to return

        Returns:
            List of FailureAnalysis for products needing healing
        """
        # Query products with consecutive failures at threshold
        stmt = (
            select(Product)
            .where(Product.deleted_at.is_(None))
            .where(Product.consecutive_failures >= self.failure_threshold)
            .where(Product.status != ProductStatus.NEEDS_ATTENTION)
            .where(Product.status != ProductStatus.ARCHIVED)
        )

        if store_domain:
            stmt = stmt.where(Product.store_domain == store_domain)

        stmt = stmt.limit(limit)
        products = session.exec(stmt).all()

        # Analyze each product
        results = []
        for product in products:
            analysis = self.analyze_product(session, product.id)
            if analysis and analysis.needs_healing:
                results.append(analysis)

        return results

    def record_failure(
        self,
        session: Session,
        product_id: int,
        error_type: ScrapeErrorType,
        error_message: str | None = None,
    ) -> int:
        """
        Record a scrape failure and update consecutive failure count.

        Args:
            session: Database session
            product_id: Product ID
            error_type: Type of error
            error_message: Optional error message

        Returns:
            Updated consecutive failure count
        """
        product = session.get(Product, product_id)
        if not product:
            return 0

        # Increment consecutive failures
        product.consecutive_failures += 1
        product.updated_at = datetime.utcnow()

        # Update status if needed
        category = self.classify_error(error_type)
        if self._check_needs_attention(session, product, category):
            product.status = ProductStatus.NEEDS_ATTENTION
        elif product.consecutive_failures >= self.failure_threshold:
            product.status = ProductStatus.ERROR

        session.add(product)
        session.commit()
        session.refresh(product)

        return product.consecutive_failures

    def record_success(
        self,
        session: Session,
        product_id: int,
    ) -> None:
        """
        Record a successful scrape and reset failure count.

        Args:
            session: Database session
            product_id: Product ID
        """
        product = session.get(Product, product_id)
        if not product:
            return

        # Reset consecutive failures
        product.consecutive_failures = 0
        product.last_checked_at = datetime.utcnow()
        product.updated_at = datetime.utcnow()

        # Reset status if it was in error state
        if product.status in (ProductStatus.ERROR, ProductStatus.NEEDS_ATTENTION):
            product.status = ProductStatus.ACTIVE

        session.add(product)
        session.commit()


# ===========================================
# Convenience Functions
# ===========================================

_failure_detector: FailureDetector | None = None


def get_failure_detector() -> FailureDetector:
    """Get the global failure detector instance."""
    global _failure_detector
    if _failure_detector is None:
        _failure_detector = FailureDetector()
    return _failure_detector
