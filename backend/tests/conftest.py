"""
Pytest fixtures for Perpee tests.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from src.api.main import app
from src.database.models import Alert, AlertType, Product, ProductStatus, Store


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create a test async engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test async session."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for API testing."""
    from src.api.dependencies import get_db

    # Override the database dependency
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_store(async_session) -> Store:
    """Create a sample store for testing."""
    store = Store(
        domain="amazon.ca",
        name="Amazon Canada",
        is_whitelisted=True,
        is_active=True,
        rate_limit_rpm=10,
        success_rate=1.0,
    )
    async_session.add(store)
    await async_session.flush()
    return store


@pytest.fixture
async def sample_product(async_session, sample_store) -> Product:
    """Create a sample product for testing."""
    product = Product(
        url="https://amazon.ca/dp/B123456",
        store_domain=sample_store.domain,
        name="Test Product",
        brand="Test Brand",
        current_price=99.99,
        original_price=129.99,
        in_stock=True,
        status=ProductStatus.ACTIVE,
    )
    async_session.add(product)
    await async_session.flush()
    await async_session.refresh(product)
    return product


@pytest.fixture
async def sample_alert(async_session, sample_product) -> Alert:
    """Create a sample alert for testing."""
    alert = Alert(
        product_id=sample_product.id,
        alert_type=AlertType.TARGET_PRICE,
        target_value=79.99,
        min_change_threshold=1.0,
        is_active=True,
    )
    async_session.add(alert)
    await async_session.flush()
    await async_session.refresh(alert)
    return alert
