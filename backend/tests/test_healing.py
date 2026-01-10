"""
Tests for the self-healing module.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from src.database.models import (
    Product,
    ProductStatus,
    ScrapeErrorType,
    ScrapeLog,
    SQLModel,
    Store,
)
from src.healing.detector import (
    DEFAULT_FAILURE_THRESHOLD,
    HEALABLE_CATEGORIES,
    FailureCategory,
    FailureDetector,
    get_failure_detector,
)
from src.healing.health import (
    StoreHealthCalculator,
    get_store_health_calculator,
)
from src.healing.regenerator import (
    RegenerationResult,
    SelectorConfig,
    SelectorRegenerator,
)
from src.healing.service import (
    HealingAttempt,
    HealingReport,
    SelfHealingService,
)

# ===========================================
# Test Fixtures
# ===========================================


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_store(test_session):
    """Create sample store for testing."""
    store = Store(
        domain="test.example.com",
        name="Test Store",
        is_whitelisted=True,
        is_active=True,
        rate_limit_rpm=10,
        success_rate=1.0,
        selectors={"price": {"css": [".price"]}},
    )
    test_session.add(store)
    test_session.commit()
    test_session.refresh(store)
    return store


@pytest.fixture
def sample_product(test_session, sample_store):
    """Create sample product for testing."""
    product = Product(
        url="https://test.example.com/product/1",
        store_domain=sample_store.domain,
        name="Test Product",
        current_price=99.99,
        status=ProductStatus.ACTIVE,
        consecutive_failures=0,
    )
    test_session.add(product)
    test_session.commit()
    test_session.refresh(product)
    return product


@pytest.fixture
def failing_product(test_session, sample_store):
    """Create failing product for testing."""
    product = Product(
        url="https://test.example.com/product/2",
        store_domain=sample_store.domain,
        name="Failing Product",
        current_price=49.99,
        status=ProductStatus.ERROR,
        consecutive_failures=5,
    )
    test_session.add(product)
    test_session.commit()
    test_session.refresh(product)
    return product


# ===========================================
# FailureDetector Tests
# ===========================================


class TestFailureDetector:
    """Tests for FailureDetector class."""

    def test_classify_error_parse_failure(self):
        """Test classification of parse failure."""
        detector = FailureDetector()
        category = detector.classify_error(ScrapeErrorType.PARSE_FAILURE)
        assert category == FailureCategory.PARSE_FAILURE

    def test_classify_error_structure_change(self):
        """Test classification of structure change."""
        detector = FailureDetector()
        category = detector.classify_error(ScrapeErrorType.STRUCTURE_CHANGE)
        assert category == FailureCategory.STRUCTURE_CHANGE

    def test_classify_error_blocked(self):
        """Test classification of blocked error."""
        detector = FailureDetector()
        category = detector.classify_error(ScrapeErrorType.BLOCKED)
        assert category == FailureCategory.BLOCKED

    def test_classify_error_not_found(self):
        """Test classification of not found error."""
        detector = FailureDetector()
        category = detector.classify_error(ScrapeErrorType.NOT_FOUND)
        assert category == FailureCategory.NOT_FOUND

    def test_classify_error_none(self):
        """Test classification of None error."""
        detector = FailureDetector()
        category = detector.classify_error(None)
        assert category == FailureCategory.UNKNOWN

    def test_is_healable_parse_failure(self):
        """Test healable check for parse failure."""
        detector = FailureDetector()
        assert detector.is_healable(FailureCategory.PARSE_FAILURE)

    def test_is_healable_structure_change(self):
        """Test healable check for structure change."""
        detector = FailureDetector()
        assert detector.is_healable(FailureCategory.STRUCTURE_CHANGE)

    def test_is_healable_blocked(self):
        """Test healable check for blocked (not healable)."""
        detector = FailureDetector()
        assert not detector.is_healable(FailureCategory.BLOCKED)

    def test_is_healable_not_found(self):
        """Test healable check for not found (not healable)."""
        detector = FailureDetector()
        assert not detector.is_healable(FailureCategory.NOT_FOUND)

    def test_healable_categories_constant(self):
        """Test HEALABLE_CATEGORIES contains expected values."""
        assert FailureCategory.PARSE_FAILURE in HEALABLE_CATEGORIES
        assert FailureCategory.STRUCTURE_CHANGE in HEALABLE_CATEGORIES
        assert FailureCategory.PRICE_VALIDATION in HEALABLE_CATEGORIES
        assert FailureCategory.BLOCKED not in HEALABLE_CATEGORIES

    def test_analyze_product_not_found(self, test_session):
        """Test analyze_product with non-existent product."""
        detector = FailureDetector()
        result = detector.analyze_product(test_session, 99999)
        assert result is None

    def test_analyze_product_healthy(self, test_session, sample_product):
        """Test analyze_product with healthy product."""
        detector = FailureDetector()
        result = detector.analyze_product(test_session, sample_product.id)

        assert result is not None
        assert result.product_id == sample_product.id
        assert result.consecutive_failures == 0
        assert not result.needs_healing
        assert not result.needs_attention

    def test_analyze_product_failing(self, test_session, failing_product):
        """Test analyze_product with failing product."""
        # Add a scrape log with parse failure
        log = ScrapeLog(
            product_id=failing_product.id,
            success=False,
            error_type=ScrapeErrorType.PARSE_FAILURE,
            error_message="Failed to extract price",
        )
        test_session.add(log)
        test_session.commit()

        detector = FailureDetector()
        result = detector.analyze_product(test_session, failing_product.id)

        assert result is not None
        assert result.product_id == failing_product.id
        assert result.consecutive_failures == 5
        assert result.category == FailureCategory.PARSE_FAILURE
        assert result.needs_healing  # Above threshold and healable

    def test_record_failure_increments_count(self, test_session, sample_product):
        """Test that record_failure increments consecutive failures."""
        detector = FailureDetector()

        initial_failures = sample_product.consecutive_failures
        new_count = detector.record_failure(
            test_session,
            sample_product.id,
            ScrapeErrorType.PARSE_FAILURE,
        )

        assert new_count == initial_failures + 1

        # Refresh product to check update
        test_session.refresh(sample_product)
        assert sample_product.consecutive_failures == new_count

    def test_record_success_resets_count(self, test_session, failing_product):
        """Test that record_success resets consecutive failures."""
        detector = FailureDetector()

        assert failing_product.consecutive_failures > 0

        detector.record_success(test_session, failing_product.id)

        test_session.refresh(failing_product)
        assert failing_product.consecutive_failures == 0
        assert failing_product.status == ProductStatus.ACTIVE

    def test_get_products_needing_healing(self, test_session, failing_product):
        """Test get_products_needing_healing returns failing products."""
        # Add scrape log with healable error
        log = ScrapeLog(
            product_id=failing_product.id,
            success=False,
            error_type=ScrapeErrorType.PARSE_FAILURE,
        )
        test_session.add(log)
        test_session.commit()

        detector = FailureDetector()
        results = detector.get_products_needing_healing(test_session)

        assert len(results) >= 1
        product_ids = [r.product_id for r in results]
        assert failing_product.id in product_ids

    def test_get_failure_detector_singleton(self):
        """Test get_failure_detector returns singleton."""
        detector1 = get_failure_detector()
        detector2 = get_failure_detector()
        assert detector1 is detector2

    def test_default_failure_threshold(self):
        """Test default failure threshold value."""
        assert DEFAULT_FAILURE_THRESHOLD == 3


# ===========================================
# SelectorRegenerator Tests
# ===========================================


class TestSelectorRegenerator:
    """Tests for SelectorRegenerator class."""

    @pytest.fixture
    def mock_regenerator(self):
        """Create a mock regenerator that doesn't require API key."""
        with patch("src.healing.regenerator.settings") as mock_settings:
            mock_settings.primary_model = "test-model"
            mock_settings.openrouter_api_key = "test-key"
            with patch("src.healing.regenerator.OpenAIModel"):
                with patch("src.healing.regenerator.Agent"):
                    regenerator = SelectorRegenerator()
                    return regenerator

    def test_validate_selectors_valid(self, mock_regenerator):
        """Test validate_selectors with valid config."""
        selectors = {
            "price": {"css": [".price", "#price"]},
            "name": {"css": ["h1.title"]},
            "availability": {"css": [".stock-status"]},
        }

        config = mock_regenerator.validate_selectors(selectors)

        assert config is not None
        assert isinstance(config, SelectorConfig)
        assert config.price == [".price", "#price"]
        assert config.name == ["h1.title"]
        assert config.availability == [".stock-status"]

    def test_validate_selectors_missing_price(self, mock_regenerator):
        """Test validate_selectors with missing price."""
        selectors = {
            "name": {"css": ["h1.title"]},
            "availability": {"css": [".stock-status"]},
        }

        config = mock_regenerator.validate_selectors(selectors)
        assert config is None

    def test_validate_selectors_missing_name(self, mock_regenerator):
        """Test validate_selectors with missing name."""
        selectors = {
            "price": {"css": [".price"]},
            "availability": {"css": [".stock-status"]},
        }

        config = mock_regenerator.validate_selectors(selectors)
        assert config is None

    def test_validate_selectors_with_optional(self, mock_regenerator):
        """Test validate_selectors with optional fields."""
        selectors = {
            "price": {"css": [".price"]},
            "name": {"css": ["h1"]},
            "availability": {"css": [".stock"]},
            "image": {"css": ["img.product"]},
            "original_price": {"css": [".was-price"]},
            "wait_for": ".product-container",
            "json_ld": True,
        }

        config = mock_regenerator.validate_selectors(selectors)

        assert config is not None
        assert config.image == ["img.product"]
        assert config.original_price == [".was-price"]
        assert config.wait_for == ".product-container"
        assert config.json_ld is True

    def test_truncate_html_short(self, mock_regenerator):
        """Test _truncate_html with short HTML."""
        short_html = "<html><body>Hello</body></html>"
        result = mock_regenerator._truncate_html(short_html)

        assert result == short_html

    def test_truncate_html_long(self, mock_regenerator):
        """Test _truncate_html with long HTML."""
        # Create HTML longer than max_chars
        long_html = "<html><body>" + "x" * 60000 + "</body></html>"
        result = mock_regenerator._truncate_html(long_html, max_chars=50000)

        assert len(result) <= 50000

    def test_parse_response_valid_json(self, mock_regenerator):
        """Test _parse_response with valid JSON."""
        response = '{"selectors": {"price": {"css": [".price"]}}, "confidence": 0.9}'
        result = mock_regenerator._parse_response(response)

        assert result is not None
        assert "selectors" in result
        assert result["confidence"] == 0.9

    def test_parse_response_markdown_json(self, mock_regenerator):
        """Test _parse_response with markdown code block."""
        response = '''Some text
```json
{"selectors": {"price": {"css": [".price"]}}}
```
More text'''
        result = mock_regenerator._parse_response(response)

        assert result is not None
        assert "selectors" in result

    def test_parse_response_invalid(self, mock_regenerator):
        """Test _parse_response with invalid JSON."""
        response = "Not JSON at all"
        result = mock_regenerator._parse_response(response)

        assert result is None

    def test_regeneration_result_dataclass(self):
        """Test RegenerationResult dataclass."""
        result = RegenerationResult(
            success=True,
            domain="test.com",
            selectors={"price": {"css": [".price"]}},
            confidence=0.85,
        )

        assert result.success
        assert result.domain == "test.com"
        assert result.confidence == 0.85
        assert result.error is None


# ===========================================
# StoreHealthCalculator Tests
# ===========================================


class TestStoreHealthCalculator:
    """Tests for StoreHealthCalculator class."""

    def test_calculate_store_health_not_found(self, test_session):
        """Test calculate_store_health with non-existent store."""
        calculator = StoreHealthCalculator()
        result = calculator.calculate_store_health(test_session, "nonexistent.com")
        assert result is None

    def test_calculate_store_health_healthy(self, test_session, sample_store, sample_product):
        """Test calculate_store_health with healthy store."""
        # Add successful scrape logs
        for _ in range(5):
            log = ScrapeLog(
                product_id=sample_product.id,
                success=True,
            )
            test_session.add(log)
        test_session.commit()

        calculator = StoreHealthCalculator()
        health = calculator.calculate_store_health(test_session, sample_store.domain)

        assert health is not None
        assert health.domain == sample_store.domain
        assert health.total_products == 1
        assert health.is_healthy
        assert not health.needs_attention

    def test_calculate_store_health_unhealthy(self, test_session, sample_store, sample_product):
        """Test calculate_store_health with unhealthy store."""
        # Add failed scrape logs
        for _ in range(10):
            log = ScrapeLog(
                product_id=sample_product.id,
                success=False,
                error_type=ScrapeErrorType.PARSE_FAILURE,
            )
            test_session.add(log)
        test_session.commit()

        calculator = StoreHealthCalculator(min_scrapes=5)
        health = calculator.calculate_store_health(test_session, sample_store.domain)

        assert health is not None
        assert health.success_rate == 0.0
        assert not health.is_healthy

    def test_calculate_all_health(self, test_session, sample_store, sample_product):
        """Test calculate_all_health."""
        calculator = StoreHealthCalculator()
        report = calculator.calculate_all_health(test_session)

        assert report is not None
        assert report.total_stores >= 1
        assert len(report.store_health) >= 1

    def test_update_store_health(self, test_session, sample_store, sample_product):
        """Test update_store_health updates database."""
        calculator = StoreHealthCalculator()

        result = calculator.update_store_health(test_session, sample_store.domain)
        assert result

        test_session.refresh(sample_store)
        # Success rate should be updated (1.0 for no failures)
        assert sample_store.success_rate is not None

    def test_get_store_health_calculator_singleton(self):
        """Test get_store_health_calculator returns singleton."""
        calc1 = get_store_health_calculator()
        calc2 = get_store_health_calculator()
        assert calc1 is calc2


# ===========================================
# SelfHealingService Tests
# ===========================================


class TestSelfHealingService:
    """Tests for SelfHealingService class."""

    def test_healing_attempt_dataclass(self):
        """Test HealingAttempt dataclass."""
        attempt = HealingAttempt(
            product_id=1,
            domain="test.com",
            success=True,
            attempt_number=1,
        )

        assert attempt.product_id == 1
        assert attempt.success
        assert attempt.timestamp is not None

    def test_healing_report_dataclass(self):
        """Test HealingReport dataclass."""
        report = HealingReport()

        assert report.total_products_checked == 0
        assert report.products_healed == 0
        assert report.attempts == []

    @pytest.mark.asyncio
    async def test_run_healing_cycle_no_products(self, test_session, sample_store, sample_product):
        """Test run_healing_cycle with no products needing healing."""
        # Mock the dependencies
        mock_detector = MagicMock()
        mock_detector.get_products_needing_healing.return_value = []

        with patch("src.healing.regenerator.settings") as mock_settings:
            mock_settings.primary_model = "test-model"
            mock_settings.openrouter_api_key = "test-key"
            with patch("src.healing.regenerator.OpenAIModel"):
                with patch("src.healing.regenerator.Agent"):
                    mock_regenerator = SelectorRegenerator()

        mock_scraper = MagicMock()

        service = SelfHealingService(
            detector=mock_detector,
            regenerator=mock_regenerator,
            scraper=mock_scraper,
        )
        report = await service.run_healing_cycle(test_session)

        assert report.total_products_checked == 0
        assert report.products_healed == 0

    def test_reset_healing_attempts(self):
        """Test reset_healing_attempts clears counters."""
        # Mock the dependencies
        mock_detector = MagicMock()

        with patch("src.healing.regenerator.settings") as mock_settings:
            mock_settings.primary_model = "test-model"
            mock_settings.openrouter_api_key = "test-key"
            with patch("src.healing.regenerator.OpenAIModel"):
                with patch("src.healing.regenerator.Agent"):
                    mock_regenerator = SelectorRegenerator()

        mock_scraper = MagicMock()

        service = SelfHealingService(
            detector=mock_detector,
            regenerator=mock_regenerator,
            scraper=mock_scraper,
        )

        # Set some attempts
        service._healing_attempts[1] = 3
        service._healing_attempts[2] = 2

        # Reset specific
        service.reset_healing_attempts(1)
        assert 1 not in service._healing_attempts
        assert 2 in service._healing_attempts

        # Reset all
        service.reset_healing_attempts()
        assert len(service._healing_attempts) == 0


# ===========================================
# Integration Tests
# ===========================================


class TestHealingIntegration:
    """Integration tests for healing module."""

    def test_detector_to_service_flow(self, test_session, sample_store, failing_product):
        """Test flow from detector to service."""
        # Add scrape log
        log = ScrapeLog(
            product_id=failing_product.id,
            success=False,
            error_type=ScrapeErrorType.PARSE_FAILURE,
        )
        test_session.add(log)
        test_session.commit()

        # Detect failing products
        detector = FailureDetector()
        analyses = detector.get_products_needing_healing(test_session)

        assert len(analyses) >= 1

        # Check analysis
        analysis = next(a for a in analyses if a.product_id == failing_product.id)
        assert analysis.needs_healing
        assert analysis.category == FailureCategory.PARSE_FAILURE

    def test_health_calculation_after_failures(
        self, test_session, sample_store, sample_product
    ):
        """Test health calculation reflects failures."""
        # Add some failures
        for _ in range(10):
            log = ScrapeLog(
                product_id=sample_product.id,
                success=False,
                error_type=ScrapeErrorType.PARSE_FAILURE,
            )
            test_session.add(log)
        test_session.commit()

        calculator = StoreHealthCalculator(min_scrapes=5)
        health = calculator.calculate_store_health(test_session, sample_store.domain)

        assert health is not None
        assert health.success_rate < 0.5  # Should be unhealthy
