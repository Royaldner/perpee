"""
Alert API routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    AlertCreate,
    AlertListItem,
    AlertResponse,
    AlertUpdate,
    AlertWithProduct,
    MessageResponse,
    paginate,
)
from src.database.models import Alert, AlertType, Product

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=dict)
async def list_alerts(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    alert_type: AlertType | None = Query(None, description="Filter by alert type"),
    active_only: bool = Query(True, description="Only show active alerts"),
):
    """
    List all alerts with pagination.
    """
    # Build query
    query = select(Alert).where(Alert.deleted_at.is_(None))

    if product_id:
        query = query.where(Alert.product_id == product_id)

    if alert_type:
        query = query.where(Alert.alert_type == alert_type)

    if active_only:
        query = query.where(Alert.is_active.is_(True))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Alert.created_at.desc())

    result = await session.execute(query)
    alerts = result.scalars().all()

    items = [AlertListItem.model_validate(a) for a in alerts]
    return paginate(items, total, page, per_page)


@router.get("/{alert_id}", response_model=AlertWithProduct)
async def get_alert(
    alert_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get an alert by ID with product details.
    """
    alert = await session.get(Alert, alert_id)

    if not alert or alert.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    # Get product details
    product = await session.get(Product, alert.product_id)

    return AlertWithProduct(
        **AlertResponse.model_validate(alert).model_dump(),
        product_name=product.name if product else "Unknown",
        product_url=product.url if product else "",
        current_price=product.current_price if product else None,
        store_domain=product.store_domain if product else "",
    )


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new alert for a product.
    """
    # Verify product exists
    product = await session.get(Product, data.product_id)

    if not product or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {data.product_id} not found",
        )

    # Check for duplicate alert
    existing_query = select(Alert).where(
        Alert.product_id == data.product_id,
        Alert.alert_type == data.alert_type,
        Alert.is_active.is_(True),
        Alert.deleted_at.is_(None),
    )
    existing = (await session.execute(existing_query)).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Active {data.alert_type.value} alert already exists for this product",
        )

    # Create alert
    alert = Alert(
        product_id=data.product_id,
        alert_type=data.alert_type,
        target_value=data.target_value,
        min_change_threshold=data.min_change_threshold,
    )

    session.add(alert)
    await session.flush()
    await session.refresh(alert)

    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    data: AlertUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an alert.
    """
    alert = await session.get(Alert, alert_id)

    if not alert or alert.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(alert, key, value)

    await session.flush()
    await session.refresh(alert)

    return AlertResponse.model_validate(alert)


@router.delete("/{alert_id}", response_model=MessageResponse)
async def delete_alert(
    alert_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete an alert.
    """
    from datetime import datetime

    alert = await session.get(Alert, alert_id)

    if not alert or alert.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    alert.deleted_at = datetime.utcnow()
    await session.flush()

    return MessageResponse(message=f"Alert {alert_id} deleted")


@router.post("/{alert_id}/reset", response_model=AlertResponse)
async def reset_alert(
    alert_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reset a triggered alert so it can trigger again.
    """
    alert = await session.get(Alert, alert_id)

    if not alert or alert.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    alert.is_triggered = False
    alert.triggered_at = None
    alert.is_active = True

    await session.flush()
    await session.refresh(alert)

    return AlertResponse.model_validate(alert)
