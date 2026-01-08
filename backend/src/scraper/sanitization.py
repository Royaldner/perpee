"""
Content sanitization for scraper operations.
Implements HTML tag stripping, XSS prevention, and price normalization.
"""

import re

import bleach

from src.core.constants import ALLOWED_HTML_TAGS, MAX_TEXT_LENGTH


def strip_html_tags(html: str) -> str:
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

    return cleaned


def sanitize_xss(text: str) -> str:
    """
    Sanitize text to prevent XSS attacks.

    Args:
        text: Text to sanitize

    Returns:
        XSS-safe text
    """
    if not text:
        return ""

    # Use bleach to clean - strips all tags by default
    cleaned = bleach.clean(text, tags=[], strip=True)

    # Remove any remaining script-like patterns
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"on\w+\s*=", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)

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
    # First strip HTML
    sanitized = strip_html_tags(name)

    # Apply XSS sanitization
    sanitized = sanitize_xss(sanitized)

    # Additional product-specific cleaning
    # Remove excessive punctuation
    sanitized = re.sub(r"[!@#$%^&*()_+=\[\]{}|\\:\";<>?,./]{3,}", "", sanitized)

    # Limit length
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "..."

    return sanitized.strip()


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


def sanitize_image_url(url: str | None) -> str | None:
    """
    Sanitize and normalize image URL.

    Args:
        url: Image URL to sanitize

    Returns:
        Sanitized URL or None
    """
    if not url:
        return None

    url = url.strip()

    # Handle protocol-relative URLs
    if url.startswith("//"):
        url = "https:" + url

    # Handle relative URLs (can't resolve without base URL)
    if not url.startswith(("http://", "https://")):
        return None

    # Basic XSS sanitization
    url = sanitize_xss(url)

    # Validate URL format
    if not re.match(r"^https?://[a-zA-Z0-9]", url):
        return None

    return url


def sanitize_scraped_content(content: dict) -> dict:
    """
    Sanitize all fields in scraped product content.

    Args:
        content: Dict with scraped product data

    Returns:
        Sanitized content dict
    """
    sanitized = {}

    if "name" in content and content["name"]:
        sanitized["name"] = sanitize_product_name(content["name"])

    if "price" in content:
        if isinstance(content["price"], str):
            sanitized["price"] = normalize_price(content["price"])
        else:
            sanitized["price"] = content["price"]

    if "original_price" in content:
        if isinstance(content["original_price"], str):
            sanitized["original_price"] = normalize_price(content["original_price"])
        else:
            sanitized["original_price"] = content["original_price"]

    if "image_url" in content:
        sanitized["image_url"] = sanitize_image_url(content["image_url"])

    if "brand" in content and content["brand"]:
        sanitized["brand"] = sanitize_text(content["brand"])[:255]

    if "upc" in content and content["upc"]:
        # UPC should only contain alphanumeric characters
        upc = re.sub(r"[^a-zA-Z0-9]", "", str(content["upc"]))
        sanitized["upc"] = upc[:50] if upc else None

    # Pass through other fields
    for key in ["currency", "in_stock"]:
        if key in content:
            sanitized[key] = content[key]

    return sanitized
