"""
Phase 6 tests - API and Notification verification.
Tests API endpoints, WebSocket chat, and notification service.
"""

import pytest
from httpx import AsyncClient

from src.api.schemas import (
    AlertCreate,
    ProductCreate,
    ScheduleCreate,
)
from src.database.models import (
    Alert,
    AlertType,
)
from src.notifications.channels.email import EmailChannel
from src.notifications.service import NotificationService
from src.notifications.templates import (
    render_back_in_stock,
    render_price_alert,
    render_product_error,
    render_store_flagged,
)

# ===========================================
# Email Template Tests
# ===========================================


class TestEmailTemplates:
    """Test email template rendering."""

    def test_render_price_alert(self):
        """Test price alert email rendering."""
        result = render_price_alert(
            product_name="Test Product",
            store_name="Amazon Canada",
            current_price=79.99,
            previous_price=99.99,
            original_price=129.99,
            product_url="https://amazon.ca/dp/B123",
            image_url="https://amazon.ca/image.jpg",
            alert_type="price_drop",
        )

        assert result.subject is not None
        assert "Test Product" in result.subject
        assert "79.99" in result.subject
        assert result.html is not None
        assert "Test Product" in result.html
        assert "Amazon Canada" in result.html
        assert result.text is not None

    def test_render_back_in_stock(self):
        """Test back in stock email rendering."""
        result = render_back_in_stock(
            product_name="Test Product",
            store_name="Best Buy",
            current_price=149.99,
            product_url="https://bestbuy.ca/item",
        )

        assert "Back in Stock" in result.subject
        assert "Test Product" in result.subject
        assert result.html is not None
        assert "In Stock" in result.html

    def test_render_product_error(self):
        """Test product error email rendering."""
        result = render_product_error(
            product_name="Test Product",
            store_name="Walmart",
            error_type="Product Not Found",
            error_message="The product page returned a 404 error.",
            product_url="https://walmart.ca/item",
        )

        assert "Tracking Issue" in result.subject
        assert result.html is not None
        assert "Product Not Found" in result.html

    def test_render_store_flagged(self):
        """Test store flagged email rendering."""
        result = render_store_flagged(
            store_name="Amazon Canada",
            store_domain="amazon.ca",
            success_rate=0.35,
            products_affected=12,
            failed_scrapes=8,
            failure_reason="Website structure may have changed.",
        )

        assert "Store Health Warning" in result.subject
        assert "35%" in result.subject
        assert result.html is not None
        assert "35%" in result.html


# ===========================================
# Email Channel Tests
# ===========================================


class TestEmailChannel:
    """Test email channel functionality."""

    def test_email_channel_not_configured(self):
        """Test email channel without API key."""
        channel = EmailChannel(api_key="", from_email="")
        assert channel.is_configured is False

    def test_email_channel_configured(self):
        """Test email channel with API key."""
        channel = EmailChannel(api_key="test_key", from_email="test@example.com")
        assert channel.is_configured is True


# ===========================================
# Notification Service Tests
# ===========================================


class TestNotificationService:
    """Test notification service functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_target_price_alert_triggered(self, async_session):
        """Test target price alert triggers when price meets target."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=100.0,
            min_change_threshold=1.0,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=95.0,
            previous_price=110.0,
            in_stock=True,
            was_in_stock=True,
        )

        assert result.triggered is True
        assert "at or below target" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_evaluate_target_price_alert_not_triggered(self, async_session):
        """Test target price alert doesn't trigger above target."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=100.0,
            min_change_threshold=1.0,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=120.0,
            previous_price=110.0,
            in_stock=True,
            was_in_stock=True,
        )

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_evaluate_percent_drop_triggered(self, async_session):
        """Test percent drop alert triggers on sufficient drop."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.PERCENT_DROP,
            target_value=10.0,  # 10% drop required
            min_change_threshold=1.0,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=85.0,  # 15% drop from 100
            previous_price=100.0,
            in_stock=True,
            was_in_stock=True,
        )

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_back_in_stock_triggered(self, async_session):
        """Test back in stock alert triggers correctly."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.BACK_IN_STOCK,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=99.0,
            previous_price=99.0,
            in_stock=True,
            was_in_stock=False,  # Was out of stock
        )

        assert result.triggered is True
        assert "back in stock" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_evaluate_any_change_triggered(self, async_session):
        """Test any change alert triggers on price change."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.ANY_CHANGE,
            min_change_threshold=1.0,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=95.0,
            previous_price=100.0,
            in_stock=True,
            was_in_stock=True,
        )

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_alert_inactive_not_triggered(self, async_session):
        """Test inactive alert doesn't trigger."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=100.0,
            is_active=False,  # Inactive
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=50.0,  # Well below target
            previous_price=100.0,
            in_stock=True,
            was_in_stock=True,
        )

        assert result.triggered is False
        assert "not active" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_price_alert_out_of_stock_not_triggered(self, async_session):
        """Test price alert doesn't trigger when out of stock."""
        service = NotificationService(async_session)

        alert = Alert(
            id=1,
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=100.0,
            is_active=True,
        )

        result = await service.evaluate_alert(
            alert=alert,
            current_price=50.0,
            previous_price=100.0,
            in_stock=False,  # Out of stock
            was_in_stock=True,
        )

        assert result.triggered is False
        assert "out of stock" in result.reason.lower()


# ===========================================
# API Schema Tests
# ===========================================


class TestAPISchemas:
    """Test API schema validation."""

    def test_product_create_valid(self):
        """Test valid product creation schema."""
        data = ProductCreate(url="https://amazon.ca/dp/B123456")
        assert str(data.url) == "https://amazon.ca/dp/B123456"

    def test_alert_create_target_price(self):
        """Test alert creation with target price."""
        data = AlertCreate(
            product_id=1,
            alert_type=AlertType.TARGET_PRICE,
            target_value=99.99,
        )
        assert data.alert_type == AlertType.TARGET_PRICE
        assert data.target_value == 99.99

    def test_alert_create_percent_drop(self):
        """Test alert creation with percent drop."""
        data = AlertCreate(
            product_id=1,
            alert_type=AlertType.PERCENT_DROP,
            target_value=10.0,
        )
        assert data.alert_type == AlertType.PERCENT_DROP
        assert data.target_value == 10.0

    def test_alert_create_back_in_stock(self):
        """Test alert creation for back in stock."""
        data = AlertCreate(
            product_id=1,
            alert_type=AlertType.BACK_IN_STOCK,
        )
        assert data.alert_type == AlertType.BACK_IN_STOCK

    def test_schedule_create_valid_cron(self):
        """Test schedule creation with valid CRON."""
        data = ScheduleCreate(
            product_id=1,
            cron_expression="0 6 * * *",
        )
        assert data.cron_expression == "0 6 * * *"

    def test_schedule_create_invalid_cron(self):
        """Test schedule creation with invalid CRON."""
        with pytest.raises(ValueError):
            ScheduleCreate(
                product_id=1,
                cron_expression="invalid cron",
            )


# ===========================================
# Health Endpoint Tests
# ===========================================


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client: AsyncClient):
        """Test health check endpoint."""
        response = await test_client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, test_client: AsyncClient):
        """Test root endpoint."""
        response = await test_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data or "message" in data


# ===========================================
# Product Endpoint Tests
# ===========================================


class TestProductEndpoints:
    """Test product CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_products_empty(self, test_client: AsyncClient):
        """Test listing products when empty."""
        response = await test_client.get("/api/products")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "meta" in data

    @pytest.mark.asyncio
    async def test_list_products_with_data(self, test_client: AsyncClient, sample_product):
        """Test listing products with data."""
        response = await test_client.get("/api/products")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_product(self, test_client: AsyncClient, sample_product):
        """Test getting a single product."""
        response = await test_client.get(f"/api/products/{sample_product.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_product.id
        assert data["name"] == sample_product.name

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, test_client: AsyncClient):
        """Test getting a non-existent product."""
        response = await test_client.get("/api/products/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_product(self, test_client: AsyncClient, sample_store):
        """Test creating a product."""
        response = await test_client.post(
            "/api/products",
            json={"url": "https://amazon.ca/dp/NEWPRODUCT123"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["url"] == "https://amazon.ca/dp/NEWPRODUCT123"
        assert data["store_domain"] == "amazon.ca"

    @pytest.mark.asyncio
    async def test_create_product_duplicate(self, test_client: AsyncClient, sample_product):
        """Test creating a duplicate product."""
        response = await test_client.post(
            "/api/products",
            json={"url": sample_product.url},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_product(self, test_client: AsyncClient, sample_product):
        """Test soft deleting a product."""
        response = await test_client.delete(f"/api/products/{sample_product.id}")
        assert response.status_code == 200

        # Verify it's no longer returned
        response = await test_client.get(f"/api/products/{sample_product.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_product_stats(self, test_client: AsyncClient, sample_product):
        """Test product statistics endpoint."""
        response = await test_client.get("/api/products/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "active" in data


# ===========================================
# Alert Endpoint Tests
# ===========================================


class TestAlertEndpoints:
    """Test alert CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_alerts(self, test_client: AsyncClient, sample_alert):
        """Test listing alerts."""
        response = await test_client.get("/api/alerts")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_alert(self, test_client: AsyncClient, sample_alert):
        """Test getting a single alert."""
        response = await test_client.get(f"/api/alerts/{sample_alert.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_alert.id
        assert data["alert_type"] == AlertType.TARGET_PRICE.value

    @pytest.mark.asyncio
    async def test_create_alert(self, test_client: AsyncClient, sample_product):
        """Test creating an alert."""
        response = await test_client.post(
            "/api/alerts",
            json={
                "product_id": sample_product.id,
                "alert_type": "percent_drop",
                "target_value": 15.0,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["product_id"] == sample_product.id
        assert data["alert_type"] == "percent_drop"

    @pytest.mark.asyncio
    async def test_update_alert(self, test_client: AsyncClient, sample_alert):
        """Test updating an alert."""
        response = await test_client.patch(
            f"/api/alerts/{sample_alert.id}",
            json={"target_value": 59.99},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["target_value"] == 59.99

    @pytest.mark.asyncio
    async def test_delete_alert(self, test_client: AsyncClient, sample_alert):
        """Test deleting an alert."""
        response = await test_client.delete(f"/api/alerts/{sample_alert.id}")
        assert response.status_code == 200


# ===========================================
# Store Endpoint Tests
# ===========================================


class TestStoreEndpoints:
    """Test store endpoints."""

    @pytest.mark.asyncio
    async def test_list_stores(self, test_client: AsyncClient, sample_store):
        """Test listing stores."""
        response = await test_client.get("/api/stores")
        assert response.status_code == 200

        data = response.json()
        assert "stores" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_store(self, test_client: AsyncClient, sample_store):
        """Test getting a single store."""
        response = await test_client.get(f"/api/stores/{sample_store.domain}")
        assert response.status_code == 200

        data = response.json()
        assert data["domain"] == sample_store.domain
        assert data["name"] == sample_store.name

    @pytest.mark.asyncio
    async def test_get_store_health(self, test_client: AsyncClient, sample_store):
        """Test getting store health."""
        response = await test_client.get(f"/api/stores/{sample_store.domain}/health")
        assert response.status_code == 200

        data = response.json()
        assert "success_rate" in data
        assert "is_healthy" in data

    @pytest.mark.asyncio
    async def test_get_store_stats(self, test_client: AsyncClient, sample_store):
        """Test store statistics endpoint."""
        response = await test_client.get("/api/stores/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "healthy" in data


# ===========================================
# Stats Endpoint Tests
# ===========================================


class TestStatsEndpoint:
    """Test statistics endpoint."""

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, test_client: AsyncClient, sample_product, sample_alert):
        """Test comprehensive stats endpoint."""
        response = await test_client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert "products" in data
        assert "alerts" in data
        assert "stores" in data


# ===========================================
# Chat Schema Tests
# ===========================================


class TestChatSchemas:
    """Test chat/WebSocket schemas."""

    def test_create_welcome_message(self):
        """Test welcome message creation."""
        from src.api.schemas import create_welcome_message

        msg = create_welcome_message("session-123")
        assert msg["type"] == "welcome"
        assert msg["data"]["session_id"] == "session-123"

    def test_create_response_message(self):
        """Test response message creation."""
        from src.api.schemas import create_response_message

        msg = create_response_message("Hello, world!")
        assert msg["type"] == "response"
        assert msg["data"]["content"] == "Hello, world!"

    def test_create_error_message(self):
        """Test error message creation."""
        from src.api.schemas import create_error_message

        msg = create_error_message("Something went wrong", "ERR001")
        assert msg["type"] == "error"
        assert msg["data"]["message"] == "Something went wrong"
        assert msg["data"]["code"] == "ERR001"

    def test_create_thinking_message(self):
        """Test thinking message creation."""
        from src.api.schemas import create_thinking_message

        msg = create_thinking_message()
        assert msg["type"] == "thinking"
