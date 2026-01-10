"""
Alert API schemas.
"""

from datetime import datetime

from pydantic import Field, field_validator

from src.api.schemas.common import BaseSchema, TimestampMixin
from src.database.models import AlertType


class AlertCreate(BaseSchema):
    """Schema for creating an alert."""

    product_id: int = Field(..., description="Product ID to create alert for")
    alert_type: AlertType = Field(..., description="Type of alert")
    target_value: float | None = Field(
        None,
        description="Target value (price for target_price, percentage for percent_drop)",
    )
    min_change_threshold: float = Field(
        default=1.0,
        ge=0,
        description="Minimum change to trigger (default $1 or 1%)",
    )

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, v: float | None, info) -> float | None:
        """Validate target_value based on alert_type."""
        alert_type = info.data.get("alert_type")

        if alert_type in [AlertType.TARGET_PRICE, AlertType.PERCENT_DROP]:
            if v is None:
                raise ValueError(f"{alert_type.value} requires a target_value")
            if v <= 0:
                raise ValueError("target_value must be positive")

        return v


class AlertUpdate(BaseSchema):
    """Schema for updating an alert."""

    target_value: float | None = Field(None, description="New target value")
    min_change_threshold: float | None = Field(
        None,
        ge=0,
        description="Minimum change threshold",
    )
    is_active: bool | None = Field(None, description="Whether alert is active")


class AlertBase(BaseSchema):
    """Base alert fields."""

    id: int
    product_id: int
    alert_type: AlertType
    target_value: float | None = None
    min_change_threshold: float = 1.0
    is_active: bool = True
    is_triggered: bool = False
    triggered_at: datetime | None = None


class AlertResponse(AlertBase, TimestampMixin):
    """Full alert response."""

    pass


class AlertListItem(BaseSchema):
    """Condensed alert for list views."""

    id: int
    product_id: int
    alert_type: AlertType
    target_value: float | None = None
    is_active: bool
    is_triggered: bool
    triggered_at: datetime | None = None


class AlertWithProduct(AlertResponse):
    """Alert with product info."""

    product_name: str
    product_url: str
    current_price: float | None = None
    store_domain: str
