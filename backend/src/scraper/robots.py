"""
Robots.txt handling for scraper.
Respects robots.txt directives with caching.
Integrates with Crawl4AI native check_robots_txt support.
"""

import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from crawl4ai import CrawlerRunConfig

from src.core.constants import DEFAULT_HEADERS, USER_AGENTS


@dataclass
class RobotsResult:
    """Result of robots.txt check."""

    allowed: bool
    crawl_delay: float | None = None
    reason: str = ""


@dataclass
class CachedRobots:
    """Cached robots.txt data."""

    parser: RobotFileParser
    crawl_delay: float | None
    fetched_at: float
    ttl: int = 3600  # Cache for 1 hour


class RobotsHandler:
    """
    Handler for robots.txt checking with caching.

    Uses Crawl4AI's native robots.txt support when available,
    with fallback to manual checking.
    """

    def __init__(self, user_agent: str | None = None, cache_ttl: int = 3600):
        """
        Initialize robots handler.

        Args:
            user_agent: User agent for robots.txt checking
            cache_ttl: Cache TTL in seconds
        """
        self.user_agent = user_agent or USER_AGENTS[0]
        self.cache_ttl = cache_ttl
        self._cache: dict[str, CachedRobots] = {}
        self._lock = asyncio.Lock()

    def _get_robots_url(self, url: str) -> str:
        """Get robots.txt URL for a given URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _get_cache_key(self, url: str) -> str:
        """Get cache key for a URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _is_cached(self, key: str) -> bool:
        """Check if robots.txt is cached and valid."""
        if key not in self._cache:
            return False
        cached = self._cache[key]
        return time.time() - cached.fetched_at < cached.ttl

    async def fetch_robots(self, url: str) -> RobotFileParser | None:
        """
        Fetch and parse robots.txt for a URL.

        Args:
            url: URL to check

        Returns:
            RobotFileParser or None if fetch failed
        """
        robots_url = self._get_robots_url(url)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    robots_url,
                    headers={
                        "User-Agent": self.user_agent,
                        **DEFAULT_HEADERS,
                    },
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    return parser

        except Exception:
            # If we can't fetch robots.txt, assume allowed
            pass

        return None

    async def check(self, url: str, respect_robots: bool = True) -> RobotsResult:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: URL to check
            respect_robots: Whether to enforce robots.txt

        Returns:
            RobotsResult with permission status
        """
        if not respect_robots:
            return RobotsResult(allowed=True, reason="Robots.txt checking disabled")

        cache_key = self._get_cache_key(url)

        async with self._lock:
            # Check cache
            if self._is_cached(cache_key):
                cached = self._cache[cache_key]
                allowed = cached.parser.can_fetch(self.user_agent, url)
                return RobotsResult(
                    allowed=allowed,
                    crawl_delay=cached.crawl_delay,
                    reason="robots.txt allows" if allowed else "robots.txt disallows",
                )

            # Fetch fresh robots.txt
            parser = await self.fetch_robots(url)

            if parser is None:
                # No robots.txt or fetch failed - assume allowed
                return RobotsResult(
                    allowed=True,
                    reason="No robots.txt or fetch failed - proceeding",
                )

            # Get crawl delay
            crawl_delay = None
            try:
                delay = parser.crawl_delay(self.user_agent)
                if delay:
                    crawl_delay = float(delay)
            except Exception:
                pass

            # Cache the result
            self._cache[cache_key] = CachedRobots(
                parser=parser,
                crawl_delay=crawl_delay,
                fetched_at=time.time(),
                ttl=self.cache_ttl,
            )

            allowed = parser.can_fetch(self.user_agent, url)
            return RobotsResult(
                allowed=allowed,
                crawl_delay=crawl_delay,
                reason="robots.txt allows" if allowed else "robots.txt disallows",
            )

    def clear_cache(self, domain: str | None = None) -> None:
        """
        Clear robots.txt cache.

        Args:
            domain: Specific domain to clear, or None for all
        """
        if domain:
            keys_to_remove = [k for k in self._cache if domain in k]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

    def get_crawl_delay(self, url: str) -> float | None:
        """
        Get cached crawl delay for a URL.

        Args:
            url: URL to check

        Returns:
            Crawl delay in seconds or None
        """
        cache_key = self._get_cache_key(url)
        if cache_key in self._cache:
            return self._cache[cache_key].crawl_delay
        return None


# ===========================================
# Global Handler Instance
# ===========================================

_robots_handler: RobotsHandler | None = None


def get_robots_handler() -> RobotsHandler:
    """Get the global robots handler instance."""
    global _robots_handler
    if _robots_handler is None:
        _robots_handler = RobotsHandler()
    return _robots_handler


async def is_allowed(url: str, respect_robots: bool = True) -> bool:
    """
    Quick check if URL is allowed by robots.txt.

    Args:
        url: URL to check
        respect_robots: Whether to enforce

    Returns:
        True if allowed
    """
    handler = get_robots_handler()
    result = await handler.check(url, respect_robots)
    return result.allowed


# ===========================================
# Crawl4AI Native Robots.txt Integration
# ===========================================


def create_robots_aware_config(
    check_robots_txt: bool = True,
    **kwargs,
) -> CrawlerRunConfig:
    """
    Create a CrawlerRunConfig with Crawl4AI native robots.txt checking enabled.

    This uses Crawl4AI's built-in robots.txt compliance rather than manual checking.
    When enabled, Crawl4AI will automatically respect robots.txt directives.

    Args:
        check_robots_txt: Whether to enable native robots.txt checking
        **kwargs: Additional CrawlerRunConfig parameters

    Returns:
        CrawlerRunConfig with robots.txt settings applied
    """
    return CrawlerRunConfig(
        check_robots_txt=check_robots_txt,
        **kwargs,
    )


def get_default_robots_config() -> CrawlerRunConfig:
    """
    Get a default CrawlerRunConfig with robots.txt checking enabled.

    Returns:
        CrawlerRunConfig configured for robots.txt compliance
    """
    return create_robots_aware_config(
        check_robots_txt=True,
    )
