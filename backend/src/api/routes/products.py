"""
Product API routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    MessageResponse,
    PriceHistoryItem,
    ProductCreate,
    ProductListItem,
    ProductPriceHistory,
    ProductResponse,
    ProductStats,
    ProductUpdate,
    paginate,
)
from src.database.models import PriceHistory, Product, ProductStatus

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=dict)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    store: str | None = Query(None, description="Filter by store domain"),
    status_filter: ProductStatus | None = Query(None, alias="status", description="Filter by status"),
):
    """
    List all tracked products with pagination.
    """
    # Build query
    query = select(Product).where(Product.deleted_at.is_(None))

    if store:
        query = query.where(Product.store_domain == store)

    if status_filter:
        query = query.where(Product.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Product.updated_at.desc())

    result = await session.execute(query)
    products = result.scalars().all()

    items = [ProductListItem.model_validate(p) for p in products]
    return paginate(items, total, page, per_page)


@router.get("/stats", response_model=ProductStats)
async def get_product_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get product statistics.
    """
    # Total products
    total_query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    total = (await session.execute(total_query)).scalar_one()

    # Active products
    active_query = select(func.count(Product.id)).where(
        Product.deleted_at.is_(None),
        Product.status == ProductStatus.ACTIVE,
    )
    active = (await session.execute(active_query)).scalar_one()

    # Paused products
    paused_query = select(func.count(Product.id)).where(
        Product.deleted_at.is_(None),
        Product.status == ProductStatus.PAUSED,
    )
    paused = (await session.execute(paused_query)).scalar_one()

    # Needs attention
    attention_query = select(func.count(Product.id)).where(
        Product.deleted_at.is_(None),
        Product.status.in_([ProductStatus.NEEDS_ATTENTION, ProductStatus.PRICE_UNAVAILABLE]),
    )
    needs_attention = (await session.execute(attention_query)).scalar_one()

    # Products by store
    by_store_query = (
        select(Product.store_domain, func.count(Product.id))
        .where(Product.deleted_at.is_(None))
        .group_by(Product.store_domain)
    )
    by_store_result = await session.execute(by_store_query)
    by_store = {row[0]: row[1] for row in by_store_result}

    return ProductStats(
        total=total,
        active=active,
        paused=paused,
        needs_attention=needs_attention,
        by_store=by_store,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a product by ID.
    """
    product = await session.get(Product, product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    return ProductResponse.model_validate(product)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new product to track via URL.

    Note: This creates a placeholder product. The actual scraping
    is done via the agent or a background task.
    """
    from urllib.parse import urlparse

    # Extract domain from URL
    parsed = urlparse(str(data.url))
    store_domain = parsed.netloc.lower()

    # Remove www. prefix if present
    if store_domain.startswith("www."):
        store_domain = store_domain[4:]

    # Check if product already exists
    existing_query = select(Product).where(
        Product.url == str(data.url),
        Product.deleted_at.is_(None),
    )
    existing = (await session.execute(existing_query)).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with URL already exists (ID: {existing.id})",
        )

    # Create placeholder product
    product = Product(
        url=str(data.url),
        store_domain=store_domain,
        name="Pending...",  # Will be updated after scraping
        status=ProductStatus.ACTIVE,
    )

    session.add(product)
    await session.flush()
    await session.refresh(product)

    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a product.
    """
    product = await session.get(Product, product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await session.flush()
    await session.refresh(product)

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete a product.
    """
    from datetime import datetime

    product = await session.get(Product, product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    product.deleted_at = datetime.utcnow()
    await session.flush()

    return MessageResponse(message=f"Product {product_id} deleted")


@router.get("/{product_id}/history", response_model=ProductPriceHistory)
async def get_price_history(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(None, ge=1, le=365, description="Limit to last N days"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
):
    """
    Get price history for a product.
    """
    product = await session.get(Product, product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # Build history query
    query = select(PriceHistory).where(PriceHistory.product_id == product_id)

    if days:
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.where(PriceHistory.scraped_at >= cutoff)

    query = query.order_by(PriceHistory.scraped_at.desc()).limit(limit)

    result = await session.execute(query)
    history = result.scalars().all()

    return ProductPriceHistory(
        product=ProductResponse.model_validate(product),
        history=[PriceHistoryItem.model_validate(h) for h in history],
    )


@router.post("/{product_id}/refresh", response_model=MessageResponse)
async def refresh_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Trigger a manual scrape for a product.

    Note: This queues a scrape task. The actual scraping
    happens asynchronously.
    """
    product = await session.get(Product, product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # TODO: Queue scrape task via scheduler or agent
    # For now, just return acknowledgement

    return MessageResponse(message=f"Refresh queued for product {product_id}")
