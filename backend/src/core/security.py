"""
Security utilities for Perpee.
Includes URL validation, SSRF protection, and content sanitization.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import bleach

from src.core.constants import (
    ALLOWED_HTML_TAGS,
    MAX_TEXT_LENGTH,
    P0_STORES,
    PRIVATE_IP_RANGES,
)
from src.core.exceptions import InvalidURLError, PrivateIPError, UnsupportedStoreError

# ===========================================
# URL Validation
# ===========================================


def validate_url(url: str) -> str:
    """
    Validate URL format and return normalized URL.

    Args:
        url: URL string to validate

    Returns:
        Normalized URL string

    Raises:
        InvalidURLError: If URL format is invalid
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL cannot be empty")

    url = url.strip()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InvalidURLError(f"Failed to parse URL: {e}") from e

    # Validate scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(f"Invalid URL scheme: {parsed.scheme}. Must be http or https.")

    # Validate netloc (domain)
    if not parsed.netloc:
        raise InvalidURLError("URL must have a valid domain")

    # Validate domain format
    domain = parsed.netloc.lower()
    if ":" in domain:
        domain = domain.split(":")[0]  # Remove port

    # Basic domain validation
    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$", domain):
        raise InvalidURLError(f"Invalid domain format: {domain}")

    # Normalize URL
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: URL string

    Returns:
        Domain string (e.g., 'amazon.ca')
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Remove port if present
    if ":" in domain:
        domain = domain.split(":")[0]

    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_whitelisted_store(url: str, whitelist: list[str] | None = None) -> bool:
    """
    Check if URL's domain is in the whitelist.

    Args:
        url: URL to check
        whitelist: List of allowed domains (defaults to P0_STORES)

    Returns:
        True if domain is whitelisted
    """
    if whitelist is None:
        whitelist = P0_STORES

    domain = extract_domain(url)

    # Check exact match and www. variant
    return domain in whitelist or f"www.{domain}" in whitelist


def validate_whitelisted_url(url: str, whitelist: list[str] | None = None) -> str:
    """
    Validate URL format AND check whitelist.

    Args:
        url: URL to validate
        whitelist: List of allowed domains

    Returns:
        Normalized URL

    Raises:
        InvalidURLError: If URL format is invalid
        UnsupportedStoreError: If store is not whitelisted
    """
    normalized_url = validate_url(url)

    if not is_whitelisted_store(normalized_url, whitelist):
        domain = extract_domain(normalized_url)
        raise UnsupportedStoreError(
            f"Store '{domain}' is not supported. Use scan_website tool first."
        )

    return normalized_url


# ===========================================
# SSRF Protection
# ===========================================


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private/internal.

    Args:
        ip: IP address string

    Returns:
        True if IP is private
    """
    try:
        ip_obj = ipaddress.ip_address(ip)

        # Check against private ranges
        for range_str in PRIVATE_IP_RANGES:
            network = ipaddress.ip_network(range_str, strict=False)
            if ip_obj in network:
                return True

        return False
    except ValueError:
        # If we can't parse the IP, be safe and reject
        return True


def resolve_and_validate_url(url: str) -> str:
    """
    Resolve URL's domain to IP and check for SSRF.

    Args:
        url: URL to validate

    Returns:
        Original URL if safe

    Raises:
        PrivateIPError: If URL resolves to private IP
        InvalidURLError: If DNS resolution fails
    """
    # First validate URL format
    validated_url = validate_url(url)

    # Extract hostname
    parsed = urlparse(validated_url)
    hostname = parsed.netloc
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # Resolve DNS
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise InvalidURLError(f"DNS resolution failed for {hostname}: {e}") from e

    # Check all resolved IPs
    for addr_info in ip_addresses:
        ip = addr_info[4][0]
        if is_private_ip(ip):
            raise PrivateIPError(
                f"URL resolves to private IP: {ip}",
                {"url": url, "ip": ip, "hostname": hostname},
            )

    return validated_url


# ===========================================
# Content Sanitization
# ===========================================


def sanitize_html(html: str) -> str:
    """
    Remove all HTML tags from string.

    Args:
        html: HTML string to sanitize

    Returns:
        Plain text with all HTML removed
    """
    if not html:
        return ""

    # Use bleach to strip all tags
    cleaned = bleach.clean(html, tags=ALLOWED_HTML_TAGS, strip=True)

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    # Truncate if too long
    if len(cleaned) > MAX_TEXT_LENGTH:
        cleaned = cleaned[:MAX_TEXT_LENGTH] + "..."

    return cleaned


def sanitize_text(text: str) -> str:
    """
    Sanitize plain text (remove control chars, normalize whitespace).

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove control characters (except newlines and tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    # Truncate if too long
    if len(cleaned) > MAX_TEXT_LENGTH:
        cleaned = cleaned[:MAX_TEXT_LENGTH] + "..."

    return cleaned


def sanitize_product_name(name: str) -> str:
    """
    Sanitize product name.

    Args:
        name: Product name to sanitize

    Returns:
        Sanitized product name
    """
    sanitized = sanitize_html(name)

    # Additional product-specific cleaning
    # Remove excessive punctuation
    sanitized = re.sub(r"[!@#$%^&*()_+=\[\]{}|\\:\";<>?,./]{3,}", "", sanitized)

    # Limit length
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "..."

    return sanitized.strip()


# ===========================================
# Price Normalization
# ===========================================


def normalize_price(price_str: str) -> float | None:
    """
    Parse price string to float.

    Args:
        price_str: Price string (e.g., "$1,234.56", "CAD 99.99")

    Returns:
        Float price or None if parsing fails
    """
    if not price_str:
        return None

    # Remove currency symbols and text
    cleaned = re.sub(r"[A-Za-z$€£¥]", "", price_str)

    # Remove commas (thousand separators)
    cleaned = cleaned.replace(",", "")

    # Remove whitespace
    cleaned = cleaned.strip()

    # Handle ranges (take lower price)
    if "-" in cleaned and cleaned.count("-") == 1:
        parts = cleaned.split("-")
        cleaned = parts[0].strip()

    try:
        price = float(cleaned)
        # Validate range
        if price < 0.01 or price > 1_000_000:
            return None
        return round(price, 2)
    except (ValueError, TypeError):
        return None


def validate_price(price: float) -> bool:
    """
    Validate that price is within acceptable range.

    Args:
        price: Price value to validate

    Returns:
        True if price is valid
    """
    return 0.01 <= price <= 1_000_000.00
