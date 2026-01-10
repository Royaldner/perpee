"""
Template rendering utilities for email notifications.
Uses Jinja2 for HTML template rendering.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Template directory path
TEMPLATE_DIR = Path(__file__).parent


@dataclass
class RenderedEmail:
    """Rendered email content."""

    subject: str
    html: str
    text: str


class TemplateRenderer:
    """
    Renders email templates using Jinja2.

    Templates are loaded from the templates directory and rendered
    with provided context variables.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        """
        Initialize the template renderer.

        Args:
            template_dir: Directory containing templates. Defaults to this module's directory.
        """
        self._template_dir = template_dir or TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file.
            context: Variables to pass to the template.

        Returns:
            Rendered HTML string.
        """
        template = self._env.get_template(template_name)
        return template.render(**context)

    def render_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text for email clients that don't support HTML.

        Args:
            html: HTML content.

        Returns:
            Plain text version.
        """
        import re

        # Remove style and script tags with content
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)

        # Replace common block elements with newlines
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)

        # Extract link text with URL
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r"\2 (\1)", text)

        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode common HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')

        # Clean up whitespace
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()


# Singleton instance
_renderer = TemplateRenderer()


def render_price_alert(
    product_name: str,
    store_name: str,
    current_price: float,
    previous_price: float | None = None,
    original_price: float | None = None,
    product_url: str = "",
    image_url: str | None = None,
    alert_type: str = "price_drop",
    unsubscribe_url: str = "",
) -> RenderedEmail:
    """
    Render a price alert email.

    Args:
        product_name: Name of the product.
        store_name: Name of the store.
        current_price: Current price.
        previous_price: Previous tracked price.
        original_price: MSRP / "Was" price.
        product_url: URL to the product page.
        image_url: Product image URL.
        alert_type: Type of alert (price_drop, target_reached, any_change).
        unsubscribe_url: URL to manage alerts.

    Returns:
        RenderedEmail with subject, HTML, and text content.
    """
    # Calculate discount and drop amounts
    discount_percent = 0
    if original_price and original_price > current_price:
        discount_percent = round((1 - current_price / original_price) * 100)

    price_drop_amount = 0.0
    if previous_price and previous_price > current_price:
        price_drop_amount = round(previous_price - current_price, 2)

    # Map alert type to label
    alert_type_labels = {
        "price_drop": "Price Drop",
        "target_reached": "Target Price Reached",
        "any_change": "Price Changed",
        "percent_drop": "Price Drop",
    }
    alert_type_label = alert_type_labels.get(alert_type, "Price Alert")

    context = {
        "product_name": product_name,
        "store_name": store_name,
        "current_price": f"{current_price:.2f}",
        "previous_price": f"{previous_price:.2f}" if previous_price else None,
        "original_price": f"{original_price:.2f}" if original_price else None,
        "discount_percent": discount_percent,
        "price_drop_amount": f"{price_drop_amount:.2f}",
        "product_url": product_url,
        "image_url": image_url,
        "alert_type_label": alert_type_label,
        "unsubscribe_url": unsubscribe_url,
    }

    html = _renderer.render("price_alert.html", context)
    text = _renderer.render_to_text(html)

    subject = f"Price Alert: {product_name} is now ${current_price:.2f}"
    if price_drop_amount > 0:
        subject = f"Price Drop: {product_name} is now ${current_price:.2f} (Save ${price_drop_amount:.2f})"

    return RenderedEmail(subject=subject, html=html, text=text)


def render_back_in_stock(
    product_name: str,
    store_name: str,
    current_price: float,
    product_url: str = "",
    image_url: str | None = None,
    unsubscribe_url: str = "",
) -> RenderedEmail:
    """
    Render a back in stock alert email.

    Args:
        product_name: Name of the product.
        store_name: Name of the store.
        current_price: Current price.
        product_url: URL to the product page.
        image_url: Product image URL.
        unsubscribe_url: URL to manage alerts.

    Returns:
        RenderedEmail with subject, HTML, and text content.
    """
    context = {
        "product_name": product_name,
        "store_name": store_name,
        "current_price": f"{current_price:.2f}",
        "product_url": product_url,
        "image_url": image_url,
        "unsubscribe_url": unsubscribe_url,
    }

    html = _renderer.render("back_in_stock.html", context)
    text = _renderer.render_to_text(html)

    subject = f"Back in Stock: {product_name}"

    return RenderedEmail(subject=subject, html=html, text=text)


def render_product_error(
    product_name: str,
    store_name: str,
    error_type: str,
    error_message: str,
    product_url: str = "",
    dashboard_url: str = "",
    unsubscribe_url: str = "",
) -> RenderedEmail:
    """
    Render a product error notification email.

    Args:
        product_name: Name of the product.
        store_name: Name of the store.
        error_type: Type of error (e.g., "Product Not Found", "Page Unavailable").
        error_message: Detailed error message.
        product_url: URL to the product page.
        dashboard_url: URL to the dashboard.
        unsubscribe_url: URL to manage notifications.

    Returns:
        RenderedEmail with subject, HTML, and text content.
    """
    context = {
        "product_name": product_name,
        "store_name": store_name,
        "error_type": error_type,
        "error_message": error_message,
        "product_url": product_url,
        "dashboard_url": dashboard_url,
        "unsubscribe_url": unsubscribe_url,
    }

    html = _renderer.render("product_error.html", context)
    text = _renderer.render_to_text(html)

    subject = f"Tracking Issue: {product_name}"

    return RenderedEmail(subject=subject, html=html, text=text)


def render_store_flagged(
    store_name: str,
    store_domain: str,
    success_rate: float,
    products_affected: int,
    failed_scrapes: int,
    failure_reason: str,
    dashboard_url: str = "",
    unsubscribe_url: str = "",
) -> RenderedEmail:
    """
    Render a store health warning email.

    Args:
        store_name: Name of the store.
        store_domain: Store domain.
        success_rate: Success rate (0.0 to 1.0).
        products_affected: Number of products affected.
        failed_scrapes: Number of failed scrapes in last 7 days.
        failure_reason: Reason for failures.
        dashboard_url: URL to the dashboard.
        unsubscribe_url: URL to manage notifications.

    Returns:
        RenderedEmail with subject, HTML, and text content.
    """
    success_rate_percent = round(success_rate * 100)

    context = {
        "store_name": store_name,
        "store_domain": store_domain,
        "success_rate_percent": success_rate_percent,
        "products_affected": products_affected,
        "failed_scrapes": failed_scrapes,
        "failure_reason": failure_reason,
        "dashboard_url": dashboard_url,
        "unsubscribe_url": unsubscribe_url,
    }

    html = _renderer.render("store_flagged.html", context)
    text = _renderer.render_to_text(html)

    subject = f"Store Health Warning: {store_name} ({success_rate_percent}% success rate)"

    return RenderedEmail(subject=subject, html=html, text=text)
