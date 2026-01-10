"""
Store API routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    StoreHealth,
    StoreListItem,
    StoreResponse,
    StoreStats,
    SupportedStoresResponse,
)
from src.database.models import Product, ProductStatus, Store

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=SupportedStoresResponse)
async def list_stores(
    session: Annotated[AsyncSession, Depends(get_db)],
    whitelisted_only: bool = Query(True, description="Only show pre-configured stores"),
):
    """
    List all supported stores with product counts.
    """
    # Get stores
    query = select(Store).where(Store.is_active.is_(True))

    if whitelisted_only:
        query = query.where(Store.is_whitelisted.is_(True))

    query = query.order_by(Store.name)
    result = await session.execute(query)
    stores = result.scalars().all()

    # Get product counts per store
    product_counts_query = (
        select(Product.store_domain, func.count(Product.id))
        .where(Product.deleted_at.is_(None))
        .group_by(Product.store_domain)
    )
    product_counts_result = await session.execute(product_counts_query)
    product_counts = {row[0]: row[1] for row in product_counts_result}

    items = [
        StoreListItem(
            domain=store.domain,
            name=store.name,
            is_whitelisted=store.is_whitelisted,
            is_active=store.is_active,
            success_rate=store.success_rate,
            product_count=product_counts.get(store.domain, 0),
        )
        for store in stores
    ]

    return SupportedStoresResponse(stores=items, total=len(items))


@router.get("/stats", response_model=StoreStats)
async def get_store_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get store statistics.
    """
    # Total stores
    total_query = select(func.count(Store.domain))
    total = (await session.execute(total_query)).scalar_one()

    # Whitelisted stores
    whitelisted_query = select(func.count(Store.domain)).where(Store.is_whitelisted.is_(True))
    whitelisted = (await session.execute(whitelisted_query)).scalar_one()

    # Healthy stores (success_rate > 0.5)
    healthy_query = select(func.count(Store.domain)).where(
        Store.is_active.is_(True),
        Store.success_rate > 0.5,
    )
    healthy = (await session.execute(healthy_query)).scalar_one()

    # Unhealthy stores
    unhealthy_query = select(func.count(Store.domain)).where(
        Store.is_active.is_(True),
        Store.success_rate <= 0.5,
    )
    unhealthy = (await session.execute(unhealthy_query)).scalar_one()

    return StoreStats(
        total=total,
        whitelisted=whitelisted,
        healthy=healthy,
        unhealthy=unhealthy,
    )


@router.get("/{store_domain}", response_model=StoreResponse)
async def get_store(
    store_domain: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a store by domain.
    """
    store = await session.get(Store, store_domain)

    if not store:
        raise HTTPException(
            status_code=404,
            detail=f"Store {store_domain} not found",
        )

    # Don't expose selectors for security
    response = StoreResponse.model_validate(store)
    response.selectors = None

    return response


@router.get("/{store_domain}/health", response_model=StoreHealth)
async def get_store_health(
    store_domain: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get health information for a store.
    """
    store = await session.get(Store, store_domain)

    if not store:
        raise HTTPException(
            status_code=404,
            detail=f"Store {store_domain} not found",
        )

    # Count products for this store
    product_count_query = select(func.count(Product.id)).where(
        Product.store_domain == store_domain,
        Product.deleted_at.is_(None),
    )
    product_count = (await session.execute(product_count_query)).scalar_one()

    # Count failed products
    failed_query = select(func.count(Product.id)).where(
        Product.store_domain == store_domain,
        Product.deleted_at.is_(None),
        Product.status.in_([ProductStatus.ERROR, ProductStatus.NEEDS_ATTENTION]),
    )
    failed_products = (await session.execute(failed_query)).scalar_one()

    return StoreHealth(
        domain=store.domain,
        name=store.name,
        success_rate=store.success_rate,
        is_healthy=store.success_rate > 0.5,
        product_count=product_count,
        failed_products=failed_products,
        last_success_at=store.last_success_at,
        last_failure_reason=None,  # TODO: Get from scrape logs
    )
