"""
Phase 1 tests - Foundation verification.
Tests database models, core utilities, and security functions.
"""

import pytest

from config.settings import Settings
from src.core.constants import P0_STORES, STORE_CATEGORIES
from src.core.exceptions import (
    InvalidURLError,
    PerpeeError,
    PrivateIPError,
    UnsupportedStoreError,
)
from src.core.security import (
    extract_domain,
    is_private_ip,
    is_whitelisted_store,
    normalize_price,
    sanitize_html,
    sanitize_product_name,
    sanitize_text,
    validate_price,
    validate_url,
    validate_whitelisted_url,
)
from src.database.models import (
    Alert,
    AlertType,
    ExtractionStrategy,
    PriceHistory,
    Product,
    ProductStatus,
    Store,
)


class TestSettings:
    """Test application settings."""

    def test_settings_load(self):
        """Test that settings load successfully."""
        settings = Settings()
        assert settings is not None
        assert settings.database_url is not None

    def test_default_values(self):
        """Test default setting values."""
        settings = Settings()
        assert settings.daily_token_limit == 100_000
        assert settings.max_scrapes_per_minute == 10
        assert settings.conversation_window_size == 15


class TestDatabaseModels:
    """Test database model definitions."""

    def test_product_status_enum(self):
        """Test ProductStatus enum values."""
        assert ProductStatus.ACTIVE.value == "active"
        assert ProductStatus.PAUSED.value == "paused"
        assert ProductStatus.ERROR.value == "error"
        assert ProductStatus.NEEDS_ATTENTION.value == "needs_attention"
        assert ProductStatus.PRICE_UNAVAILABLE.value == "price_unavailable"
        assert ProductStatus.ARCHIVED.value == "archived"

    def test_alert_type_enum(self):
        """Test AlertType enum values."""
        assert AlertType.TARGET_PRICE.value == "target_price"
        assert AlertType.PERCENT_DROP.value == "percent_drop"
        assert AlertType.ANY_CHANGE.value == "any_change"
        assert AlertType.BACK_IN_STOCK.value == "back_in_stock"

    def test_extraction_strategy_enum(self):
        """Test ExtractionStrategy enum values."""
        assert ExtractionStrategy.JSON_LD.value == "json_ld"
        assert ExtractionStrategy.CSS_SELECTOR.value == "css_selector"
        assert ExtractionStrategy.XPATH.value == "xpath"
        assert ExtractionStrategy.LLM.value == "llm"

    def test_store_model(self):
        """Test Store model instantiation."""
        store = Store(
            domain="amazon.ca",
            name="Amazon Canada",
            is_whitelisted=True,
            is_active=True,
            rate_limit_rpm=5,
        )
        assert store.domain == "amazon.ca"
        assert store.name == "Amazon Canada"
        assert store.is_whitelisted is True

    def test_product_model(self):
        """Test Product model instantiation."""
        product = Product(
            url="https://amazon.ca/dp/B123456",
            store_domain="amazon.ca",
            name="Test Product",
            current_price=99.99,
            currency="CAD",
            in_stock=True,
        )
        assert product.url == "https://amazon.ca/dp/B123456"
        assert product.store_domain == "amazon.ca"
        assert product.current_price == 99.99
        assert product.status == ProductStatus.ACTIVE

    def test_alert_model(self):
        """Test Alert model instantiation."""
        alert = Alert(
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=50.00,
            min_change_threshold=1.0,
        )
        assert alert.alert_type == AlertType.TARGET_PRICE
        assert alert.target_value == 50.00
        assert alert.is_active is True
        assert alert.is_triggered is False

    def test_price_history_model(self):
        """Test PriceHistory model instantiation."""
        history = PriceHistory(
            product_id=1,
            price=99.99,
            original_price=129.99,
            in_stock=True,
        )
        assert history.price == 99.99
        assert history.original_price == 129.99


class TestURLValidation:
    """Test URL validation functions."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = validate_url("https://amazon.ca/product/123")
        assert url == "https://amazon.ca/product/123"

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        url = validate_url("http://amazon.ca/product/123")
        assert url == "http://amazon.ca/product/123"

    def test_url_with_query_params(self):
        """Test URL with query parameters."""
        url = validate_url("https://amazon.ca/product?id=123&ref=home")
        assert "id=123" in url

    def test_invalid_scheme(self):
        """Test invalid URL scheme."""
        with pytest.raises(InvalidURLError):
            validate_url("ftp://amazon.ca/file")

    def test_empty_url(self):
        """Test empty URL."""
        with pytest.raises(InvalidURLError):
            validate_url("")

    def test_no_domain(self):
        """Test URL without domain."""
        with pytest.raises(InvalidURLError):
            validate_url("https:///path")


class TestDomainExtraction:
    """Test domain extraction function."""

    def test_extract_simple_domain(self):
        """Test simple domain extraction."""
        assert extract_domain("https://amazon.ca/product") == "amazon.ca"

    def test_extract_www_domain(self):
        """Test www prefix removal."""
        assert extract_domain("https://www.amazon.ca/product") == "amazon.ca"

    def test_extract_domain_with_port(self):
        """Test domain with port."""
        assert extract_domain("https://amazon.ca:443/product") == "amazon.ca"

    def test_extract_subdomain(self):
        """Test subdomain handling."""
        assert extract_domain("https://shop.example.com/product") == "shop.example.com"


class TestWhitelist:
    """Test whitelist checking."""

    def test_whitelisted_store(self):
        """Test whitelisted store detection."""
        assert is_whitelisted_store("https://amazon.ca/product") is True
        assert is_whitelisted_store("https://bestbuy.ca/product") is True
        assert is_whitelisted_store("https://walmart.ca/product") is True

    def test_non_whitelisted_store(self):
        """Test non-whitelisted store detection."""
        assert is_whitelisted_store("https://unknown-store.com/product") is False

    def test_validate_whitelisted_url(self):
        """Test combined validation and whitelist check."""
        url = validate_whitelisted_url("https://amazon.ca/product")
        assert url == "https://amazon.ca/product"

    def test_validate_non_whitelisted_url(self):
        """Test rejection of non-whitelisted URL."""
        with pytest.raises(UnsupportedStoreError):
            validate_whitelisted_url("https://unknown-store.com/product")


class TestSSRFProtection:
    """Test SSRF protection functions."""

    def test_private_ip_localhost(self):
        """Test localhost detection."""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.0.0.100") is True

    def test_private_ip_10_range(self):
        """Test 10.x.x.x range detection."""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True

    def test_private_ip_172_range(self):
        """Test 172.16.x.x range detection."""
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True

    def test_private_ip_192_range(self):
        """Test 192.168.x.x range detection."""
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True

    def test_public_ip(self):
        """Test public IP is not flagged."""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False


class TestContentSanitization:
    """Test content sanitization functions."""

    def test_sanitize_html_tags(self):
        """Test HTML tag removal."""
        html = "<p>Hello <b>World</b></p>"
        assert sanitize_html(html) == "Hello World"

    def test_sanitize_script_tags(self):
        """Test script tag removal."""
        html = "<script>alert('xss')</script>Hello"
        result = sanitize_html(html)
        assert "script" not in result.lower()
        assert "Hello" in result

    def test_sanitize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    World\n\nTest"
        assert sanitize_text(text) == "Hello World Test"

    def test_sanitize_product_name(self):
        """Test product name sanitization."""
        name = "<b>Test Product!!!</b> - Buy Now"
        result = sanitize_product_name(name)
        assert "<b>" not in result
        assert "Test Product" in result


class TestPriceNormalization:
    """Test price normalization functions."""

    def test_simple_price(self):
        """Test simple price parsing."""
        assert normalize_price("99.99") == 99.99

    def test_price_with_dollar_sign(self):
        """Test price with $ symbol."""
        assert normalize_price("$99.99") == 99.99

    def test_price_with_cad(self):
        """Test price with CAD prefix."""
        assert normalize_price("CAD 99.99") == 99.99

    def test_price_with_commas(self):
        """Test price with thousand separators."""
        assert normalize_price("$1,234.56") == 1234.56

    def test_invalid_price(self):
        """Test invalid price returns None."""
        assert normalize_price("not a price") is None
        assert normalize_price("") is None

    def test_price_validation(self):
        """Test price range validation."""
        assert validate_price(99.99) is True
        assert validate_price(0.01) is True
        assert validate_price(0.00) is False
        assert validate_price(-10.00) is False


class TestStoreConstants:
    """Test store constants."""

    def test_p0_stores_count(self):
        """Test P0 stores list has expected count."""
        assert len(P0_STORES) == 16

    def test_store_categories(self):
        """Test store categories are defined."""
        assert "general" in STORE_CATEGORIES
        assert "electronics" in STORE_CATEGORIES
        assert "grocery" in STORE_CATEGORIES
        assert "pharmacy" in STORE_CATEGORIES
        assert "home" in STORE_CATEGORIES

    def test_amazon_in_p0(self):
        """Test Amazon is in P0 stores."""
        assert "amazon.ca" in P0_STORES

    def test_all_categories_stores_in_p0(self):
        """Test all category stores are in P0 list."""
        for category, stores in STORE_CATEGORIES.items():
            for store in stores:
                assert store in P0_STORES, f"{store} from {category} not in P0_STORES"


class TestExceptions:
    """Test custom exception classes."""

    def test_perpee_error(self):
        """Test base PerpeeError."""
        error = PerpeeError("Test error", {"key": "value"})
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    def test_invalid_url_error(self):
        """Test InvalidURLError."""
        error = InvalidURLError("Bad URL")
        assert isinstance(error, PerpeeError)

    def test_private_ip_error(self):
        """Test PrivateIPError."""
        error = PrivateIPError("SSRF detected", {"ip": "127.0.0.1"})
        assert "SSRF detected" in str(error)
        assert error.details["ip"] == "127.0.0.1"


class TestStoreSeedData:
    """Test store seed data."""

    def test_seed_data_import(self):
        """Test seed data imports correctly."""
        from config.stores_seed import P0_STORES as SEED_STORES

        assert len(SEED_STORES) == 16

    def test_all_stores_have_selectors(self):
        """Test all stores have selectors defined."""
        from config.stores_seed import P0_STORES as SEED_STORES

        for store in SEED_STORES:
            assert "selectors" in store
            assert "price" in store["selectors"]
            assert "name" in store["selectors"]

    def test_get_store_config(self):
        """Test get_store_config function."""
        from config.stores_seed import get_store_config

        config = get_store_config("amazon.ca")
        assert config is not None
        assert config["name"] == "Amazon Canada"

    def test_get_store_config_not_found(self):
        """Test get_store_config returns None for unknown store."""
        from config.stores_seed import get_store_config

        config = get_store_config("unknown.com")
        assert config is None

    def test_store_supports_json_ld(self):
        """Test JSON-LD support detection."""
        from config.stores_seed import store_supports_json_ld

        assert store_supports_json_ld("amazon.ca") is True
        assert store_supports_json_ld("bestbuy.ca") is True
