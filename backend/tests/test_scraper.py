"""
Tests for the scraper module.

Tests extraction strategies, rate limiting, block detection, and more.
"""

import time

import pytest

from src.core.security import normalize_price
from src.database.models import ExtractionStrategy
from src.scraper.block_detection import BlockType, detect_block
from src.scraper.rate_limiter import RateLimiter, RateLimitState
from src.scraper.retry import ErrorCategory, RetryConfig, categorize_error
from src.scraper.strategies import (
    CssSelectorStrategy,
    JsonLdStrategy,
    ProductData,
)
from src.scraper.user_agent import UserAgentManager

# ===========================================
# JSON-LD Strategy Tests
# ===========================================


class TestJsonLdStrategy:
    """Tests for JSON-LD extraction strategy."""

    def test_extract_basic_product(self):
        """Test extraction of basic product JSON-LD."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Test Product",
                "brand": {"@type": "Brand", "name": "TestBrand"},
                "offers": {
                    "@type": "Offer",
                    "price": "99.99",
                    "priceCurrency": "CAD",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is not None
        assert result.name == "Test Product"
        assert result.price == 99.99
        assert result.currency == "CAD"
        assert result.brand == "TestBrand"
        assert result.in_stock is True
        assert result.strategy_used == ExtractionStrategy.JSON_LD

    def test_extract_product_with_graph(self):
        """Test extraction from @graph structure."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "WebSite",
                        "name": "Test Store"
                    },
                    {
                        "@type": "Product",
                        "name": "Graph Product",
                        "offers": {
                            "@type": "Offer",
                            "price": "49.99"
                        }
                    }
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is not None
        assert result.name == "Graph Product"
        assert result.price == 49.99

    def test_extract_aggregate_offer(self):
        """Test extraction with AggregateOffer."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "Multi-Price Product",
                "offers": {
                    "@type": "AggregateOffer",
                    "lowPrice": "29.99",
                    "highPrice": "59.99",
                    "priceCurrency": "CAD"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is not None
        assert result.price == 29.99  # Should use lowPrice

    def test_extract_out_of_stock(self):
        """Test detection of out of stock status."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "Out of Stock Product",
                "offers": {
                    "@type": "Offer",
                    "price": "99.99",
                    "availability": "https://schema.org/OutOfStock"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is not None
        assert result.in_stock is False

    def test_extract_no_jsonld(self):
        """Test with no JSON-LD present."""
        html = "<html><body><h1>Product</h1></body></html>"
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is None

    def test_extract_invalid_json(self):
        """Test with invalid JSON in script tag."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            { invalid json }
            </script>
        </head>
        <body></body>
        </html>
        """
        strategy = JsonLdStrategy()
        result = strategy.extract(html)

        assert result is None


# ===========================================
# CSS Selector Strategy Tests
# ===========================================


class TestCssSelectorStrategy:
    """Tests for CSS selector extraction strategy."""

    def test_extract_with_selectors(self):
        """Test extraction with store selectors."""
        html = """
        <html>
        <body>
            <h1 id="product-title">Test CSS Product</h1>
            <span class="price">$149.99</span>
            <span class="original-price">$199.99</span>
            <button class="add-to-cart">Add to Cart</button>
            <img class="product-image" src="https://example.com/image.jpg">
        </body>
        </html>
        """
        selectors = {
            "name": {"css": ["#product-title", "h1"]},
            "price": {"css": [".price"]},
            "original_price": {"css": [".original-price"]},
            "availability": {
                "css": [".add-to-cart"],
                "in_stock_patterns": ["add to cart"],
            },
            "image": {"css": [".product-image"]},
        }

        strategy = CssSelectorStrategy()
        result = strategy.extract(html, selectors)

        assert result is not None
        assert result.name == "Test CSS Product"
        assert result.price == 149.99
        assert result.original_price == 199.99
        assert result.in_stock is True
        assert result.image_url == "https://example.com/image.jpg"
        assert result.strategy_used == ExtractionStrategy.CSS_SELECTOR

    def test_extract_multiple_selectors_fallback(self):
        """Test fallback to secondary selector."""
        html = """
        <html>
        <body>
            <div class="product-name">Fallback Product</div>
            <span class="current-price">$79.99</span>
        </body>
        </html>
        """
        selectors = {
            "name": {"css": ["#does-not-exist", ".product-name"]},
            "price": {"css": ["#no-price", ".current-price"]},
        }

        strategy = CssSelectorStrategy()
        result = strategy.extract(html, selectors)

        assert result is not None
        assert result.name == "Fallback Product"
        assert result.price == 79.99

    def test_extract_no_selectors(self):
        """Test with no selectors provided."""
        html = "<html><body><h1>Product</h1></body></html>"
        strategy = CssSelectorStrategy()
        result = strategy.extract(html, None)

        assert result is None

    def test_extract_relative_image_url(self):
        """Test handling of protocol-relative image URL."""
        html = """
        <html>
        <body>
            <h1 class="title">Product</h1>
            <span class="price">$10.00</span>
            <img class="img" src="//cdn.example.com/image.jpg">
        </body>
        </html>
        """
        selectors = {
            "name": {"css": [".title"]},
            "price": {"css": [".price"]},
            "image": {"css": [".img"]},
        }

        strategy = CssSelectorStrategy()
        result = strategy.extract(html, selectors)

        assert result is not None
        assert result.image_url == "https://cdn.example.com/image.jpg"


# ===========================================
# Rate Limiter Tests
# ===========================================


class TestRateLimiter:
    """Tests for rate limiting."""

    def test_rate_limit_state_basic(self):
        """Test basic rate limit state."""
        state = RateLimitState(limit=5)

        # Should allow initial requests
        for _ in range(5):
            assert state.can_request()
            state.record_request()

        # Should block next request
        assert not state.can_request()

    def test_rate_limit_window_cleanup(self):
        """Test that old requests are cleaned up."""
        state = RateLimitState(limit=2, window_seconds=1)

        state.record_request()
        state.record_request()
        assert not state.can_request()

        # Wait for window to pass
        time.sleep(1.1)
        state.clean_old_requests()

        assert state.can_request()

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter acquire."""
        limiter = RateLimiter(global_limit=5, window_seconds=60)
        limiter.set_store_limit("test.com", 3)

        # Should allow 3 requests (store limit)
        for _ in range(3):
            await limiter.acquire("test.com")

        # Next request should wait
        assert not limiter.check("test.com")

    def test_rate_limiter_stats(self):
        """Test rate limiter statistics."""
        limiter = RateLimiter(global_limit=10)

        # Make some requests manually
        limiter._global.record_request()
        limiter._stores["test.com"].record_request()

        stats = limiter.get_stats()

        assert stats["global"]["current"] == 1
        assert "test.com" in stats["stores"]


# ===========================================
# Block Detection Tests
# ===========================================


class TestBlockDetection:
    """Tests for block detection."""

    def test_detect_captcha(self):
        """Test CAPTCHA detection."""
        html = """
        <html>
        <body>
            <div class="g-recaptcha">Please verify you are human</div>
        </body>
        </html>
        """
        result = detect_block(html)

        assert result.is_blocked
        assert result.block_type == BlockType.CAPTCHA

    def test_detect_rate_limit_429(self):
        """Test rate limit detection from 429 status."""
        result = detect_block("<html></html>", status_code=429)

        assert result.is_blocked
        assert result.block_type == BlockType.RATE_LIMITED

    def test_detect_not_found(self):
        """Test 404 detection."""
        result = detect_block("<html><body>Page not found</body></html>", status_code=404)

        assert result.is_blocked
        assert result.block_type == BlockType.NOT_FOUND

    def test_detect_empty_response(self):
        """Test empty response detection."""
        result = detect_block("", status_code=200)

        assert result.is_blocked
        assert result.block_type == BlockType.EMPTY_RESPONSE

    def test_detect_bot_detection(self):
        """Test bot detection patterns."""
        html = """
        <html>
        <body>
            <h1>Pardon Our Interruption</h1>
            <p>We have detected unusual traffic from your network.</p>
        </body>
        </html>
        """
        result = detect_block(html)

        assert result.is_blocked
        assert result.block_type == BlockType.BOT_DETECTION

    def test_no_block_normal_page(self):
        """Test that normal page is not flagged as blocked."""
        html = """
        <html>
        <body>
            <h1>Product Name</h1>
            <span class="price">$99.99</span>
            <button>Add to Cart</button>
        </body>
        </html>
        """
        result = detect_block(html, status_code=200)

        assert not result.is_blocked


# ===========================================
# Retry Logic Tests
# ===========================================


class TestRetryLogic:
    """Tests for retry logic."""

    def test_categorize_timeout_error(self):
        """Test categorization of timeout error."""
        from src.core.exceptions import TimeoutError

        error = TimeoutError("Request timed out")
        category = categorize_error(error)

        assert category == ErrorCategory.TIMEOUT

    def test_categorize_network_error(self):
        """Test categorization of network error."""
        from src.core.exceptions import NetworkError

        error = NetworkError("Connection refused")
        category = categorize_error(error)

        assert category == ErrorCategory.NETWORK

    def test_categorize_not_found(self):
        """Test categorization of 404 error."""
        from src.core.exceptions import NotFoundError

        error = NotFoundError("Page not found")
        category = categorize_error(error)

        assert category == ErrorCategory.NOT_FOUND

    def test_retry_config_should_retry(self):
        """Test retry decision logic."""
        config = RetryConfig(max_retries=3)

        # Should retry network errors
        assert config.should_retry(ErrorCategory.NETWORK, 0)
        assert config.should_retry(ErrorCategory.NETWORK, 2)
        assert not config.should_retry(ErrorCategory.NETWORK, 3)

        # Should not retry 404s
        assert not config.should_retry(ErrorCategory.NOT_FOUND, 0)

        # Forbidden gets 1 retry
        assert config.should_retry(ErrorCategory.FORBIDDEN, 0)
        assert not config.should_retry(ErrorCategory.FORBIDDEN, 1)


# ===========================================
# User Agent Tests
# ===========================================


class TestUserAgentManager:
    """Tests for user agent management."""

    def test_get_user_agent(self):
        """Test getting user agent."""
        manager = UserAgentManager()
        ua = manager.get_user_agent("test.com")

        assert ua is not None
        assert "Mozilla" in ua

    def test_rotate_user_agent(self):
        """Test user agent rotation."""
        manager = UserAgentManager(user_agents=["UA1", "UA2", "UA3"])

        ua1 = manager.get_user_agent("test.com")
        manager.rotate("test.com")
        ua2 = manager.get_user_agent("test.com")

        assert ua1 != ua2

    def test_report_failure_rotation(self):
        """Test that failures trigger rotation."""
        manager = UserAgentManager(user_agents=["UA1", "UA2"])

        # Report 3 failures
        for _ in range(3):
            manager.report_failure("test.com")

        # Should have rotated
        stats = manager.get_stats("test.com")
        assert stats["failures"][0] == 3

    def test_get_headers(self):
        """Test getting complete headers."""
        manager = UserAgentManager()
        headers = manager.get_headers("test.com")

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers


# ===========================================
# Price Normalization Tests
# ===========================================


class TestPriceNormalization:
    """Tests for price parsing and normalization."""

    def test_normalize_simple_price(self):
        """Test simple price normalization."""
        assert normalize_price("$99.99") == 99.99
        assert normalize_price("99.99") == 99.99

    def test_normalize_price_with_comma(self):
        """Test price with thousand separator."""
        assert normalize_price("$1,234.56") == 1234.56
        assert normalize_price("1,234.56") == 1234.56

    def test_normalize_price_with_currency(self):
        """Test price with currency text."""
        assert normalize_price("CAD $99.99") == 99.99
        assert normalize_price("CAD 99.99") == 99.99

    def test_normalize_price_range(self):
        """Test price range (should return lower)."""
        assert normalize_price("$29.99 - $49.99") == 29.99

    def test_normalize_invalid_price(self):
        """Test invalid price returns None."""
        assert normalize_price("") is None
        assert normalize_price("abc") is None
        assert normalize_price("free") is None

    def test_normalize_out_of_range_price(self):
        """Test out of range prices."""
        assert normalize_price("$0.001") is None  # Too low
        assert normalize_price("$10000000") is None  # Too high


# ===========================================
# Integration Tests (mock-based)
# ===========================================


class TestScraperIntegration:
    """Integration tests for scraper module."""

    def test_product_data_model(self):
        """Test ProductData dataclass."""
        product = ProductData(
            name="Test Product",
            price=99.99,
            currency="CAD",
            in_stock=True,
            strategy_used=ExtractionStrategy.JSON_LD,
        )

        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.currency == "CAD"
        assert product.in_stock is True

    def test_amazon_selectors_structure(self):
        """Test that Amazon selectors have expected structure."""
        from config.stores_seed import get_store_config

        config = get_store_config("amazon.ca")

        assert config is not None
        assert "selectors" in config
        assert "price" in config["selectors"]
        assert "name" in config["selectors"]
        assert "css" in config["selectors"]["price"]

    def test_all_p0_stores_have_selectors(self):
        """Test that all P0 stores have selector configurations."""
        from config.stores_seed import get_store_config
        from src.core.constants import P0_STORES

        for domain in P0_STORES:
            config = get_store_config(domain)
            assert config is not None, f"Missing config for {domain}"
            assert "selectors" in config, f"Missing selectors for {domain}"
            assert "price" in config["selectors"], f"Missing price selector for {domain}"
            assert "name" in config["selectors"], f"Missing name selector for {domain}"
