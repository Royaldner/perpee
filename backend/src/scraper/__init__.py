"""
Perpee scraper module.

This module provides web scraping capabilities for extracting product data
from Canadian online retailers.

Main components:
- ScraperEngine: Main scraper with waterfall extraction
- ProductData: Extracted product data model
- ScrapeResult: Result of scrape operation
"""

from .block_detection import BlockDetectionResult, BlockType, detect_block
from .engine import (
    ScraperConfig,
    ScraperEngine,
    ScrapeResult,
    get_scraper_engine,
    scrape_product,
)
from .rate_limiter import (
    RateLimiter,
    TokenBucket,
    configure_rate_limiter,
    create_crawl4ai_rate_limiter,
    get_default_crawl4ai_rate_limiter,
    get_rate_limiter,
)
from .retry import ErrorCategory, RetryConfig, RetryHandler, RetryResult
from .robots import (
    RobotsHandler,
    RobotsResult,
    create_robots_aware_config,
    get_default_robots_config,
    get_robots_handler,
    is_allowed,
)
from .sanitization import (
    normalize_price,
    sanitize_image_url,
    sanitize_product_name,
    sanitize_scraped_content,
    sanitize_text,
    sanitize_xss,
    strip_html_tags,
    validate_price,
)
from .strategies import (
    CssSelectorStrategy,
    JsonLdStrategy,
    LlmExtractionStrategy,
    ProductData,
    XPathStrategy,
)
from .user_agent import UserAgentManager, get_browser_headers, get_user_agent_manager
from .validators import (
    block_private_ip,
    check_domain_whitelist,
    extract_domain,
    is_private_ip,
    validate_url_complete,
    validate_url_format,
    validate_whitelisted_url,
)

__all__ = [
    # Block detection
    "BlockDetectionResult",
    "BlockType",
    "detect_block",
    # Engine
    "ScrapeResult",
    "ScraperConfig",
    "ScraperEngine",
    "get_scraper_engine",
    "scrape_product",
    # Rate limiting
    "RateLimiter",
    "TokenBucket",
    "configure_rate_limiter",
    "create_crawl4ai_rate_limiter",
    "get_default_crawl4ai_rate_limiter",
    "get_rate_limiter",
    # Retry
    "ErrorCategory",
    "RetryConfig",
    "RetryHandler",
    "RetryResult",
    # Robots
    "RobotsHandler",
    "RobotsResult",
    "create_robots_aware_config",
    "get_default_robots_config",
    "get_robots_handler",
    "is_allowed",
    # Sanitization
    "normalize_price",
    "sanitize_image_url",
    "sanitize_product_name",
    "sanitize_scraped_content",
    "sanitize_text",
    "sanitize_xss",
    "strip_html_tags",
    "validate_price",
    # Strategies
    "CssSelectorStrategy",
    "JsonLdStrategy",
    "LlmExtractionStrategy",
    "ProductData",
    "XPathStrategy",
    # User agent
    "UserAgentManager",
    "get_browser_headers",
    "get_user_agent_manager",
    # Validators
    "block_private_ip",
    "check_domain_whitelist",
    "extract_domain",
    "is_private_ip",
    "validate_url_complete",
    "validate_url_format",
    "validate_whitelisted_url",
]
