"""
Retry strategy for scraper operations.
Implements exponential backoff with configurable retry matrix.
"""

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from src.core.constants import MAX_RETRIES, RETRY_DELAYS
from src.core.exceptions import (
    BlockedError,
    NetworkError,
    NotFoundError,
    ScraperError,
    TimeoutError,
)

T = TypeVar("T")


class ErrorCategory(str, Enum):
    """Categories of errors for retry logic."""

    NETWORK = "network_error"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    RATE_LIMITED = "rate_limited"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
    PARSE_ERROR = "parse_error"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = MAX_RETRIES
    delays: dict[str, list[float]] = field(default_factory=lambda: RETRY_DELAYS.copy())
    jitter: float = 0.2  # Random jitter factor (0.2 = +-20%)

    def get_delay(self, category: ErrorCategory, attempt: int) -> float:
        """
        Get delay for a specific error category and attempt.

        Args:
            category: Error category
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds with jitter applied
        """
        delays = self.delays.get(category.value, [2, 4, 8])
        base_delay = delays[min(attempt, len(delays) - 1)]

        # Apply jitter
        jitter_range = base_delay * self.jitter
        return base_delay + random.uniform(-jitter_range, jitter_range)

    def should_retry(self, category: ErrorCategory, attempt: int) -> bool:
        """
        Check if should retry for given error category and attempt.

        Args:
            category: Error category
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry
        """
        # Don't retry not_found
        if category == ErrorCategory.NOT_FOUND:
            return False

        # Forbidden gets only 1 retry
        if category == ErrorCategory.FORBIDDEN:
            return attempt < 1

        # Blocked gets limited retries
        if category == ErrorCategory.BLOCKED:
            return attempt < 2

        # Parse errors might benefit from retry (page might not have loaded fully)
        if category == ErrorCategory.PARSE_ERROR:
            return attempt < 2

        return attempt < self.max_retries


@dataclass
class RetryResult:
    """Result of a retry operation."""

    success: bool
    result: Any = None
    error: Exception | None = None
    attempts: int = 0
    category: ErrorCategory | None = None
    message: str = ""


def categorize_error(error: Exception) -> ErrorCategory:
    """
    Categorize an exception for retry purposes.

    Args:
        error: Exception to categorize

    Returns:
        Error category
    """
    if isinstance(error, TimeoutError):
        return ErrorCategory.TIMEOUT
    if isinstance(error, NetworkError):
        return ErrorCategory.NETWORK
    if isinstance(error, NotFoundError):
        return ErrorCategory.NOT_FOUND
    if isinstance(error, BlockedError):
        # Check if it's a rate limit
        if "429" in str(error) or "rate" in str(error).lower():
            return ErrorCategory.RATE_LIMITED
        if "403" in str(error):
            return ErrorCategory.FORBIDDEN
        return ErrorCategory.BLOCKED
    if isinstance(error, ScraperError):
        return ErrorCategory.PARSE_ERROR

    # Generic network errors
    error_str = str(error).lower()
    if "timeout" in error_str:
        return ErrorCategory.TIMEOUT
    if "connection" in error_str or "network" in error_str:
        return ErrorCategory.NETWORK
    if "404" in error_str:
        return ErrorCategory.NOT_FOUND
    if "403" in error_str:
        return ErrorCategory.FORBIDDEN
    if "429" in error_str:
        return ErrorCategory.RATE_LIMITED
    if "50" in error_str:  # 500, 502, 503, etc.
        return ErrorCategory.SERVER_ERROR

    return ErrorCategory.NETWORK  # Default to network error


class RetryHandler:
    """
    Handler for retry operations with exponential backoff.
    """

    def __init__(self, config: RetryConfig | None = None):
        """
        Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self._callbacks: list[Callable[[int, ErrorCategory, float], None]] = []

    def on_retry(self, callback: Callable[[int, ErrorCategory, float], None]) -> None:
        """
        Register callback for retry events.

        Args:
            callback: Function called on retry (attempt, category, delay)
        """
        self._callbacks.append(callback)

    def _notify_retry(self, attempt: int, category: ErrorCategory, delay: float) -> None:
        """Notify callbacks of retry event."""
        for callback in self._callbacks:
            try:
                callback(attempt, category, delay)
            except Exception:
                pass

    async def execute(
        self,
        func: Callable[[], T],
        is_async: bool = False,
    ) -> RetryResult:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            is_async: Whether func is async

        Returns:
            RetryResult with outcome
        """
        attempt = 0
        last_error: Exception | None = None
        last_category: ErrorCategory | None = None

        while True:
            try:
                if is_async:
                    result = await func()
                else:
                    result = func()
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                )
            except Exception as e:
                last_error = e
                last_category = categorize_error(e)

                if not self.config.should_retry(last_category, attempt):
                    break

                delay = self.config.get_delay(last_category, attempt)
                self._notify_retry(attempt + 1, last_category, delay)
                await asyncio.sleep(delay)
                attempt += 1

        # Build user-friendly message
        message = self._build_message(last_category, attempt + 1, last_error)

        return RetryResult(
            success=False,
            error=last_error,
            attempts=attempt + 1,
            category=last_category,
            message=message,
        )

    def _build_message(
        self,
        category: ErrorCategory | None,
        attempts: int,
        error: Exception | None,
    ) -> str:
        """Build user-friendly error message."""
        messages = {
            ErrorCategory.NETWORK: f"Network error after {attempts} attempts. Please check your connection.",
            ErrorCategory.TIMEOUT: f"Request timed out after {attempts} attempts. The website may be slow.",
            ErrorCategory.SERVER_ERROR: f"Server error after {attempts} attempts. The website may be having issues.",
            ErrorCategory.RATE_LIMITED: "Rate limited by the website. Please wait before trying again.",
            ErrorCategory.FORBIDDEN: "Access denied by the website. This product may require login.",
            ErrorCategory.NOT_FOUND: "Product page not found (404). The URL may be incorrect.",
            ErrorCategory.BLOCKED: "Blocked by the website. CAPTCHA or login may be required.",
            ErrorCategory.PARSE_ERROR: "Failed to extract product data. The page format may have changed.",
        }

        if category:
            return messages.get(category, f"Error after {attempts} attempts: {error}")

        return f"Error after {attempts} attempts: {error}"


async def with_retry(
    func: Callable[[], T],
    config: RetryConfig | None = None,
    on_retry: Callable[[int, ErrorCategory, float], None] | None = None,
) -> T:
    """
    Execute async function with retry logic.

    Args:
        func: Async function to execute
        config: Retry configuration
        on_retry: Callback for retry events

    Returns:
        Function result

    Raises:
        Original exception if all retries fail
    """
    handler = RetryHandler(config)
    if on_retry:
        handler.on_retry(on_retry)

    result = await handler.execute(func, is_async=True)

    if result.success:
        return result.result

    raise result.error


def get_retry_message(attempt: int, max_retries: int, error: str) -> str:
    """
    Get user-friendly retry message.

    Args:
        attempt: Current attempt (1-indexed)
        max_retries: Maximum retries
        error: Error description

    Returns:
        User-friendly message
    """
    return f"Retrying {attempt}/{max_retries}... ({error})"
