"""
Schedule API schemas.
"""

from datetime import datetime

from pydantic import Field, field_validator

from src.api.schemas.common import BaseSchema, TimestampMixin


def validate_cron_expression(cron: str) -> str:
    """Validate a CRON expression."""
    from croniter import croniter

    try:
        croniter(cron)
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid CRON expression: {e}") from e

    return cron


class ScheduleCreate(BaseSchema):
    """Schema for creating a schedule."""

    product_id: int | None = Field(
        None,
        description="Product ID (for product-specific schedule)",
    )
    store_domain: str | None = Field(
        None,
        max_length=255,
        description="Store domain (for store-wide schedule)",
    )
    cron_expression: str = Field(
        ...,
        max_length=100,
        description="CRON expression (e.g., '0 6 * * *' for daily at 6 AM)",
    )

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate CRON expression."""
        return validate_cron_expression(v)

    @field_validator("store_domain")
    @classmethod
    def validate_schedule_target(cls, v: str | None, info) -> str | None:
        """Ensure at least one of product_id or store_domain is set."""
        product_id = info.data.get("product_id")
        if product_id is None and v is None:
            raise ValueError("Either product_id or store_domain must be provided")
        if product_id is not None and v is not None:
            raise ValueError("Cannot set both product_id and store_domain")
        return v


class ScheduleUpdate(BaseSchema):
    """Schema for updating a schedule."""

    cron_expression: str | None = Field(
        None,
        max_length=100,
        description="New CRON expression",
    )
    is_active: bool | None = Field(None, description="Whether schedule is active")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        """Validate CRON expression if provided."""
        if v is not None:
            return validate_cron_expression(v)
        return v


class ScheduleBase(BaseSchema):
    """Base schedule fields."""

    id: int
    product_id: int | None = None
    store_domain: str | None = None
    cron_expression: str
    is_active: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class ScheduleResponse(ScheduleBase, TimestampMixin):
    """Full schedule response."""

    pass


class ScheduleListItem(BaseSchema):
    """Condensed schedule for list views."""

    id: int
    product_id: int | None = None
    store_domain: str | None = None
    cron_expression: str
    is_active: bool
    next_run_at: datetime | None = None


class ScheduleWithDetails(ScheduleResponse):
    """Schedule with product/store details."""

    product_name: str | None = None
    store_name: str | None = None
