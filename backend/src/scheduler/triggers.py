"""
Schedule trigger utilities for Perpee.

Handles CRON parsing, validation, and schedule management.
"""

from dataclasses import dataclass
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlmodel import Session, select

from src.database.models import Product, Schedule

# Minimum interval between scrapes (24 hours for MVP)
MIN_INTERVAL_HOURS = 24

# Default schedules
DEFAULT_CRON = "0 6 * * *"  # 6 AM UTC daily
WEEKLY_CRON = "0 6 * * 1"  # 6 AM UTC every Monday

# Valid CRON field ranges
CRON_FIELD_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "day_of_week": (0, 6),  # 0 = Monday in standard cron
}


@dataclass
class CronValidation:
    """Result of CRON expression validation."""

    valid: bool
    expression: str
    error: str | None = None
    next_run: datetime | None = None
    interval_hours: float | None = None


@dataclass
class ScheduleInfo:
    """Information about effective schedule for a product."""

    product_id: int
    cron_expression: str
    source: str  # "product", "store", or "system"
    schedule_id: int | None = None
    next_run: datetime | None = None


def validate_cron(expression: str) -> CronValidation:
    """
    Validate a CRON expression.

    Args:
        expression: CRON expression to validate (5 fields)

    Returns:
        CronValidation with result
    """
    expression = expression.strip()

    # Basic format check (5 fields)
    parts = expression.split()
    if len(parts) != 5:
        return CronValidation(
            valid=False,
            expression=expression,
            error=f"Expected 5 fields, got {len(parts)}",
        )

    # Try to parse with croniter
    try:
        cron = croniter(expression)
        next_run = cron.get_next(datetime)

        # Calculate approximate interval
        second_run = cron.get_next(datetime)
        interval = second_run - next_run
        interval_hours = interval.total_seconds() / 3600

        return CronValidation(
            valid=True,
            expression=expression,
            next_run=next_run,
            interval_hours=interval_hours,
        )

    except (ValueError, KeyError) as e:
        return CronValidation(
            valid=False,
            expression=expression,
            error=str(e),
        )


def validate_cron_with_minimum(
    expression: str,
    min_hours: int = MIN_INTERVAL_HOURS,
) -> CronValidation:
    """
    Validate CRON expression with minimum interval enforcement.

    Args:
        expression: CRON expression to validate
        min_hours: Minimum hours between runs

    Returns:
        CronValidation with result
    """
    validation = validate_cron(expression)

    if not validation.valid:
        return validation

    # Check minimum interval
    if validation.interval_hours and validation.interval_hours < min_hours:
        return CronValidation(
            valid=False,
            expression=expression,
            error=f"Interval {validation.interval_hours:.1f}h is below minimum {min_hours}h",
            interval_hours=validation.interval_hours,
        )

    return validation


def parse_cron_to_trigger(expression: str) -> CronTrigger | None:
    """
    Parse CRON expression to APScheduler trigger.

    Args:
        expression: CRON expression

    Returns:
        CronTrigger or None if invalid
    """
    try:
        return CronTrigger.from_crontab(expression)
    except (ValueError, KeyError):
        return None


def get_next_run_time(expression: str, base_time: datetime | None = None) -> datetime | None:
    """
    Get next run time for a CRON expression.

    Args:
        expression: CRON expression
        base_time: Base time (default: now)

    Returns:
        Next run datetime or None if invalid
    """
    try:
        base = base_time or datetime.utcnow()
        cron = croniter(expression, base)
        return cron.get_next(datetime)
    except (ValueError, KeyError):
        return None


def get_effective_schedule(
    session: Session,
    product_id: int,
) -> ScheduleInfo:
    """
    Get the effective schedule for a product.

    Priority: product schedule > store schedule > system default

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        ScheduleInfo with effective schedule
    """
    product = session.get(Product, product_id)
    if not product:
        return ScheduleInfo(
            product_id=product_id,
            cron_expression=DEFAULT_CRON,
            source="system",
        )

    # Check for product-specific schedule
    product_schedule = _get_product_schedule(session, product_id)
    if product_schedule:
        return ScheduleInfo(
            product_id=product_id,
            cron_expression=product_schedule.cron_expression,
            source="product",
            schedule_id=product_schedule.id,
            next_run=get_next_run_time(product_schedule.cron_expression),
        )

    # Check for store schedule
    store_schedule = _get_store_schedule(session, product.store_domain)
    if store_schedule:
        return ScheduleInfo(
            product_id=product_id,
            cron_expression=store_schedule.cron_expression,
            source="store",
            schedule_id=store_schedule.id,
            next_run=get_next_run_time(store_schedule.cron_expression),
        )

    # Fall back to system default
    return ScheduleInfo(
        product_id=product_id,
        cron_expression=DEFAULT_CRON,
        source="system",
        next_run=get_next_run_time(DEFAULT_CRON),
    )


def _get_product_schedule(session: Session, product_id: int) -> Schedule | None:
    """Get active schedule for a product."""
    stmt = (
        select(Schedule)
        .where(Schedule.product_id == product_id)
        .where(Schedule.is_active.is_(True))
        .where(Schedule.deleted_at.is_(None))
        .order_by(Schedule.created_at.desc())
        .limit(1)
    )
    return session.exec(stmt).first()


def _get_store_schedule(session: Session, domain: str) -> Schedule | None:
    """Get active schedule for a store."""
    stmt = (
        select(Schedule)
        .where(Schedule.store_domain == domain)
        .where(Schedule.product_id.is_(None))
        .where(Schedule.is_active.is_(True))
        .where(Schedule.deleted_at.is_(None))
        .order_by(Schedule.created_at.desc())
        .limit(1)
    )
    return session.exec(stmt).first()


def create_schedule(
    session: Session,
    cron_expression: str,
    product_id: int | None = None,
    store_domain: str | None = None,
    validate_minimum: bool = True,
) -> Schedule | None:
    """
    Create a new schedule.

    Args:
        session: Database session
        cron_expression: CRON expression
        product_id: Optional product ID (for product schedule)
        store_domain: Optional store domain (for store schedule)
        validate_minimum: Whether to enforce minimum interval

    Returns:
        Created Schedule or None if validation fails
    """
    if not product_id and not store_domain:
        raise ValueError("Either product_id or store_domain must be provided")

    # Validate CRON
    if validate_minimum:
        validation = validate_cron_with_minimum(cron_expression)
    else:
        validation = validate_cron(cron_expression)

    if not validation.valid:
        raise ValueError(f"Invalid CRON expression: {validation.error}")

    # Create schedule
    schedule = Schedule(
        product_id=product_id,
        store_domain=store_domain,
        cron_expression=cron_expression,
        is_active=True,
        next_run_at=validation.next_run,
    )

    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return schedule


def update_schedule_next_run(
    session: Session,
    schedule_id: int,
) -> bool:
    """
    Update a schedule's next_run_at time.

    Args:
        session: Database session
        schedule_id: Schedule to update

    Returns:
        True if updated
    """
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        return False

    schedule.last_run_at = datetime.utcnow()
    schedule.next_run_at = get_next_run_time(schedule.cron_expression)
    schedule.updated_at = datetime.utcnow()

    session.add(schedule)
    session.commit()

    return True


# ===========================================
# Human-Readable Schedule Descriptions
# ===========================================


def describe_cron(expression: str) -> str:
    """
    Convert CRON expression to human-readable description.

    Args:
        expression: CRON expression

    Returns:
        Human-readable description
    """
    parts = expression.split()
    if len(parts) != 5:
        return "Invalid schedule"

    minute, hour, day, month, dow = parts

    # Handle common patterns
    if expression == "0 6 * * *":
        return "Daily at 6:00 AM UTC"
    if expression == "0 0 * * *":
        return "Daily at midnight UTC"
    if expression == "0 6 * * 0":
        return "Weekly on Sunday at 6:00 AM UTC"
    if expression == "0 6 * * 1":
        return "Weekly on Monday at 6:00 AM UTC"

    # Build description
    desc_parts = []

    # Time
    if hour != "*" and minute != "*":
        time_str = f"{hour.zfill(2)}:{minute.zfill(2)} UTC"
        desc_parts.append(f"at {time_str}")

    # Day of week
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if dow != "*":
        if dow.isdigit():
            desc_parts.append(f"on {dow_names[int(dow)]}")
        else:
            desc_parts.append(f"on day {dow}")

    # Day of month
    if day != "*":
        desc_parts.append(f"on day {day}")

    # Month
    if month != "*":
        desc_parts.append(f"in month {month}")

    if not desc_parts:
        return "Custom schedule"

    return " ".join(desc_parts)


# ===========================================
# Predefined Schedule Options
# ===========================================

SCHEDULE_PRESETS = {
    "daily_morning": {
        "cron": "0 6 * * *",
        "description": "Daily at 6:00 AM UTC",
    },
    "daily_evening": {
        "cron": "0 18 * * *",
        "description": "Daily at 6:00 PM UTC",
    },
    "twice_daily": {
        "cron": "0 6,18 * * *",
        "description": "Twice daily at 6:00 AM and 6:00 PM UTC",
    },
    "weekly": {
        "cron": "0 6 * * 1",
        "description": "Weekly on Monday at 6:00 AM UTC",
    },
}


def get_preset_schedule(preset_name: str) -> dict | None:
    """
    Get a predefined schedule configuration.

    Args:
        preset_name: Name of preset

    Returns:
        Preset config or None
    """
    return SCHEDULE_PRESETS.get(preset_name)
