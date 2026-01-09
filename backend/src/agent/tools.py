"""
Agent tools for Pydantic AI.
Implements all 10 tools for the price monitoring agent.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic_ai import RunContext

from src.core.exceptions import (
    RecordNotFoundError,
    ToolExecutionError,
    UnsupportedStoreError,
)
from src.core.security import extract_domain, validate_url
from src.database import repository
from src.database.models import (
    Alert,
    AlertType,
    Product,
    ProductStatus,
    Schedule,
)
from src.rag.search import SearchOptions

from .dependencies import AgentDependencies

logger = logging.getLogger(__name__)


# ===========================================
# Tool Result Types
# ===========================================


@dataclass
class ProductResult:
    """Result of a product operation."""

    success: bool
    product_id: int | None = None
    name: str = ""
    price: float | None = None
    store: str = ""
    message: str = ""
    url: str = ""


@dataclass
class SearchResult:
    """Result of a search operation."""

    products: list[dict[str, Any]]
    total: int
    query: str


@dataclass
class PriceHistoryResult:
    """Result of price history query."""

    product_id: int
    product_name: str
    history: list[dict[str, Any]]
    min_price: float | None = None
    max_price: float | None = None
    current_price: float | None = None


@dataclass
class AlertResult:
    """Result of alert operation."""

    success: bool
    alert_id: int | None = None
    message: str = ""


@dataclass
class ScheduleResult:
    """Result of schedule operation."""

    success: bool
    schedule_id: int | None = None
    message: str = ""


@dataclass
class CompareResult:
    """Result of price comparison."""

    product_name: str
    prices: list[dict[str, Any]]
    lowest_price: float | None = None
    lowest_store: str = ""


# ===========================================
# Tool Implementations
# ===========================================


async def scrape_product(
    ctx: RunContext[AgentDependencies],
    url: str,
) -> ProductResult:
    """
    Scrape a product from URL and add it to tracking.

    Args:
        ctx: Run context with dependencies
        url: Product page URL

    Returns:
        ProductResult with product details or error
    """
    try:
        # Validate URL
        url = validate_url(url)
        domain = extract_domain(url)

        # Check if product already exists
        existing = await repository.get_product_by_url(ctx.deps.session, url)
        if existing:
            return ProductResult(
                success=True,
                product_id=existing.id,
                name=existing.name,
                price=existing.current_price,
                store=existing.store_domain,
                message="Product is already being tracked",
                url=url,
            )

        # Check if store is whitelisted
        store = await repository.get_store_by_domain(ctx.deps.session, domain)
        if not store or not store.is_whitelisted:
            return ProductResult(
                success=False,
                message=f"Store '{domain}' is not supported. Use scan_website first to analyze unknown stores.",
                url=url,
            )

        # Scrape the product
        result = await ctx.deps.scraper.scrape(url)

        if not result.success or not result.product:
            return ProductResult(
                success=False,
                message=f"Failed to scrape product: {result.error_message}",
                url=url,
            )

        # Create product in database
        product = Product(
            url=url,
            store_domain=domain,
            name=result.product.name,
            brand=result.product.brand,
            current_price=result.product.price,
            original_price=result.product.original_price,
            in_stock=result.product.in_stock,
            image_url=result.product.image_url,
            status=ProductStatus.ACTIVE,
            last_checked_at=datetime.utcnow(),
        )

        product = await repository.create(ctx.deps.session, product)

        # Add initial price history
        await repository.add_price_history(
            ctx.deps.session,
            product_id=product.id,
            price=product.current_price,
            original_price=product.original_price,
            in_stock=product.in_stock,
        )

        # Index in RAG
        await ctx.deps.sync_service.index_product(product)

        await ctx.deps.session.commit()

        logger.info(f"Added product {product.id}: {product.name}")

        return ProductResult(
            success=True,
            product_id=product.id,
            name=product.name,
            price=product.current_price,
            store=domain,
            message="Product is now being tracked!",
            url=url,
        )

    except UnsupportedStoreError as e:
        return ProductResult(success=False, message=str(e), url=url)
    except Exception as e:
        logger.error(f"Error scraping product: {e}")
        raise ToolExecutionError("scrape_product", str(e)) from e


async def scan_website(
    ctx: RunContext[AgentDependencies],
    url: str,
) -> dict[str, Any]:
    """
    Analyze an unknown website to determine if it can be scraped.

    Args:
        ctx: Run context with dependencies
        url: URL to analyze

    Returns:
        Analysis results including whether the site can be tracked
    """
    try:
        url = validate_url(url)
        domain = extract_domain(url)

        # Check if already whitelisted
        store = await repository.get_store_by_domain(ctx.deps.session, domain)
        if store and store.is_whitelisted:
            return {
                "success": True,
                "domain": domain,
                "is_supported": True,
                "message": f"{store.name} is already a supported store!",
            }

        # Try to scrape with LLM extraction
        result = await ctx.deps.scraper.scrape(url, validate_ssrf=True)

        if result.success and result.product:
            return {
                "success": True,
                "domain": domain,
                "is_supported": True,
                "product_found": True,
                "product_name": result.product.name,
                "product_price": result.product.price,
                "strategy_used": result.strategy_used.value if result.strategy_used else None,
                "message": "Website appears to be scrapeable. You can track products from this site.",
            }

        return {
            "success": False,
            "domain": domain,
            "is_supported": False,
            "error": result.error_message,
            "message": "Could not extract product data. This site may not be compatible.",
        }

    except Exception as e:
        logger.error(f"Error scanning website: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to analyze website.",
        }


async def search_products(
    ctx: RunContext[AgentDependencies],
    query: str,
    store: str | None = None,
    limit: int = 10,
) -> SearchResult:
    """
    Search tracked products using semantic search.

    Args:
        ctx: Run context with dependencies
        query: Search query
        store: Optional store domain filter
        limit: Maximum results (default 10)

    Returns:
        SearchResult with matching products
    """
    try:
        options = SearchOptions(
            limit=min(limit, 50),
            store_domain=store,
        )

        results = await ctx.deps.search_service.search(
            query=query,
            session=ctx.deps.session,
            options=options,
        )

        products = [
            {
                "id": r.product_id,
                "name": r.name,
                "store": r.store_domain,
                "price": r.current_price,
                "in_stock": r.in_stock,
            }
            for r in results
        ]

        return SearchResult(
            products=products,
            total=len(products),
            query=query,
        )

    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise ToolExecutionError("search_products", str(e)) from e


async def web_search(
    ctx: RunContext[AgentDependencies],
    query: str,
) -> list[dict[str, Any]]:
    """
    Search the web for product URLs using DuckDuckGo.

    Args:
        ctx: Run context with dependencies
        query: Search query

    Returns:
        List of search results with URLs
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text(
                f"{query} site:amazon.ca OR site:bestbuy.ca OR site:walmart.ca",
                max_results=5,
            )
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "description": r.get("body", ""),
                })

        return results

    except ImportError:
        logger.warning("duckduckgo_search not installed, web search unavailable")
        return []
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return []


async def get_price_history(
    ctx: RunContext[AgentDependencies],
    product_id: int,
    days: int | None = 30,
) -> PriceHistoryResult:
    """
    Get price history for a product.

    Args:
        ctx: Run context with dependencies
        product_id: Product ID
        days: Number of days of history (default 30)

    Returns:
        PriceHistoryResult with price history
    """
    try:
        # Get product
        product = await repository.get_by_id(ctx.deps.session, Product, product_id)
        if not product:
            raise RecordNotFoundError("Product", product_id)

        # Get history
        history = await repository.get_price_history(
            ctx.deps.session,
            product_id=product_id,
            days=days,
            limit=100,
        )

        history_data = [
            {
                "price": h.price,
                "original_price": h.original_price,
                "in_stock": h.in_stock,
                "date": h.scraped_at.isoformat(),
            }
            for h in history
        ]

        prices = [h.price for h in history if h.price is not None]

        return PriceHistoryResult(
            product_id=product_id,
            product_name=product.name,
            history=history_data,
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            current_price=product.current_price,
        )

    except RecordNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        raise ToolExecutionError("get_price_history", str(e)) from e


async def create_schedule(
    ctx: RunContext[AgentDependencies],
    product_id: int,
    cron_expression: str,
) -> ScheduleResult:
    """
    Create a monitoring schedule for a product.

    Args:
        ctx: Run context with dependencies
        product_id: Product ID
        cron_expression: Cron expression (e.g., "0 6 * * *" for 6 AM daily)

    Returns:
        ScheduleResult
    """
    try:
        # Validate product exists
        product = await repository.get_by_id(ctx.deps.session, Product, product_id)
        if not product:
            raise RecordNotFoundError("Product", product_id)

        # Validate cron expression
        from croniter import croniter

        if not croniter.is_valid(cron_expression):
            return ScheduleResult(
                success=False,
                message=f"Invalid cron expression: {cron_expression}",
            )

        # Calculate next run time
        cron = croniter(cron_expression, datetime.utcnow())
        next_run = cron.get_next(datetime)

        # Create schedule
        schedule = Schedule(
            product_id=product_id,
            cron_expression=cron_expression,
            is_active=True,
            next_run_at=next_run,
        )

        schedule = await repository.create(ctx.deps.session, schedule)
        await ctx.deps.session.commit()

        return ScheduleResult(
            success=True,
            schedule_id=schedule.id,
            message=f"Schedule created. Next check: {next_run.strftime('%Y-%m-%d %H:%M UTC')}",
        )

    except RecordNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise ToolExecutionError("create_schedule", str(e)) from e


async def set_alert(
    ctx: RunContext[AgentDependencies],
    product_id: int,
    alert_type: str,
    target_value: float | None = None,
) -> AlertResult:
    """
    Create a price alert for a product.

    Args:
        ctx: Run context with dependencies
        product_id: Product ID
        alert_type: Type of alert (target_price, percent_drop, any_change, back_in_stock)
        target_value: Target value for target_price or percent_drop alerts

    Returns:
        AlertResult
    """
    try:
        # Validate product exists
        product = await repository.get_by_id(ctx.deps.session, Product, product_id)
        if not product:
            raise RecordNotFoundError("Product", product_id)

        # Validate alert type
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            valid_types = [t.value for t in AlertType]
            return AlertResult(
                success=False,
                message=f"Invalid alert type. Valid types: {', '.join(valid_types)}",
            )

        # Validate target value
        if alert_type_enum in (AlertType.TARGET_PRICE, AlertType.PERCENT_DROP):
            if target_value is None:
                return AlertResult(
                    success=False,
                    message=f"target_value is required for {alert_type} alerts",
                )
            if target_value <= 0:
                return AlertResult(
                    success=False,
                    message="target_value must be positive",
                )

        # Create alert
        alert = Alert(
            product_id=product_id,
            alert_type=alert_type_enum,
            target_value=target_value,
            is_active=True,
        )

        alert = await repository.create(ctx.deps.session, alert)
        await ctx.deps.session.commit()

        # Build confirmation message
        if alert_type_enum == AlertType.TARGET_PRICE:
            msg = f"Alert set! You'll be notified when price drops to ${target_value:.2f} or below."
        elif alert_type_enum == AlertType.PERCENT_DROP:
            msg = f"Alert set! You'll be notified when price drops by {target_value:.0f}% or more."
        elif alert_type_enum == AlertType.ANY_CHANGE:
            msg = "Alert set! You'll be notified of any price change."
        else:
            msg = "Alert set! You'll be notified when this item is back in stock."

        return AlertResult(
            success=True,
            alert_id=alert.id,
            message=msg,
        )

    except RecordNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise ToolExecutionError("set_alert", str(e)) from e


async def compare_prices(
    ctx: RunContext[AgentDependencies],
    canonical_id: int,
) -> CompareResult:
    """
    Compare prices across stores for the same product.

    Args:
        ctx: Run context with dependencies
        canonical_id: Canonical product ID

    Returns:
        CompareResult with prices from all stores
    """
    try:
        # Get all products linked to this canonical product
        products = await repository.get_products_for_canonical(
            ctx.deps.session,
            canonical_id=canonical_id,
        )

        if not products:
            return CompareResult(
                product_name="Unknown",
                prices=[],
                message="No products found for this canonical ID",
            )

        prices = []
        lowest_price = None
        lowest_store = ""
        product_name = products[0].name

        for product in products:
            if product.current_price is not None:
                prices.append({
                    "store": product.store_domain,
                    "price": product.current_price,
                    "in_stock": product.in_stock,
                    "url": product.url,
                })

                if product.in_stock and (
                    lowest_price is None or product.current_price < lowest_price
                ):
                    lowest_price = product.current_price
                    lowest_store = product.store_domain

        return CompareResult(
            product_name=product_name,
            prices=prices,
            lowest_price=lowest_price,
            lowest_store=lowest_store,
        )

    except Exception as e:
        logger.error(f"Error comparing prices: {e}")
        raise ToolExecutionError("compare_prices", str(e)) from e


async def list_products(
    ctx: RunContext[AgentDependencies],
    store: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    List tracked products.

    Args:
        ctx: Run context with dependencies
        store: Optional store domain filter
        limit: Maximum results (default 20)

    Returns:
        List of product summaries
    """
    try:
        if store:
            products = await repository.get_products_by_store(
                ctx.deps.session,
                store_domain=store,
                limit=min(limit, 100),
            )
        else:
            products = await repository.get_all(
                ctx.deps.session,
                Product,
                limit=min(limit, 100),
            )

        return [
            {
                "id": p.id,
                "name": p.name,
                "store": p.store_domain,
                "price": p.current_price,
                "original_price": p.original_price,
                "in_stock": p.in_stock,
                "status": p.status.value,
                "last_checked": p.last_checked_at.isoformat() if p.last_checked_at else None,
            }
            for p in products
        ]

    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise ToolExecutionError("list_products", str(e)) from e


async def remove_product(
    ctx: RunContext[AgentDependencies],
    product_id: int,
) -> ProductResult:
    """
    Stop tracking a product (soft delete).

    Args:
        ctx: Run context with dependencies
        product_id: Product ID

    Returns:
        ProductResult
    """
    try:
        product = await repository.get_by_id(ctx.deps.session, Product, product_id)
        if not product:
            raise RecordNotFoundError("Product", product_id)

        product_name = product.name

        # Soft delete
        await repository.soft_delete(ctx.deps.session, product)

        # Remove from RAG index
        ctx.deps.sync_service.remove_product(product_id)

        await ctx.deps.session.commit()

        return ProductResult(
            success=True,
            product_id=product_id,
            name=product_name,
            message=f"Stopped tracking '{product_name}'",
        )

    except RecordNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error removing product: {e}")
        raise ToolExecutionError("remove_product", str(e)) from e
