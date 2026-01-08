"""
Rate limiting for scraper operations.
Implements per-store and global rate limits with Crawl4AI integration.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from crawl4ai import RateLimiter as Crawl4AIRateLimiter

from src.core.constants import MAX_SCRAPES_PER_MINUTE
from src.core.exceptions import RateLimitError


@dataclass
class RateLimitState:
    """State for a single rate limiter."""

    requests: list[float] = field(default_factory=list)
    limit: int = 10
    window_seconds: int = 60

    def clean_old_requests(self) -> None:
        """Remove requests outside the window."""
        cutoff = time.time() - self.window_seconds
        self.requests = [t for t in self.requests if t > cutoff]

    def can_request(self) -> bool:
        """Check if a new request is allowed."""
        self.clean_old_requests()
        return len(self.requests) < self.limit

    def record_request(self) -> None:
        """Record a new request."""
        self.requests.append(time.time())

    def wait_time(self) -> float:
        """Calculate time to wait before next request is allowed."""
        self.clean_old_requests()
        if len(self.requests) < self.limit:
            return 0

        oldest = min(self.requests)
        return max(0, oldest + self.window_seconds - time.time())


class RateLimiter:
    """
    Thread-safe rate limiter for scraper operations.

    Supports:
    - Global rate limit (all scrapes)
    - Per-store rate limits
    """

    def __init__(self, global_limit: int = MAX_SCRAPES_PER_MINUTE, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            global_limit: Max requests per minute globally
            window_seconds: Time window for rate limit
        """
        self._global = RateLimitState(limit=global_limit, window_seconds=window_seconds)
        self._stores: dict[str, RateLimitState] = defaultdict(
            lambda: RateLimitState(limit=10, window_seconds=window_seconds)
        )
        self._lock = asyncio.Lock()

    def set_store_limit(self, domain: str, limit: int) -> None:
        """
        Set rate limit for a specific store.

        Args:
            domain: Store domain
            limit: Requests per minute for this store
        """
        if domain not in self._stores:
            self._stores[domain] = RateLimitState(limit=limit)
        else:
            self._stores[domain].limit = limit

    async def acquire(self, domain: str) -> None:
        """
        Acquire permission to make a request.
        Blocks if rate limit is exceeded.

        Args:
            domain: Store domain

        Raises:
            RateLimitError: If limit cannot be acquired in reasonable time
        """
        async with self._lock:
            # Check global limit
            global_wait = self._global.wait_time()
            store_wait = self._stores[domain].wait_time()

            wait_time = max(global_wait, store_wait)

            if wait_time > 0:
                # Wait up to 30 seconds, otherwise fail
                if wait_time > 30:
                    raise RateLimitError(
                        f"Rate limit exceeded for {domain}",
                        retry_after=int(wait_time),
                    )
                await asyncio.sleep(wait_time)

            # Record the request
            self._global.record_request()
            self._stores[domain].record_request()

    def check(self, domain: str) -> bool:
        """
        Check if a request is allowed without blocking.

        Args:
            domain: Store domain

        Returns:
            True if request is allowed
        """
        return self._global.can_request() and self._stores[domain].can_request()

    def get_wait_time(self, domain: str) -> float:
        """
        Get wait time before next request is allowed.

        Args:
            domain: Store domain

        Returns:
            Seconds to wait (0 if no wait needed)
        """
        return max(self._global.wait_time(), self._stores[domain].wait_time())

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict with current state
        """
        self._global.clean_old_requests()
        return {
            "global": {
                "current": len(self._global.requests),
                "limit": self._global.limit,
                "window_seconds": self._global.window_seconds,
            },
            "stores": {
                domain: {
                    "current": len(state.requests),
                    "limit": state.limit,
                }
                for domain, state in self._stores.items()
                if state.requests
            },
        }


class TokenBucket:
    """
    Token bucket rate limiter for smooth rate limiting.
    Alternative to sliding window for some use cases.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Max tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens from the bucket.
        Blocks until tokens are available.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            while True:
                self._add_tokens()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                # Calculate wait time
                needed = tokens - self.tokens
                wait_time = needed / self.rate
                await asyncio.sleep(wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired
        """
        self._add_tokens()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# ===========================================
# Global Rate Limiter Instance
# ===========================================

# Singleton rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def configure_rate_limiter(global_limit: int = MAX_SCRAPES_PER_MINUTE) -> RateLimiter:
    """
    Configure and get rate limiter.

    Args:
        global_limit: Global rate limit

    Returns:
        Configured rate limiter
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(global_limit=global_limit)
    return _rate_limiter


# ===========================================
# Crawl4AI RateLimiter Integration
# ===========================================


def create_crawl4ai_rate_limiter(
    base_delay: tuple[float, float] = (1.0, 2.0),
    max_delay: float = 30.0,
    max_retries: int = 3,
) -> Crawl4AIRateLimiter:
    """
    Create a Crawl4AI RateLimiter instance for use with MemoryAdaptiveDispatcher.

    Args:
        base_delay: Tuple of (min_delay, max_delay) for random delay between requests
        max_delay: Maximum delay after exponential backoff
        max_retries: Maximum number of retries on rate limit

    Returns:
        Configured Crawl4AI RateLimiter
    """
    return Crawl4AIRateLimiter(
        base_delay=base_delay,
        max_delay=max_delay,
        max_retries=max_retries,
    )


def get_default_crawl4ai_rate_limiter() -> Crawl4AIRateLimiter:
    """
    Get a default Crawl4AI RateLimiter with sensible defaults.

    Returns:
        Crawl4AI RateLimiter configured for Canadian retail sites
    """
    return create_crawl4ai_rate_limiter(
        base_delay=(1.0, 2.0),  # Random delay between 1-2 seconds
        max_delay=30.0,         # Max 30 seconds after backoff
        max_retries=3,          # 3 retry attempts
    )
