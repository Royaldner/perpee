"""
Agent guardrails for token limits, rate limiting, and timeouts.
Protects against runaway costs and ensures responsible API usage.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from config.settings import settings
from src.core.exceptions import RateLimitError, TokenLimitError

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Tracks token usage for a single request."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


@dataclass
class DailyTokenTracker:
    """
    Tracks daily token usage to enforce budget limits.

    Token limit resets at midnight UTC.
    """

    daily_limit: int = field(default_factory=lambda: settings.daily_token_limit)
    _usage_today: int = 0
    _reset_timestamp: float = 0.0

    def __post_init__(self):
        """Initialize reset timestamp to start of current day."""
        self._reset_timestamp = self._get_day_start()

    def _get_day_start(self) -> float:
        """Get timestamp for start of current UTC day."""
        import datetime

        now = datetime.datetime.now(datetime.UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start.timestamp()

    def _maybe_reset(self) -> None:
        """Reset usage if a new day has started."""
        current_day_start = self._get_day_start()
        if current_day_start > self._reset_timestamp:
            logger.info(f"Resetting daily token usage (was {self._usage_today})")
            self._usage_today = 0
            self._reset_timestamp = current_day_start

    @property
    def remaining(self) -> int:
        """Tokens remaining for today."""
        self._maybe_reset()
        return max(0, self.daily_limit - self._usage_today)

    @property
    def usage_percent(self) -> float:
        """Percentage of daily budget used."""
        self._maybe_reset()
        return (self._usage_today / self.daily_limit) * 100

    def record_usage(self, tokens: int) -> None:
        """
        Record token usage.

        Args:
            tokens: Number of tokens used
        """
        self._maybe_reset()
        self._usage_today += tokens
        logger.debug(f"Recorded {tokens} tokens (total today: {self._usage_today})")

    def check_available(self, estimated_tokens: int) -> bool:
        """
        Check if there are enough tokens available.

        Args:
            estimated_tokens: Estimated tokens for the request

        Returns:
            True if enough tokens available
        """
        return self.remaining >= estimated_tokens

    def enforce_limit(self, estimated_tokens: int) -> None:
        """
        Raise exception if daily limit would be exceeded.

        Args:
            estimated_tokens: Estimated tokens for the request

        Raises:
            TokenLimitError: If limit would be exceeded
        """
        if not self.check_available(estimated_tokens):
            raise TokenLimitError(
                f"Daily token limit would be exceeded. "
                f"Remaining: {self.remaining}, Requested: {estimated_tokens}"
            )


@dataclass
class LLMRateLimiter:
    """
    Rate limiter for LLM API requests.

    Uses sliding window algorithm.
    """

    max_requests_per_minute: int = field(
        default_factory=lambda: settings.max_llm_requests_per_minute
    )
    _timestamps: deque = field(default_factory=lambda: deque(maxlen=100))

    def _cleanup_old(self) -> None:
        """Remove timestamps older than 1 minute."""
        now = time.time()
        cutoff = now - 60.0

        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    @property
    def requests_in_window(self) -> int:
        """Number of requests in the current window."""
        self._cleanup_old()
        return len(self._timestamps)

    @property
    def can_make_request(self) -> bool:
        """Check if a request can be made."""
        return self.requests_in_window < self.max_requests_per_minute

    def record_request(self) -> None:
        """Record a request timestamp."""
        self._timestamps.append(time.time())

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.

        Waits if rate limit is reached.
        """
        while not self.can_make_request:
            # Wait until the oldest request expires
            wait_time = 60.0 - (time.time() - self._timestamps[0])
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(min(wait_time + 0.1, 5.0))
            self._cleanup_old()

        self.record_request()

    def enforce_limit(self) -> None:
        """
        Raise exception if rate limit exceeded.

        Raises:
            RateLimitError: If rate limit exceeded
        """
        if not self.can_make_request:
            wait_time = 60.0 - (time.time() - self._timestamps[0])
            raise RateLimitError("llm_requests", retry_after=int(wait_time) + 1)


@dataclass
class InputValidator:
    """Validates and limits input to the agent."""

    max_input_tokens: int = field(default_factory=lambda: settings.input_token_limit)
    max_output_tokens: int = field(default_factory=lambda: settings.output_token_limit)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple approximation: ~4 characters per token.
        """
        return len(text) // 4 + 1

    def validate_input(self, text: str) -> str:
        """
        Validate and potentially truncate input.

        Args:
            text: Input text

        Returns:
            Validated (possibly truncated) text

        Raises:
            TokenLimitError: If input exceeds limit and can't be truncated
        """
        estimated = self.estimate_tokens(text)

        if estimated <= self.max_input_tokens:
            return text

        # Truncate to approximate limit
        max_chars = self.max_input_tokens * 4
        truncated = text[:max_chars]

        logger.warning(
            f"Input truncated from ~{estimated} to ~{self.estimate_tokens(truncated)} tokens"
        )

        return truncated

    def get_max_output_tokens(self) -> int:
        """Get maximum output tokens for API request."""
        return self.max_output_tokens


def with_timeout(timeout_seconds: int | None = None):
    """
    Decorator to add timeout to async functions.

    Args:
        timeout_seconds: Timeout in seconds (default: operation_timeout from settings)
    """
    timeout = timeout_seconds or settings.operation_timeout_seconds

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except TimeoutError as e:
                raise TimeoutError(
                    f"Operation timed out after {timeout} seconds"
                ) from e

        return wrapper

    return decorator


# ===========================================
# Global Instances
# ===========================================

_token_tracker: DailyTokenTracker | None = None
_rate_limiter: LLMRateLimiter | None = None
_input_validator: InputValidator | None = None


def get_token_tracker() -> DailyTokenTracker:
    """Get the global token tracker instance."""
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = DailyTokenTracker()
    return _token_tracker


def get_rate_limiter() -> LLMRateLimiter:
    """Get the global LLM rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LLMRateLimiter()
    return _rate_limiter


def get_input_validator() -> InputValidator:
    """Get the global input validator instance."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator


def reset_guardrails() -> None:
    """Reset all guardrail instances (for testing)."""
    global _token_tracker, _rate_limiter, _input_validator
    _token_tracker = None
    _rate_limiter = None
    _input_validator = None
