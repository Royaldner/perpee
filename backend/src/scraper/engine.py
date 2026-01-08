"""
Main scraper engine for Perpee.
Implements waterfall extraction with Crawl4AI.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

from config.stores_seed import get_store_config, get_store_selectors
from src.core.constants import (
    MAX_CONCURRENT_BROWSERS,
    MEMORY_THRESHOLD_PERCENT,
    OPERATION_TIMEOUT,
    PAGE_LOAD_DELAY,
    REQUEST_TIMEOUT,
)
from src.core.exceptions import (
    BlockedError,
    NetworkError,
    NotFoundError,
    ParseError,
    RobotsBlockedError,
    TimeoutError,
)
from src.core.security import extract_domain, resolve_and_validate_url, validate_url
from src.database.models import ExtractionStrategy, ScrapeErrorType

from .block_detection import BlockType, detect_block
from .rate_limiter import RateLimiter, get_rate_limiter
from .retry import RetryConfig, RetryHandler
from .robots import RobotsHandler, get_robots_handler
from .strategies import (
    CssSelectorStrategy,
    JsonLdStrategy,
    LlmExtractionStrategy,
    ProductData,
    XPathStrategy,
)
from .user_agent import UserAgentManager, get_user_agent_manager


@dataclass
class ScrapeResult:
    """Result of a scrape operation."""

    success: bool
    product: ProductData | None = None
    url: str = ""
    domain: str = ""
    strategy_used: ExtractionStrategy | None = None
    response_time_ms: int = 0
    error_type: ScrapeErrorType | None = None
    error_message: str | None = None
    attempts: int = 1
    status_code: int | None = None


@dataclass
class ScraperConfig:
    """Configuration for scraper engine."""

    request_timeout: int = REQUEST_TIMEOUT
    operation_timeout: int = OPERATION_TIMEOUT
    page_load_delay: float = PAGE_LOAD_DELAY
    max_concurrent: int = MAX_CONCURRENT_BROWSERS
    memory_threshold: float = MEMORY_THRESHOLD_PERCENT
    respect_robots: bool = True
    enable_retries: bool = True
    stealth_mode: bool = True


class ScraperEngine:
    """
    Main scraper engine for product data extraction.

    Features:
    - Waterfall extraction (JSON-LD -> CSS -> XPath -> LLM)
    - Rate limiting (per-store and global)
    - Retry with exponential backoff
    - Block detection and evasion
    - robots.txt compliance
    """

    def __init__(
        self,
        config: ScraperConfig | None = None,
        rate_limiter: RateLimiter | None = None,
        robots_handler: RobotsHandler | None = None,
        ua_manager: UserAgentManager | None = None,
        llm_client: Any = None,
    ):
        """
        Initialize scraper engine.

        Args:
            config: Scraper configuration
            rate_limiter: Rate limiter instance
            robots_handler: Robots.txt handler
            ua_manager: User agent manager
            llm_client: Optional LLM client for LLM extraction
        """
        self.config = config or ScraperConfig()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.robots_handler = robots_handler or get_robots_handler()
        self.ua_manager = ua_manager or get_user_agent_manager()
        self.llm_client = llm_client

        # Initialize extraction strategies
        self._strategies = [
            JsonLdStrategy(),
            CssSelectorStrategy(),
            XPathStrategy(),
            LlmExtractionStrategy(llm_client),
        ]

        # Retry handler
        self._retry_handler = RetryHandler(
            RetryConfig(max_retries=3, jitter=0.2)
        )

        # Configure MemoryAdaptiveDispatcher for batch operations
        # Per plan: Max 3 concurrent browsers, 70% memory threshold
        self._dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=self.config.memory_threshold,
            max_session_permit=self.config.max_concurrent,
        )

        # Browser semaphore for single-URL operations
        self._browser_semaphore = asyncio.Semaphore(self.config.max_concurrent)

    async def scrape(
        self,
        url: str,
        validate_ssrf: bool = True,
        use_cache: bool = False,
    ) -> ScrapeResult:
        """
        Scrape product data from URL.

        Args:
            url: Product page URL
            validate_ssrf: Whether to validate against SSRF
            use_cache: Whether to use cached pages

        Returns:
            ScrapeResult with extracted data or error
        """
        start_time = time.time()
        domain = ""

        try:
            # Validate URL
            if validate_ssrf:
                url = resolve_and_validate_url(url)
            else:
                url = validate_url(url)

            domain = extract_domain(url)

            # Check robots.txt
            if self.config.respect_robots:
                robots_result = await self.robots_handler.check(url)
                if not robots_result.allowed:
                    return ScrapeResult(
                        success=False,
                        url=url,
                        domain=domain,
                        error_type=ScrapeErrorType.ROBOTS_BLOCKED,
                        error_message=f"Blocked by robots.txt: {robots_result.reason}",
                        response_time_ms=self._elapsed_ms(start_time),
                    )

            # Configure store rate limit
            store_config = get_store_config(domain)
            if store_config:
                self.rate_limiter.set_store_limit(
                    domain, store_config.get("rate_limit_rpm", 10)
                )

            # Acquire rate limit
            await self.rate_limiter.acquire(domain)

            # Execute scrape with retries
            if self.config.enable_retries:
                result = await self._scrape_with_retry(url, domain, use_cache)
            else:
                result = await self._do_scrape(url, domain, use_cache)

            result.response_time_ms = self._elapsed_ms(start_time)
            return result

        except Exception as e:
            error_type = self._categorize_error(e)
            return ScrapeResult(
                success=False,
                url=url,
                domain=domain,
                error_type=error_type,
                error_message=str(e),
                response_time_ms=self._elapsed_ms(start_time),
            )

    async def _scrape_with_retry(
        self,
        url: str,
        domain: str,
        use_cache: bool,
    ) -> ScrapeResult:
        """Execute scrape with retry logic."""

        async def do_scrape():
            return await self._do_scrape(url, domain, use_cache)

        result = await self._retry_handler.execute(do_scrape, is_async=True)

        if result.success:
            scrape_result = result.result
            scrape_result.attempts = result.attempts
            self.ua_manager.report_success(domain)
            return scrape_result

        # Handle failure
        self.ua_manager.report_failure(domain)
        return ScrapeResult(
            success=False,
            url=url,
            domain=domain,
            error_type=self._categorize_error(result.error),
            error_message=result.message,
            attempts=result.attempts,
        )

    async def _do_scrape(
        self,
        url: str,
        domain: str,
        use_cache: bool,
    ) -> ScrapeResult:
        """Execute single scrape attempt."""
        async with self._browser_semaphore:
            # Get headers
            headers = self.ua_manager.get_headers(domain)

            # Configure browser
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            # Get store-specific wait selector
            store_config = get_store_config(domain)
            wait_for = None
            if store_config and "selectors" in store_config:
                wait_for = store_config["selectors"].get("wait_for")

            # Configure crawl
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED if use_cache else CacheMode.BYPASS,
                delay_before_return_html=self.config.page_load_delay,
                page_timeout=self.config.request_timeout * 1000,  # ms
                wait_for=wait_for,
                headers=headers,
            )

            # Execute crawl
            try:
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    result = await asyncio.wait_for(
                        crawler.arun(url, config=crawl_config),
                        timeout=self.config.operation_timeout,
                    )

                    if not result.success:
                        raise NetworkError(f"Crawl failed: {result.error_message}")

                    # Check for blocks
                    block_result = detect_block(
                        result.html,
                        status_code=result.status_code or 200,
                    )

                    if block_result.is_blocked:
                        raise self._block_to_exception(block_result)

                    # Extract product data
                    product_data = await self._extract(
                        result.html, domain, url
                    )

                    if product_data and product_data.name and product_data.price:
                        return ScrapeResult(
                            success=True,
                            product=product_data,
                            url=url,
                            domain=domain,
                            strategy_used=product_data.strategy_used,
                            status_code=result.status_code,
                        )

                    raise ParseError("Failed to extract product data from page")

            except TimeoutError as e:
                raise TimeoutError(f"Operation timed out after {self.config.operation_timeout}s") from e

    async def _extract(
        self,
        html: str,
        domain: str,
        url: str,
    ) -> ProductData | None:
        """
        Extract product data using waterfall strategy.

        Args:
            html: Page HTML
            domain: Store domain
            url: Original URL

        Returns:
            ProductData if extraction successful
        """
        selectors = get_store_selectors(domain)

        # Try each strategy in order
        for strategy in self._strategies:
            try:
                # Skip LLM if no client configured
                if isinstance(strategy, LlmExtractionStrategy) and not self.llm_client:
                    continue

                result = strategy.extract(html, selectors)

                if result and result.name and result.price:
                    return result

            except Exception:
                # Continue to next strategy on failure
                continue

        return None

    def _block_to_exception(self, block_result) -> Exception:
        """Convert block detection result to appropriate exception."""
        block_exceptions = {
            BlockType.CAPTCHA: BlockedError("CAPTCHA challenge required"),
            BlockType.LOGIN_REQUIRED: BlockedError("Login required"),
            BlockType.RATE_LIMITED: BlockedError("Rate limited by website"),
            BlockType.GEO_BLOCKED: BlockedError("Content geo-blocked"),
            BlockType.BOT_DETECTION: BlockedError("Bot detection triggered"),
            BlockType.ACCESS_DENIED: BlockedError("Access denied"),
            BlockType.NOT_FOUND: NotFoundError("Page not found"),
            BlockType.EMPTY_RESPONSE: NetworkError("Empty response"),
            BlockType.MAINTENANCE: NetworkError("Site under maintenance"),
        }
        return block_exceptions.get(
            block_result.block_type,
            BlockedError(f"Blocked: {block_result.details}"),
        )

    def _categorize_error(self, error: Exception) -> ScrapeErrorType:
        """Map exception to ScrapeErrorType."""
        if isinstance(error, TimeoutError):
            return ScrapeErrorType.TIMEOUT
        if isinstance(error, NetworkError):
            return ScrapeErrorType.NETWORK_ERROR
        if isinstance(error, BlockedError):
            return ScrapeErrorType.BLOCKED
        if isinstance(error, NotFoundError):
            return ScrapeErrorType.NOT_FOUND
        if isinstance(error, ParseError):
            return ScrapeErrorType.PARSE_FAILURE
        if isinstance(error, RobotsBlockedError):
            return ScrapeErrorType.ROBOTS_BLOCKED

        # Default to network error
        return ScrapeErrorType.NETWORK_ERROR

    def _elapsed_ms(self, start_time: float) -> int:
        """Calculate elapsed time in milliseconds."""
        return int((time.time() - start_time) * 1000)

    async def scrape_batch(
        self,
        urls: list[str],
        validate_ssrf: bool = True,
        use_cache: bool = False,
    ) -> list[ScrapeResult]:
        """
        Scrape multiple URLs using MemoryAdaptiveDispatcher for efficient batch processing.

        Args:
            urls: List of product page URLs
            validate_ssrf: Whether to validate against SSRF
            use_cache: Whether to use cached pages

        Returns:
            List of ScrapeResults (same order as input URLs)
        """
        if not urls:
            return []

        # For small batches, use regular scrape
        if len(urls) <= 2:
            return [await self.scrape(url, validate_ssrf, use_cache) for url in urls]

        # Configure browser for batch operation
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Configure crawl for batch
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED if use_cache else CacheMode.BYPASS,
            delay_before_return_html=self.config.page_load_delay,
            page_timeout=self.config.request_timeout * 1000,
        )

        results: list[ScrapeResult] = []

        # Use dispatcher for batch crawling
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler_results = await crawler.arun_many(
                urls,
                config=crawl_config,
                dispatcher=self._dispatcher,
            )

            for url, result in zip(urls, crawler_results, strict=True):
                start_time = time.time()
                domain = extract_domain(url) if result else ""

                if not result or not result.success:
                    results.append(ScrapeResult(
                        success=False,
                        url=url,
                        domain=domain,
                        error_type=ScrapeErrorType.NETWORK_ERROR,
                        error_message=result.error_message if result else "Crawl failed",
                        response_time_ms=self._elapsed_ms(start_time),
                    ))
                    continue

                # Check for blocks
                block_result = detect_block(
                    result.html,
                    status_code=result.status_code or 200,
                )

                if block_result.is_blocked:
                    results.append(ScrapeResult(
                        success=False,
                        url=url,
                        domain=domain,
                        error_type=ScrapeErrorType.BLOCKED,
                        error_message=f"Blocked: {block_result.details}",
                        response_time_ms=self._elapsed_ms(start_time),
                    ))
                    continue

                # Extract product data
                try:
                    product_data = await self._extract(result.html, domain, url)

                    if product_data and product_data.name and product_data.price:
                        results.append(ScrapeResult(
                            success=True,
                            product=product_data,
                            url=url,
                            domain=domain,
                            strategy_used=product_data.strategy_used,
                            status_code=result.status_code,
                            response_time_ms=self._elapsed_ms(start_time),
                        ))
                    else:
                        results.append(ScrapeResult(
                            success=False,
                            url=url,
                            domain=domain,
                            error_type=ScrapeErrorType.PARSE_FAILURE,
                            error_message="Failed to extract product data",
                            response_time_ms=self._elapsed_ms(start_time),
                        ))
                except Exception as e:
                    results.append(ScrapeResult(
                        success=False,
                        url=url,
                        domain=domain,
                        error_type=self._categorize_error(e),
                        error_message=str(e),
                        response_time_ms=self._elapsed_ms(start_time),
                    ))

        return results


# ===========================================
# Convenience Functions
# ===========================================

_scraper_engine: ScraperEngine | None = None


def get_scraper_engine() -> ScraperEngine:
    """Get the global scraper engine instance."""
    global _scraper_engine
    if _scraper_engine is None:
        _scraper_engine = ScraperEngine()
    return _scraper_engine


async def scrape_product(url: str) -> ScrapeResult:
    """
    Quick function to scrape a product URL.

    Args:
        url: Product page URL

    Returns:
        ScrapeResult
    """
    engine = get_scraper_engine()
    return await engine.scrape(url)
