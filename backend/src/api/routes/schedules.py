"""
Schedule API routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    MessageResponse,
    ScheduleCreate,
    ScheduleListItem,
    ScheduleResponse,
    ScheduleUpdate,
    ScheduleWithDetails,
    paginate,
)
from src.database.models import Product, Schedule, Store

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=dict)
async def list_schedules(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    store_domain: str | None = Query(None, description="Filter by store domain"),
    active_only: bool = Query(True, description="Only show active schedules"),
):
    """
    List all schedules with pagination.
    """
    # Build query
    query = select(Schedule).where(Schedule.deleted_at.is_(None))

    if product_id:
        query = query.where(Schedule.product_id == product_id)

    if store_domain:
        query = query.where(Schedule.store_domain == store_domain)

    if active_only:
        query = query.where(Schedule.is_active.is_(True))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Get paginated results
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Schedule.created_at.desc())

    result = await session.execute(query)
    schedules = result.scalars().all()

    items = [ScheduleListItem.model_validate(s) for s in schedules]
    return paginate(items, total, page, per_page)


@router.get("/{schedule_id}", response_model=ScheduleWithDetails)
async def get_schedule(
    schedule_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a schedule by ID with product/store details.
    """
    schedule = await session.get(Schedule, schedule_id)

    if not schedule or schedule.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    # Get product or store name
    product_name = None
    store_name = None

    if schedule.product_id:
        product = await session.get(Product, schedule.product_id)
        if product:
            product_name = product.name

    if schedule.store_domain:
        store = await session.get(Store, schedule.store_domain)
        if store:
            store_name = store.name

    return ScheduleWithDetails(
        **ScheduleResponse.model_validate(schedule).model_dump(),
        product_name=product_name,
        store_name=store_name,
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new schedule for a product or store.
    """
    # Verify product exists if product_id provided
    if data.product_id:
        product = await session.get(Product, data.product_id)
        if not product or product.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {data.product_id} not found",
            )

    # Verify store exists if store_domain provided
    if data.store_domain:
        store = await session.get(Store, data.store_domain)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store {data.store_domain} not found",
            )

    # Check for duplicate schedule
    existing_query = select(Schedule).where(Schedule.deleted_at.is_(None))

    if data.product_id:
        existing_query = existing_query.where(Schedule.product_id == data.product_id)
    else:
        existing_query = existing_query.where(Schedule.store_domain == data.store_domain)

    existing = (await session.execute(existing_query)).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule already exists for this product/store",
        )

    # Calculate next run time
    from datetime import datetime

    from croniter import croniter

    cron = croniter(data.cron_expression, datetime.utcnow())
    next_run_at = cron.get_next(datetime)

    # Create schedule
    schedule = Schedule(
        product_id=data.product_id,
        store_domain=data.store_domain,
        cron_expression=data.cron_expression,
        next_run_at=next_run_at,
    )

    session.add(schedule)
    await session.flush()
    await session.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a schedule.
    """
    schedule = await session.get(Schedule, schedule_id)

    if not schedule or schedule.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # If cron_expression changed, recalculate next_run_at
    if "cron_expression" in update_data:
        from datetime import datetime

        from croniter import croniter

        cron = croniter(update_data["cron_expression"], datetime.utcnow())
        schedule.next_run_at = cron.get_next(datetime)

    for key, value in update_data.items():
        setattr(schedule, key, value)

    await session.flush()
    await session.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}", response_model=MessageResponse)
async def delete_schedule(
    schedule_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete a schedule.
    """
    from datetime import datetime

    schedule = await session.get(Schedule, schedule_id)

    if not schedule or schedule.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    schedule.deleted_at = datetime.utcnow()
    await session.flush()

    return MessageResponse(message=f"Schedule {schedule_id} deleted")
