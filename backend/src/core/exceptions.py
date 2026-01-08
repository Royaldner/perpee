"""
Custom exception classes for Perpee.
"""


class PerpeeError(Exception):
    """Base exception for all Perpee errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ===========================================
# Scraper Exceptions
# ===========================================


class ScraperError(PerpeeError):
    """Base exception for scraper-related errors."""

    pass


class NetworkError(ScraperError):
    """Network-related errors (connection issues, DNS failures)."""

    pass


class TimeoutError(ScraperError):
    """Request or operation timeout."""

    pass


class BlockedError(ScraperError):
    """Request blocked by website (CAPTCHA, login wall, rate limit)."""

    pass


class ParseError(ScraperError):
    """Failed to parse product data from page."""

    pass


class PriceValidationError(ScraperError):
    """Extracted price failed validation (negative, too high, etc.)."""

    pass


class StructureChangeError(ScraperError):
    """Website structure changed, selectors no longer work."""

    pass


class NotFoundError(ScraperError):
    """Product page returned 404."""

    pass


class RobotsBlockedError(ScraperError):
    """URL blocked by robots.txt."""

    pass


# ===========================================
# URL/Security Exceptions
# ===========================================


class URLError(PerpeeError):
    """Base exception for URL-related errors."""

    pass


class InvalidURLError(URLError):
    """URL format is invalid."""

    pass


class UnsupportedStoreError(URLError):
    """Store is not whitelisted/supported."""

    pass


class PrivateIPError(URLError):
    """URL resolves to private IP (SSRF protection)."""

    pass


# ===========================================
# Agent Exceptions
# ===========================================


class AgentError(PerpeeError):
    """Base exception for agent-related errors."""

    pass


class TokenLimitError(AgentError):
    """Token limit exceeded (daily or per-request)."""

    pass


class ToolExecutionError(AgentError):
    """Tool execution failed."""

    def __init__(self, tool_name: str, message: str, details: dict | None = None):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}", details)


class ModelError(AgentError):
    """LLM model returned an error."""

    pass


# ===========================================
# Database Exceptions
# ===========================================


class DatabaseError(PerpeeError):
    """Base exception for database errors."""

    pass


class RecordNotFoundError(DatabaseError):
    """Requested record not found in database."""

    def __init__(self, model: str, id: int | str):
        super().__init__(f"{model} with id '{id}' not found", {"model": model, "id": id})


class DuplicateRecordError(DatabaseError):
    """Attempt to create duplicate record."""

    pass


# ===========================================
# Notification Exceptions
# ===========================================


class NotificationError(PerpeeError):
    """Base exception for notification errors."""

    pass


class EmailDeliveryError(NotificationError):
    """Email delivery failed."""

    pass


# ===========================================
# Rate Limit Exceptions
# ===========================================


class RateLimitError(PerpeeError):
    """Rate limit exceeded."""

    def __init__(self, limit_type: str, retry_after: int | None = None):
        self.limit_type = limit_type
        self.retry_after = retry_after
        message = f"Rate limit exceeded: {limit_type}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message, {"limit_type": limit_type, "retry_after": retry_after})


# ===========================================
# Validation Exceptions
# ===========================================


class ValidationError(PerpeeError):
    """Input validation failed."""

    pass
