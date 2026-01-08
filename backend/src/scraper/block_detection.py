"""
Block detection for scraper operations.
Detects CAPTCHA, login walls, and other blocking mechanisms.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    """Types of blocks that can be detected."""

    CAPTCHA = "captcha"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"
    GEO_BLOCKED = "geo_blocked"
    BOT_DETECTION = "bot_detection"
    EMPTY_RESPONSE = "empty_response"
    ACCESS_DENIED = "access_denied"
    AGE_GATE = "age_gate"
    MAINTENANCE = "maintenance"
    NOT_FOUND = "not_found"


@dataclass
class BlockDetectionResult:
    """Result of block detection analysis."""

    is_blocked: bool
    block_type: BlockType | None = None
    confidence: float = 0.0  # 0.0 to 1.0
    details: str = ""
    indicators: list[str] | None = None


# ===========================================
# Detection Patterns
# ===========================================

CAPTCHA_PATTERNS = [
    r"captcha",
    r"recaptcha",
    r"hcaptcha",
    r"challenge-form",
    r"g-recaptcha",
    r"cf-turnstile",
    r"verify.+human",
    r"robot.+check",
    r"prove.+human",
    r"security.+check",
    r"are you a robot",
    r"i am not a robot",
    r"complete.+captcha",
    r"datadome",
    r"px-captcha",
    r"distil",
]

LOGIN_PATTERNS = [
    r"sign.?in",
    r"log.?in",
    r"please.+sign.?in",
    r"please.+log.?in",
    r"authentication.+required",
    r"access.+denied.*login",
    r"members.+only",
    r"password",
    r"create.+account",
    r"register.+to.+continue",
]

RATE_LIMIT_PATTERNS = [
    r"rate.?limit",
    r"too.+many.+requests",
    r"slow.+down",
    r"try.+again.+later",
    r"request.+limit",
    r"temporarily.+unavailable",
    r"service.+unavailable",
    r"retry.+later",
]

BOT_DETECTION_PATTERNS = [
    r"automated.+access",
    r"bot.+detected",
    r"suspicious.+activity",
    r"unusual.+traffic",
    r"blocked.+suspicious",
    r"access.+denied",
    r"pardon.+interruption",
    r"attention.+required",
    r"checking.+browser",
    r"ddos.+protection",
    r"cloudflare",
    r"akamai",
    r"incapsula",
    r"imperva",
    r"sucuri",
]

GEO_BLOCK_PATTERNS = [
    r"not.+available.+in.+your.+region",
    r"not.+available.+in.+your.+country",
    r"geo.?restricted",
    r"region.+blocked",
    r"available.+only.+in",
    r"sorry.+this.+content.+is.+not.+available",
]

MAINTENANCE_PATTERNS = [
    r"under.+maintenance",
    r"scheduled.+maintenance",
    r"temporarily.+down",
    r"we.+will.+be.+back",
    r"site.+under.+construction",
    r"coming.+soon",
]

AGE_GATE_PATTERNS = [
    r"age.+verification",
    r"confirm.+your.+age",
    r"must.+be.+18",
    r"must.+be.+21",
    r"adult.+content",
    r"age.+restricted",
]


# ===========================================
# Block Detection Functions
# ===========================================


def detect_block(
    html: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> BlockDetectionResult:
    """
    Detect if a page indicates a blocked request.

    Args:
        html: Page HTML content
        status_code: HTTP status code
        headers: Response headers

    Returns:
        BlockDetectionResult with detection details
    """
    headers = headers or {}

    # Check status codes that override content analysis
    if status_code == 429:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.RATE_LIMITED,
            confidence=1.0,
            details="Rate limited by server (429)",
            indicators=["http_429"],
        )

    if status_code == 404:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.NOT_FOUND,
            confidence=1.0,
            details="Page not found (404)",
            indicators=["http_404"],
        )

    # Check empty response (after status codes that can have minimal content)
    if not html or len(html.strip()) < 100:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.EMPTY_RESPONSE,
            confidence=0.9,
            details="Empty or minimal response received",
            indicators=["empty_response"],
        )

    # Check status code
    if status_code == 403:
        result = _detect_403_block(html, headers)
        if result.is_blocked:
            return result

    if status_code == 503:
        if _matches_patterns(html, MAINTENANCE_PATTERNS):
            return BlockDetectionResult(
                is_blocked=True,
                block_type=BlockType.MAINTENANCE,
                confidence=0.9,
                details="Site under maintenance",
                indicators=["http_503", "maintenance_pattern"],
            )

    # Check HTML content for various blocks
    html_lower = html.lower()

    # CAPTCHA detection
    captcha_result = _detect_captcha(html_lower)
    if captcha_result.is_blocked:
        return captcha_result

    # Bot detection
    bot_result = _detect_bot_block(html_lower)
    if bot_result.is_blocked:
        return bot_result

    # Login required
    login_result = _detect_login_required(html_lower)
    if login_result.is_blocked:
        return login_result

    # Rate limiting
    rate_result = _detect_rate_limit(html_lower)
    if rate_result.is_blocked:
        return rate_result

    # Geo blocking
    geo_result = _detect_geo_block(html_lower)
    if geo_result.is_blocked:
        return geo_result

    # Age gate
    age_result = _detect_age_gate(html_lower)
    if age_result.is_blocked:
        return age_result

    return BlockDetectionResult(is_blocked=False)


def _matches_patterns(text: str, patterns: list[str]) -> tuple[bool, list[str]]:
    """
    Check if text matches any pattern.

    Returns:
        Tuple of (matches, list of matched patterns)
    """
    matched = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)
    return bool(matched), matched


def _detect_403_block(html: str, headers: dict[str, str]) -> BlockDetectionResult:
    """Detect specific type of 403 block."""
    html_lower = html.lower()

    # Check headers for WAF indicators
    waf_headers = ["cf-ray", "x-sucuri-id", "x-akamai-request-id", "x-cdn"]
    waf_detected = any(h.lower() in headers for h in waf_headers)

    if waf_detected:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.BOT_DETECTION,
            confidence=0.9,
            details="WAF/CDN blocking detected",
            indicators=["http_403", "waf_header"],
        )

    # Check for CAPTCHA in 403 page
    captcha_match, patterns = _matches_patterns(html_lower, CAPTCHA_PATTERNS)
    if captcha_match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.CAPTCHA,
            confidence=0.95,
            details="CAPTCHA challenge required",
            indicators=["http_403"] + patterns,
        )

    return BlockDetectionResult(
        is_blocked=True,
        block_type=BlockType.ACCESS_DENIED,
        confidence=0.8,
        details="Access denied (403)",
        indicators=["http_403"],
    )


def _detect_captcha(html: str) -> BlockDetectionResult:
    """Detect CAPTCHA challenge."""
    match, patterns = _matches_patterns(html, CAPTCHA_PATTERNS)
    if match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.CAPTCHA,
            confidence=0.9,
            details="CAPTCHA challenge detected",
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


def _detect_bot_block(html: str) -> BlockDetectionResult:
    """Detect bot/automation blocking."""
    match, patterns = _matches_patterns(html, BOT_DETECTION_PATTERNS)
    if match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.BOT_DETECTION,
            confidence=0.85,
            details="Bot detection triggered",
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


def _detect_login_required(html: str) -> BlockDetectionResult:
    """Detect login requirement."""
    match, patterns = _matches_patterns(html, LOGIN_PATTERNS)
    if match:
        # Check for high-confidence indicators
        if "sign in to continue" in html or "log in to continue" in html:
            return BlockDetectionResult(
                is_blocked=True,
                block_type=BlockType.LOGIN_REQUIRED,
                confidence=0.9,
                details="Login required to view content",
                indicators=patterns,
            )
        # Lower confidence for generic login page elements
        return BlockDetectionResult(
            is_blocked=False,  # Many product pages have login links
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


def _detect_rate_limit(html: str) -> BlockDetectionResult:
    """Detect rate limiting."""
    match, patterns = _matches_patterns(html, RATE_LIMIT_PATTERNS)
    if match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.RATE_LIMITED,
            confidence=0.9,
            details="Rate limiting detected",
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


def _detect_geo_block(html: str) -> BlockDetectionResult:
    """Detect geo-blocking."""
    match, patterns = _matches_patterns(html, GEO_BLOCK_PATTERNS)
    if match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.GEO_BLOCKED,
            confidence=0.85,
            details="Content not available in your region",
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


def _detect_age_gate(html: str) -> BlockDetectionResult:
    """Detect age verification requirement."""
    match, patterns = _matches_patterns(html, AGE_GATE_PATTERNS)
    if match:
        return BlockDetectionResult(
            is_blocked=True,
            block_type=BlockType.AGE_GATE,
            confidence=0.85,
            details="Age verification required",
            indicators=patterns,
        )
    return BlockDetectionResult(is_blocked=False)


# ===========================================
# Evasion Strategies
# ===========================================


def get_evasion_strategy(block_result: BlockDetectionResult) -> dict[str, Any]:
    """
    Get recommended evasion strategy for a detected block.

    Args:
        block_result: Detection result

    Returns:
        Dict with evasion recommendations
    """
    if not block_result.is_blocked:
        return {}

    strategies = {
        BlockType.CAPTCHA: {
            "action": "fail",
            "message": "CAPTCHA detected. Manual intervention required.",
            "retryable": False,
        },
        BlockType.LOGIN_REQUIRED: {
            "action": "fail",
            "message": "Login required. Cannot scrape protected content.",
            "retryable": False,
        },
        BlockType.RATE_LIMITED: {
            "action": "wait",
            "wait_seconds": 60,
            "message": "Rate limited. Waiting before retry.",
            "retryable": True,
        },
        BlockType.GEO_BLOCKED: {
            "action": "fail",
            "message": "Content not available in your region.",
            "retryable": False,
        },
        BlockType.BOT_DETECTION: {
            "action": "rotate",
            "rotate_user_agent": True,
            "clear_cookies": True,
            "add_delay": 5,
            "message": "Bot detection triggered. Rotating identity.",
            "retryable": True,
        },
        BlockType.EMPTY_RESPONSE: {
            "action": "retry",
            "add_delay": 2,
            "message": "Empty response. Retrying with delay.",
            "retryable": True,
        },
        BlockType.ACCESS_DENIED: {
            "action": "rotate",
            "rotate_user_agent": True,
            "message": "Access denied. Rotating user agent.",
            "retryable": True,
            "max_retries": 2,
        },
        BlockType.AGE_GATE: {
            "action": "fail",
            "message": "Age verification required. Cannot proceed automatically.",
            "retryable": False,
        },
        BlockType.MAINTENANCE: {
            "action": "wait",
            "wait_seconds": 300,
            "message": "Site under maintenance.",
            "retryable": True,
        },
        BlockType.NOT_FOUND: {
            "action": "fail",
            "message": "Page not found (404).",
            "retryable": False,
        },
    }

    return strategies.get(
        block_result.block_type,
        {"action": "retry", "retryable": True, "message": "Unknown block type"},
    )
