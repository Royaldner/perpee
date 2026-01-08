"""
Extraction strategies for product data.
Implements waterfall: JSON-LD -> CSS -> XPath -> LLM
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from src.core.constants import JSON_LD_PRODUCT_TYPES
from src.core.security import normalize_price, sanitize_product_name
from src.database.models import ExtractionStrategy


@dataclass
class ProductData:
    """Extracted product data."""

    name: str | None = None
    price: float | None = None
    original_price: float | None = None
    currency: str = "CAD"
    in_stock: bool = True
    image_url: str | None = None
    brand: str | None = None
    upc: str | None = None
    strategy_used: ExtractionStrategy | None = None


class BaseStrategy(ABC):
    """Base class for extraction strategies."""

    strategy_type: ExtractionStrategy

    @abstractmethod
    def extract(self, html: str, selectors: dict | None = None) -> ProductData | None:
        """
        Extract product data from HTML.

        Args:
            html: Raw HTML content
            selectors: Store-specific selectors (for CSS/XPath strategies)

        Returns:
            ProductData if successful, None otherwise
        """
        pass


class JsonLdStrategy(BaseStrategy):
    """Extract product data from JSON-LD structured data."""

    strategy_type = ExtractionStrategy.JSON_LD

    def extract(self, html: str, selectors: dict | None = None) -> ProductData | None:
        """Extract from JSON-LD script tags."""
        soup = BeautifulSoup(html, "lxml")

        # Find all JSON-LD scripts
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        if not scripts:
            return None

        for script in scripts:
            try:
                data = json.loads(script.string)
                product = self._find_product(data)
                if product:
                    return self._parse_product(product)
            except (json.JSONDecodeError, TypeError):
                continue

        return None

    def _find_product(self, data: Any) -> dict | None:
        """
        Find product data in JSON-LD structure.
        Handles @graph, nested structures, and direct products.
        """
        if isinstance(data, list):
            for item in data:
                result = self._find_product(item)
                if result:
                    return result
            return None

        if not isinstance(data, dict):
            return None

        # Check @graph
        if "@graph" in data:
            return self._find_product(data["@graph"])

        # Check if this is a product
        item_type = data.get("@type", "")
        if isinstance(item_type, list):
            item_type = item_type[0] if item_type else ""

        if item_type in JSON_LD_PRODUCT_TYPES:
            return data

        # Check nested mainEntity or mainEntityOfPage
        for key in ["mainEntity", "mainEntityOfPage"]:
            if key in data:
                result = self._find_product(data[key])
                if result:
                    return result

        return None

    def _parse_product(self, data: dict) -> ProductData:
        """Parse product data from JSON-LD dict."""
        result = ProductData(strategy_used=self.strategy_type)

        # Name
        result.name = sanitize_product_name(data.get("name", ""))

        # Brand
        brand = data.get("brand")
        if isinstance(brand, dict):
            result.brand = brand.get("name")
        elif isinstance(brand, str):
            result.brand = brand

        # UPC/SKU
        result.upc = data.get("gtin13") or data.get("gtin") or data.get("sku")

        # Image
        image = data.get("image")
        if isinstance(image, list):
            result.image_url = image[0] if image else None
        elif isinstance(image, dict):
            result.image_url = image.get("url")
        else:
            result.image_url = image

        # Price from offers
        offers = data.get("offers")
        if offers:
            self._parse_offers(offers, result)

        return result if result.name and result.price else result

    def _parse_offers(self, offers: Any, result: ProductData) -> None:
        """Parse price and availability from offers."""
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            return

        offer_type = offers.get("@type", "")

        # Handle AggregateOffer
        if offer_type == "AggregateOffer":
            # Use lowPrice for aggregate offers
            price_str = offers.get("lowPrice") or offers.get("price")
        else:
            price_str = offers.get("price")

        if price_str:
            result.price = normalize_price(str(price_str))

        # Currency
        result.currency = offers.get("priceCurrency", "CAD")

        # Availability
        availability = offers.get("availability", "")
        if isinstance(availability, str):
            availability_lower = availability.lower()
            result.in_stock = any(
                status in availability_lower
                for status in ["instock", "in stock", "available", "preorder", "pre-order"]
            )


class CssSelectorStrategy(BaseStrategy):
    """Extract product data using CSS selectors."""

    strategy_type = ExtractionStrategy.CSS_SELECTOR

    def extract(self, html: str, selectors: dict | None = None) -> ProductData | None:
        """Extract using CSS selectors."""
        if not selectors:
            return None

        soup = BeautifulSoup(html, "lxml")
        result = ProductData(strategy_used=self.strategy_type)

        # Extract price
        price_selectors = selectors.get("price", {}).get("css", [])
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                result.price = normalize_price(price_text)
                if result.price:
                    break

        # Extract name
        name_selectors = selectors.get("name", {}).get("css", [])
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                result.name = sanitize_product_name(element.get_text(strip=True))
                if result.name:
                    break

        # Extract original price (MSRP)
        original_price_selectors = selectors.get("original_price", {}).get("css", [])
        for selector in original_price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                result.original_price = normalize_price(price_text)
                if result.original_price:
                    break

        # Extract availability
        result.in_stock = self._extract_availability(soup, selectors)

        # Extract image
        image_selectors = selectors.get("image", {}).get("css", [])
        for selector in image_selectors:
            element = soup.select_one(selector)
            if element:
                result.image_url = element.get("src") or element.get("data-src")
                if result.image_url:
                    # Handle relative URLs
                    if result.image_url.startswith("//"):
                        result.image_url = "https:" + result.image_url
                    break

        # Return if we have minimum required data
        if result.name and result.price:
            return result

        return None

    def _extract_availability(self, soup: BeautifulSoup, selectors: dict) -> bool:
        """Extract availability status."""
        availability_config = selectors.get("availability", {})
        css_selectors = availability_config.get("css", [])
        in_stock_patterns = availability_config.get("in_stock_patterns", [])

        for selector in css_selectors:
            element = soup.select_one(selector)
            if element:
                # Check button text or element existence
                text = element.get_text(strip=True).lower()

                # Check against patterns
                for pattern in in_stock_patterns:
                    if pattern.lower() in text:
                        return True

                # If it's a button and exists, likely in stock
                if element.name == "button":
                    return True

        # Default to in stock if no clear indicator
        return True


class XPathStrategy(BaseStrategy):
    """Extract product data using XPath expressions."""

    strategy_type = ExtractionStrategy.XPATH

    def extract(self, html: str, selectors: dict | None = None) -> ProductData | None:
        """Extract using XPath expressions."""
        if not selectors:
            return None

        # Check if XPath selectors are provided
        xpath_selectors = selectors.get("xpath", {})
        if not xpath_selectors:
            return None

        try:
            from lxml import etree

            tree = etree.HTML(html)
            if tree is None:
                return None

            result = ProductData(strategy_used=self.strategy_type)

            # Extract price
            price_xpaths = xpath_selectors.get("price", [])
            for xpath in price_xpaths:
                elements = tree.xpath(xpath)
                if elements:
                    text = elements[0].text if hasattr(elements[0], "text") else str(elements[0])
                    result.price = normalize_price(text)
                    if result.price:
                        break

            # Extract name
            name_xpaths = xpath_selectors.get("name", [])
            for xpath in name_xpaths:
                elements = tree.xpath(xpath)
                if elements:
                    text = elements[0].text if hasattr(elements[0], "text") else str(elements[0])
                    result.name = sanitize_product_name(text)
                    if result.name:
                        break

            if result.name and result.price:
                return result

        except Exception:
            pass

        return None


class LlmExtractionStrategy(BaseStrategy):
    """
    Extract product data using LLM for unknown stores.
    This is the fallback when structured extraction fails.
    """

    strategy_type = ExtractionStrategy.LLM

    def __init__(self, llm_client=None):
        """
        Initialize with optional LLM client.

        Args:
            llm_client: Client for LLM API (OpenRouter)
        """
        self.llm_client = llm_client

    def extract(self, html: str, selectors: dict | None = None) -> ProductData | None:
        """
        Extract using LLM.
        Note: This requires an active LLM client. Returns None if not configured.
        """
        if not self.llm_client:
            return None

        # This will be implemented when we build the agent module
        # For now, return None as it requires LLM integration
        return None

    async def extract_async(self, html: str, url: str) -> ProductData | None:
        """
        Async extraction using LLM.

        Args:
            html: Page HTML
            url: Source URL for context

        Returns:
            ProductData if extraction successful
        """
        if not self.llm_client:
            return None

        # Clean HTML to reduce tokens (will be used when LLM integration is complete)
        # cleaned_html = self._clean_html_for_llm(html)

        # This will call the LLM with a structured prompt
        # Implementation deferred to agent module integration
        return None

    def _clean_html_for_llm(self, html: str, max_length: int = 50000) -> str:
        """
        Clean HTML to reduce token usage.
        Removes scripts, styles, and unnecessary content.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style tags
        for tag in soup(["script", "style", "noscript", "iframe", "svg", "path"]):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
            comment.extract()

        # Get text with some structure
        text = soup.get_text(separator="\n", strip=True)

        # Normalize whitespace
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        return text


# ===========================================
# Strategy Factory
# ===========================================


def get_extraction_strategies(llm_client=None) -> list[BaseStrategy]:
    """
    Get ordered list of extraction strategies.

    Args:
        llm_client: Optional LLM client for LLM strategy

    Returns:
        List of strategies in priority order
    """
    return [
        JsonLdStrategy(),
        CssSelectorStrategy(),
        XPathStrategy(),
        LlmExtractionStrategy(llm_client),
    ]
