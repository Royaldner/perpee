"""
LLM-based selector regeneration for self-healing.

Uses LLM to analyze HTML and generate new CSS selectors when existing ones break.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from sqlmodel import Session

from config.settings import settings
from src.database.models import Store

logger = logging.getLogger(__name__)

# Load regeneration prompt template
PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


def load_regeneration_prompt() -> str:
    """Load selector regeneration prompt from file or use default."""
    prompt_file = PROMPTS_DIR / "regenerate_selectors.txt"
    if prompt_file.exists():
        return prompt_file.read_text()

    # Default prompt if file not found
    return """You are a web scraping expert. Analyze the HTML content and generate CSS selectors
to extract product information (price, name, availability, image, original price).

For each field, provide an array of CSS selectors in order of preference.
Return a JSON object with the selector configuration."""


@dataclass
class RegenerationResult:
    """Result of selector regeneration attempt."""

    success: bool
    domain: str
    selectors: dict | None = None
    error: str | None = None
    confidence: float = 0.0
    attempts_used: int = 0


@dataclass
class SelectorConfig:
    """Validated selector configuration."""

    price: list[str]
    name: list[str]
    availability: list[str]
    image: list[str] | None = None
    original_price: list[str] | None = None
    wait_for: str | None = None
    json_ld: bool = False


class SelectorRegenerator:
    """
    LLM-based CSS selector regeneration.

    Analyzes HTML content to generate new selectors when existing ones break.
    Uses the same LLM configuration as the main agent.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        min_confidence: float = 0.7,
    ):
        """
        Initialize selector regenerator.

        Args:
            max_attempts: Maximum regeneration attempts per product
            min_confidence: Minimum confidence score to accept selectors
        """
        self.max_attempts = max_attempts
        self.min_confidence = min_confidence

        # Initialize LLM model (using OpenRouter like the main agent)
        self._model = OpenAIModel(
            settings.primary_model,
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )

        # Create agent for selector regeneration
        self._agent = Agent(
            model=self._model,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for selector regeneration."""
        return """You are a web scraping expert specializing in e-commerce product pages.

Your task is to analyze HTML content and generate reliable CSS selectors for extracting product data.

## Guidelines

1. **Prioritize Stable Selectors**
   - Prefer semantic HTML attributes (data-*, itemprop, aria-*)
   - Use ID selectors when unique and descriptive
   - Avoid positional selectors (:nth-child) when possible
   - Look for consistent patterns across similar elements

2. **Multiple Fallbacks**
   - Provide 2-4 selectors per field in order of preference
   - First selector should be most specific/reliable
   - Later selectors should be progressively more general

3. **Price Selectors**
   - Target the final/sale price, not original/MSRP
   - Handle currency symbols and formatting
   - Check for "sale", "now", "current" price containers

4. **Availability Selectors**
   - Look for "Add to Cart" buttons
   - Check for out-of-stock indicators
   - Note common patterns: inventory status, shipping info

5. **Response Format**
   Return valid JSON only:
   ```json
   {
     "selectors": {
       "price": {"css": ["selector1", "selector2"]},
       "name": {"css": ["selector1", "selector2"]},
       "availability": {"css": ["selector1"], "in_stock_patterns": ["in stock"]},
       "image": {"css": ["selector1"]},
       "original_price": {"css": ["selector1"]},
       "wait_for": "main-selector-to-wait-for"
     },
     "confidence": 0.85,
     "notes": "Brief explanation of selector choices"
   }
   ```"""

    async def regenerate(
        self,
        html: str,
        domain: str,
        current_selectors: dict | None = None,
    ) -> RegenerationResult:
        """
        Regenerate CSS selectors from HTML content.

        Args:
            html: HTML content of the page
            domain: Store domain
            current_selectors: Current (broken) selectors for context

        Returns:
            RegenerationResult with new selectors or error
        """
        # Truncate HTML to reasonable size for LLM
        truncated_html = self._truncate_html(html)

        # Build prompt
        prompt = self._build_regeneration_prompt(
            truncated_html, domain, current_selectors
        )

        try:
            # Run LLM agent
            result = await self._agent.run(prompt)

            # Parse response
            parsed = self._parse_response(result.data)

            if parsed and parsed.get("selectors"):
                confidence = parsed.get("confidence", 0.5)

                if confidence >= self.min_confidence:
                    return RegenerationResult(
                        success=True,
                        domain=domain,
                        selectors=parsed["selectors"],
                        confidence=confidence,
                    )
                else:
                    return RegenerationResult(
                        success=False,
                        domain=domain,
                        error=f"Low confidence: {confidence:.2f}",
                        confidence=confidence,
                    )

            return RegenerationResult(
                success=False,
                domain=domain,
                error="Failed to parse selector response",
            )

        except Exception as e:
            logger.error(f"Selector regeneration failed for {domain}: {e}")
            return RegenerationResult(
                success=False,
                domain=domain,
                error=str(e),
            )

    def _truncate_html(self, html: str, max_chars: int = 50000) -> str:
        """
        Truncate HTML to reasonable size for LLM processing.

        Tries to preserve product-relevant sections.
        """
        if len(html) <= max_chars:
            return html

        # Try to find and extract product-relevant sections
        # Look for common product container patterns
        product_markers = [
            '<main',
            'class="product',
            'id="product',
            'itemtype="http://schema.org/Product',
            'data-product',
        ]

        for marker in product_markers:
            idx = html.lower().find(marker.lower())
            if idx != -1:
                # Extract section around the marker
                start = max(0, idx - 1000)
                end = min(len(html), idx + max_chars - 1000)
                return html[start:end]

        # Fallback: just truncate from the start
        return html[:max_chars]

    def _build_regeneration_prompt(
        self,
        html: str,
        domain: str,
        current_selectors: dict | None,
    ) -> str:
        """Build the regeneration prompt with context."""
        prompt_parts = [
            f"Analyze this HTML from {domain} and generate CSS selectors for product data extraction.",
            "",
        ]

        if current_selectors:
            prompt_parts.extend([
                "## Current (Broken) Selectors",
                "These selectors are no longer working:",
                f"```json\n{json.dumps(current_selectors, indent=2)}\n```",
                "",
            ])

        prompt_parts.extend([
            "## HTML Content",
            "```html",
            html,
            "```",
            "",
            "Generate new CSS selectors that will reliably extract product data from this page.",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, response: str) -> dict | None:
        """Parse LLM response to extract selector configuration."""
        try:
            # Try to find JSON in response
            response = response.strip()

            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end > start:
                    response = response[start:end]

            return json.loads(response.strip())

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse selector response: {e}")
            return None

    def validate_selectors(self, selectors: dict) -> SelectorConfig | None:
        """
        Validate selector configuration.

        Args:
            selectors: Raw selector dict from LLM

        Returns:
            SelectorConfig if valid, None otherwise
        """
        try:
            # Extract required fields
            price = selectors.get("price", {}).get("css", [])
            name = selectors.get("name", {}).get("css", [])
            availability = selectors.get("availability", {}).get("css", [])

            if not price or not name or not availability:
                return None

            # Extract optional fields
            image = selectors.get("image", {}).get("css")
            original_price = selectors.get("original_price", {}).get("css")
            wait_for = selectors.get("wait_for")
            json_ld = selectors.get("json_ld", False)

            return SelectorConfig(
                price=price,
                name=name,
                availability=availability,
                image=image,
                original_price=original_price,
                wait_for=wait_for,
                json_ld=json_ld,
            )

        except Exception as e:
            logger.warning(f"Selector validation failed: {e}")
            return None

    async def update_store_selectors(
        self,
        session: Session,
        domain: str,
        new_selectors: dict,
    ) -> bool:
        """
        Update store selectors in database.

        Args:
            session: Database session
            domain: Store domain
            new_selectors: New selector configuration

        Returns:
            True if update successful
        """
        try:
            store = session.get(Store, domain)
            if not store:
                logger.warning(f"Store not found: {domain}")
                return False

            # Merge with existing selectors, preserving non-CSS config
            existing = store.selectors or {}
            merged = {**existing, **new_selectors}

            store.selectors = merged
            store.updated_at = datetime.utcnow()

            session.add(store)
            session.commit()

            logger.info(f"Updated selectors for store: {domain}")
            return True

        except Exception as e:
            logger.error(f"Failed to update store selectors: {e}")
            session.rollback()
            return False


# ===========================================
# Convenience Functions
# ===========================================

_selector_regenerator: SelectorRegenerator | None = None


def get_selector_regenerator() -> SelectorRegenerator:
    """Get the global selector regenerator instance."""
    global _selector_regenerator
    if _selector_regenerator is None:
        _selector_regenerator = SelectorRegenerator()
    return _selector_regenerator
