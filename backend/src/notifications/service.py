"""
NotificationService for orchestrating email notifications.
Handles alert evaluation, duplicate prevention, and notification logging.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.database.models import (
    Alert,
    AlertType,
    Notification,
    NotificationChannel,
    NotificationStatus,
    Product,
    Store,
)
from src.notifications.channels.email import EmailChannel
from src.notifications.templates import (
    render_back_in_stock,
    render_price_alert,
    render_product_error,
    render_store_flagged,
)

logger = logging.getLogger(__name__)


@dataclass
class AlertEvaluationResult:
    """Result of evaluating an alert condition."""

    triggered: bool
    alert_type: AlertType
    alert_id: int
    reason: str | None = None


@dataclass
class NotificationResult:
    """Result of sending a notification."""

    success: bool
    notification_id: int | None = None
    error_message: str | None = None


class NotificationService:
    """
    Orchestrates notification sending with duplicate prevention.

    Features:
    - Alert condition evaluation
    - Duplicate prevention (checks last notified price)
    - Notification logging to database
    - Email delivery via Resend
    """

    # Cooldown period to prevent duplicate notifications (in hours)
    NOTIFICATION_COOLDOWN_HOURS = 24

    def __init__(
        self,
        session: AsyncSession,
        email_channel: EmailChannel | None = None,
        user_email: str | None = None,
    ) -> None:
        """
        Initialize the notification service.

        Args:
            session: Database session.
            email_channel: Email channel for sending. Defaults to new EmailChannel.
            user_email: User email address. Defaults to settings.user_email.
        """
        self._session = session
        self._email = email_channel or EmailChannel()
        self._user_email = user_email or settings.user_email

    async def evaluate_alert(
        self,
        alert: Alert,
        current_price: float,
        previous_price: float | None,
        in_stock: bool,
        was_in_stock: bool | None,
    ) -> AlertEvaluationResult:
        """
        Evaluate if an alert should trigger based on current conditions.

        Args:
            alert: The alert to evaluate.
            current_price: Current product price.
            previous_price: Previous tracked price.
            in_stock: Current stock status.
            was_in_stock: Previous stock status.

        Returns:
            AlertEvaluationResult indicating if alert should trigger.
        """
        if not alert.is_active:
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason="Alert is not active",
            )

        # Back in stock check
        if alert.alert_type == AlertType.BACK_IN_STOCK:
            if in_stock and was_in_stock is False:
                return AlertEvaluationResult(
                    triggered=True,
                    alert_type=alert.alert_type,
                    alert_id=alert.id,
                    reason="Product is back in stock",
                )
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason="Stock status unchanged or still out of stock",
            )

        # Price-based alerts require stock
        if not in_stock:
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason="Product is out of stock",
            )

        # Target price check
        if alert.alert_type == AlertType.TARGET_PRICE:
            target = alert.target_value
            if target and current_price <= target:
                return AlertEvaluationResult(
                    triggered=True,
                    alert_type=alert.alert_type,
                    alert_id=alert.id,
                    reason=f"Price ${current_price:.2f} is at or below target ${target:.2f}",
                )
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason=f"Price ${current_price:.2f} is above target ${target:.2f}" if target else "No target set",
            )

        # Percent drop check
        if alert.alert_type == AlertType.PERCENT_DROP:
            if previous_price and previous_price > 0:
                drop_percent = ((previous_price - current_price) / previous_price) * 100
                target_percent = alert.target_value or 0

                # Check minimum threshold
                price_diff = previous_price - current_price
                if price_diff < alert.min_change_threshold:
                    return AlertEvaluationResult(
                        triggered=False,
                        alert_type=alert.alert_type,
                        alert_id=alert.id,
                        reason=f"Price drop ${price_diff:.2f} below threshold ${alert.min_change_threshold:.2f}",
                    )

                if drop_percent >= target_percent:
                    return AlertEvaluationResult(
                        triggered=True,
                        alert_type=alert.alert_type,
                        alert_id=alert.id,
                        reason=f"Price dropped {drop_percent:.1f}% (target: {target_percent:.1f}%)",
                    )
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason="No price drop detected",
            )

        # Any change check
        if alert.alert_type == AlertType.ANY_CHANGE:
            if previous_price is not None and current_price != previous_price:
                price_diff = abs(current_price - previous_price)

                # Check minimum threshold
                if price_diff < alert.min_change_threshold:
                    return AlertEvaluationResult(
                        triggered=False,
                        alert_type=alert.alert_type,
                        alert_id=alert.id,
                        reason=f"Price change ${price_diff:.2f} below threshold ${alert.min_change_threshold:.2f}",
                    )

                return AlertEvaluationResult(
                    triggered=True,
                    alert_type=alert.alert_type,
                    alert_id=alert.id,
                    reason=f"Price changed from ${previous_price:.2f} to ${current_price:.2f}",
                )
            return AlertEvaluationResult(
                triggered=False,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                reason="No price change detected",
            )

        return AlertEvaluationResult(
            triggered=False,
            alert_type=alert.alert_type,
            alert_id=alert.id,
            reason="Unknown alert type",
        )

    async def check_duplicate(
        self,
        product_id: int,
        alert_id: int,
        current_price: float,
    ) -> bool:
        """
        Check if a notification was recently sent for this alert and price.

        Args:
            product_id: Product ID.
            alert_id: Alert ID.
            current_price: Current price to compare.

        Returns:
            True if this would be a duplicate, False if okay to send.
        """
        cutoff = datetime.utcnow() - timedelta(hours=self.NOTIFICATION_COOLDOWN_HOURS)

        query = (
            select(Notification)
            .where(
                Notification.product_id == product_id,
                Notification.alert_id == alert_id,
                Notification.status == NotificationStatus.SENT,
                Notification.created_at >= cutoff,
            )
            .order_by(Notification.created_at.desc())
            .limit(1)
        )

        result = await self._session.execute(query)
        last_notification = result.scalar_one_or_none()

        if not last_notification:
            return False

        # Check if the price in the last notification is the same
        payload = last_notification.payload or {}
        last_price = payload.get("current_price")

        if last_price is not None and abs(float(last_price) - current_price) < 0.01:
            logger.info(
                "Duplicate notification prevented",
                extra={
                    "product_id": product_id,
                    "alert_id": alert_id,
                    "price": current_price,
                },
            )
            return True

        return False

    async def send_price_alert(
        self,
        product: Product,
        alert: Alert,
        previous_price: float | None = None,
    ) -> NotificationResult:
        """
        Send a price alert notification.

        Args:
            product: The product.
            alert: The triggered alert.
            previous_price: Previous price (for drop calculations).

        Returns:
            NotificationResult with success status.
        """
        if not self._user_email:
            return NotificationResult(
                success=False,
                error_message="No user email configured",
            )

        # Check for duplicates
        if await self.check_duplicate(product.id, alert.id, product.current_price):
            return NotificationResult(
                success=False,
                error_message="Duplicate notification prevented",
            )

        # Get store name
        store = await self._session.get(Store, product.store_domain)
        store_name = store.name if store else product.store_domain

        # Render email
        alert_type_map = {
            AlertType.TARGET_PRICE: "target_reached",
            AlertType.PERCENT_DROP: "percent_drop",
            AlertType.ANY_CHANGE: "any_change",
        }

        rendered = render_price_alert(
            product_name=product.name,
            store_name=store_name,
            current_price=product.current_price,
            previous_price=previous_price,
            original_price=product.original_price,
            product_url=product.url,
            image_url=product.image_url,
            alert_type=alert_type_map.get(alert.alert_type, "price_drop"),
        )

        # Create notification record
        notification = Notification(
            alert_id=alert.id,
            product_id=product.id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
            payload={
                "product_name": product.name,
                "current_price": product.current_price,
                "previous_price": previous_price,
                "alert_type": alert.alert_type.value,
            },
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)

        # Send email
        try:
            result = await self._email.send(
                to=self._user_email,
                subject=rendered.subject,
                html_content=rendered.html,
                text_content=rendered.text,
                tags=[
                    {"name": "type", "value": "price_alert"},
                    {"name": "product_id", "value": str(product.id)},
                ],
            )

            if result.success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
                logger.info(f"Price alert sent for product {product.id}")
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = result.error_message

            await self._session.flush()

            return NotificationResult(
                success=result.success,
                notification_id=notification.id,
                error_message=result.error_message,
            )

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self._session.flush()

            return NotificationResult(
                success=False,
                notification_id=notification.id,
                error_message=str(e),
            )

    async def send_back_in_stock(
        self,
        product: Product,
        alert: Alert,
    ) -> NotificationResult:
        """
        Send a back in stock notification.

        Args:
            product: The product.
            alert: The triggered alert.

        Returns:
            NotificationResult with success status.
        """
        if not self._user_email:
            return NotificationResult(
                success=False,
                error_message="No user email configured",
            )

        # Get store name
        store = await self._session.get(Store, product.store_domain)
        store_name = store.name if store else product.store_domain

        # Render email
        rendered = render_back_in_stock(
            product_name=product.name,
            store_name=store_name,
            current_price=product.current_price or 0,
            product_url=product.url,
            image_url=product.image_url,
        )

        # Create notification record
        notification = Notification(
            alert_id=alert.id,
            product_id=product.id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
            payload={
                "product_name": product.name,
                "current_price": product.current_price,
                "alert_type": "back_in_stock",
            },
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)

        # Send email
        try:
            result = await self._email.send(
                to=self._user_email,
                subject=rendered.subject,
                html_content=rendered.html,
                text_content=rendered.text,
                tags=[
                    {"name": "type", "value": "back_in_stock"},
                    {"name": "product_id", "value": str(product.id)},
                ],
            )

            if result.success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
                logger.info(f"Back in stock alert sent for product {product.id}")
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = result.error_message

            await self._session.flush()

            return NotificationResult(
                success=result.success,
                notification_id=notification.id,
                error_message=result.error_message,
            )

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self._session.flush()

            return NotificationResult(
                success=False,
                notification_id=notification.id,
                error_message=str(e),
            )

    async def send_product_error(
        self,
        product: Product,
        error_type: str,
        error_message: str,
    ) -> NotificationResult:
        """
        Send a product error notification.

        Args:
            product: The product.
            error_type: Type of error.
            error_message: Error details.

        Returns:
            NotificationResult with success status.
        """
        if not self._user_email:
            return NotificationResult(
                success=False,
                error_message="No user email configured",
            )

        # Get store name
        store = await self._session.get(Store, product.store_domain)
        store_name = store.name if store else product.store_domain

        # Render email
        rendered = render_product_error(
            product_name=product.name,
            store_name=store_name,
            error_type=error_type,
            error_message=error_message,
            product_url=product.url,
        )

        # Create notification record
        notification = Notification(
            product_id=product.id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
            payload={
                "product_name": product.name,
                "error_type": error_type,
                "error_message": error_message,
            },
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)

        # Send email
        try:
            result = await self._email.send(
                to=self._user_email,
                subject=rendered.subject,
                html_content=rendered.html,
                text_content=rendered.text,
                tags=[
                    {"name": "type", "value": "product_error"},
                    {"name": "product_id", "value": str(product.id)},
                ],
            )

            if result.success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = result.error_message

            await self._session.flush()

            return NotificationResult(
                success=result.success,
                notification_id=notification.id,
                error_message=result.error_message,
            )

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self._session.flush()

            return NotificationResult(
                success=False,
                notification_id=notification.id,
                error_message=str(e),
            )

    async def send_store_flagged(
        self,
        store: Store,
        products_affected: int,
        failed_scrapes: int,
        failure_reason: str,
    ) -> NotificationResult:
        """
        Send a store health warning notification.

        Args:
            store: The flagged store.
            products_affected: Number of products affected.
            failed_scrapes: Number of failed scrapes.
            failure_reason: Reason for failures.

        Returns:
            NotificationResult with success status.
        """
        if not self._user_email:
            return NotificationResult(
                success=False,
                error_message="No user email configured",
            )

        # Render email
        rendered = render_store_flagged(
            store_name=store.name,
            store_domain=store.domain,
            success_rate=store.success_rate,
            products_affected=products_affected,
            failed_scrapes=failed_scrapes,
            failure_reason=failure_reason,
        )

        # Create notification record (no product/alert association)
        notification = Notification(
            product_id=0,  # No specific product
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
            payload={
                "store_domain": store.domain,
                "store_name": store.name,
                "success_rate": store.success_rate,
                "products_affected": products_affected,
            },
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)

        # Send email
        try:
            result = await self._email.send(
                to=self._user_email,
                subject=rendered.subject,
                html_content=rendered.html,
                text_content=rendered.text,
                tags=[
                    {"name": "type", "value": "store_flagged"},
                    {"name": "store", "value": store.domain},
                ],
            )

            if result.success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = result.error_message

            await self._session.flush()

            return NotificationResult(
                success=result.success,
                notification_id=notification.id,
                error_message=result.error_message,
            )

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self._session.flush()

            return NotificationResult(
                success=False,
                notification_id=notification.id,
                error_message=str(e),
            )

    async def process_price_change(
        self,
        product: Product,
        new_price: float,
        new_stock: bool,
        old_price: float | None = None,
        old_stock: bool | None = None,
    ) -> list[NotificationResult]:
        """
        Process a price change and send any triggered notifications.

        Args:
            product: The product.
            new_price: New price.
            new_stock: New stock status.
            old_price: Previous price.
            old_stock: Previous stock status.

        Returns:
            List of NotificationResults for each triggered alert.
        """
        results = []

        # Get active alerts for this product
        query = select(Alert).where(
            Alert.product_id == product.id,
            Alert.is_active.is_(True),
            Alert.deleted_at.is_(None),
        )
        alert_result = await self._session.execute(query)
        alerts = list(alert_result.scalars().all())

        for alert in alerts:
            evaluation = await self.evaluate_alert(
                alert=alert,
                current_price=new_price,
                previous_price=old_price,
                in_stock=new_stock,
                was_in_stock=old_stock,
            )

            if evaluation.triggered:
                logger.info(
                    f"Alert triggered: {evaluation.reason}",
                    extra={
                        "product_id": product.id,
                        "alert_id": alert.id,
                        "alert_type": alert.alert_type.value,
                    },
                )

                # Mark alert as triggered
                alert.is_triggered = True
                alert.triggered_at = datetime.utcnow()
                await self._session.flush()

                # Send appropriate notification
                if alert.alert_type == AlertType.BACK_IN_STOCK:
                    result = await self.send_back_in_stock(product, alert)
                else:
                    result = await self.send_price_alert(product, alert, old_price)

                results.append(result)

        return results
