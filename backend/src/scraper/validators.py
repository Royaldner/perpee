"""
URL validation for scraper operations.
Implements URL format validation, domain whitelist check, and private IP blocking.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

from src.core.constants import P0_STORES, PRIVATE_IP_RANGES
from src.core.exceptions import InvalidURLError, PrivateIPError, UnsupportedStoreError


def validate_url_format(url: str) -> str:
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


def check_domain_whitelist(url: str, whitelist: list[str] | None = None) -> bool:
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
    normalized_url = validate_url_format(url)

    if not check_domain_whitelist(normalized_url, whitelist):
        domain = extract_domain(normalized_url)
        raise UnsupportedStoreError(
            f"Store '{domain}' is not supported. Use scan_website tool first."
        )

    return normalized_url


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


def block_private_ip(url: str) -> str:
    """
    Resolve URL's domain to IP and block private IPs (SSRF protection).

    Args:
        url: URL to validate

    Returns:
        Original URL if safe

    Raises:
        PrivateIPError: If URL resolves to private IP
        InvalidURLError: If DNS resolution fails
    """
    # First validate URL format
    validated_url = validate_url_format(url)

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


def validate_url_complete(url: str, check_whitelist: bool = True) -> str:
    """
    Complete URL validation: format, whitelist, and SSRF protection.

    Args:
        url: URL to validate
        check_whitelist: Whether to check domain whitelist

    Returns:
        Validated and normalized URL

    Raises:
        InvalidURLError: If URL format is invalid
        UnsupportedStoreError: If store is not whitelisted
        PrivateIPError: If URL resolves to private IP
    """
    # Validate format
    normalized = validate_url_format(url)

    # Check whitelist if required
    if check_whitelist and not check_domain_whitelist(normalized):
        domain = extract_domain(normalized)
        raise UnsupportedStoreError(
            f"Store '{domain}' is not supported. Use scan_website tool first."
        )

    # Block private IPs
    return block_private_ip(normalized)
