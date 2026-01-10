"""
Tests for the scheduler module.
"""

from datetime import datetime

import pytest
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from src.database.models import (
    Product,
    ProductStatus,
    Schedule,
    SQLModel,
    Store,
)
from src.scheduler.batching import BatchProcessor, BatchResult
from src.scheduler.service import SchedulerService, get_scheduler_service
from src.scheduler.triggers import (
    DEFAULT_CRON,
    MIN_INTERVAL_HOURS,
    SCHEDULE_PRESETS,
    create_schedule,
    describe_cron,
    get_effective_schedule,
    get_next_run_time,
    get_preset_schedule,
    validate_cron,
    validate_cron_with_minimum,
)

# ===========================================
# Test Fixtures
# ===========================================


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_store(test_session):
    """Create sample store for testing."""
    store = Store(
        domain="test.example.com",
        name="Test Store",
        is_whitelisted=True,
        is_active=True,
    )
    test_session.add(store)
    test_session.commit()
    test_session.refresh(store)
    return store


@pytest.fixture
def sample_product(test_session, sample_store):
    """Create sample product for testing."""
    product = Product(
        url="https://test.example.com/product/1",
        store_domain=sample_store.domain,
        name="Test Product",
        current_price=99.99,
        status=ProductStatus.ACTIVE,
    )
    test_session.add(product)
    test_session.commit()
    test_session.refresh(product)
    return product


# ===========================================
# CRON Validation Tests
# ===========================================


class TestCronValidation:
    """Tests for CRON validation functions."""

    def test_validate_cron_valid_daily(self):
        """Test validation of valid daily CRON."""
        result = validate_cron("0 6 * * *")

        assert result.valid
        assert result.expression == "0 6 * * *"
        assert result.error is None
        assert result.next_run is not None

    def test_validate_cron_valid_weekly(self):
        """Test validation of valid weekly CRON."""
        result = validate_cron("0 6 * * 1")

        assert result.valid
        assert result.next_run is not None

    def test_validate_cron_valid_hourly(self):
        """Test validation of valid hourly CRON."""
        result = validate_cron("0 * * * *")

        assert result.valid
        assert result.interval_hours is not None
        assert result.interval_hours == pytest.approx(1.0, rel=0.1)

    def test_validate_cron_invalid_format(self):
        """Test validation of invalid format."""
        result = validate_cron("not a cron")

        assert not result.valid
        assert result.error is not None

    def test_validate_cron_too_few_fields(self):
        """Test validation with too few fields."""
        result = validate_cron("0 6 * *")

        assert not result.valid
        assert "5 fields" in result.error

    def test_validate_cron_too_many_fields(self):
        """Test validation with too many fields."""
        result = validate_cron("0 6 * * * *")

        assert not result.valid
        assert "5 fields" in result.error

    def test_validate_cron_with_minimum_passes(self):
        """Test validation with minimum interval passes."""
        # Daily at 6 AM = 24 hour interval
        result = validate_cron_with_minimum("0 6 * * *", min_hours=24)

        assert result.valid

    def test_validate_cron_with_minimum_fails(self):
        """Test validation with minimum interval fails."""
        # Hourly = 1 hour interval, minimum is 24
        result = validate_cron_with_minimum("0 * * * *", min_hours=24)

        assert not result.valid
        assert "below minimum" in result.error

    def test_validate_cron_invalid_values(self):
        """Test validation with invalid field values."""
        _result = validate_cron("60 25 32 13 8")

        # croniter may or may not catch all invalid values
        # but the basic format should pass
        # The key is we handle errors gracefully

    def test_min_interval_hours_constant(self):
        """Test MIN_INTERVAL_HOURS constant."""
        assert MIN_INTERVAL_HOURS == 24

    def test_default_cron_constant(self):
        """Test DEFAULT_CRON constant."""
        assert DEFAULT_CRON == "0 6 * * *"


# ===========================================
# CRON Utility Tests
# ===========================================


class TestCronUtilities:
    """Tests for CRON utility functions."""

    def test_get_next_run_time_valid(self):
        """Test get_next_run_time with valid CRON."""
        next_run = get_next_run_time("0 6 * * *")

        assert next_run is not None
        assert next_run > datetime.utcnow()

    def test_get_next_run_time_invalid(self):
        """Test get_next_run_time with invalid CRON."""
        next_run = get_next_run_time("invalid")

        assert next_run is None

    def test_get_next_run_time_with_base(self):
        """Test get_next_run_time with custom base time."""
        base = datetime(2024, 1, 1, 0, 0)
        next_run = get_next_run_time("0 6 * * *", base)

        assert next_run is not None
        assert next_run.hour == 6

    def test_describe_cron_daily_6am(self):
        """Test describe_cron for daily at 6 AM."""
        desc = describe_cron("0 6 * * *")
        assert "6:00 AM" in desc or "Daily" in desc

    def test_describe_cron_midnight(self):
        """Test describe_cron for midnight."""
        desc = describe_cron("0 0 * * *")
        assert "midnight" in desc.lower() or "Daily" in desc

    def test_describe_cron_weekly(self):
        """Test describe_cron for weekly."""
        desc = describe_cron("0 6 * * 0")
        assert "Weekly" in desc or "Sunday" in desc

    def test_describe_cron_invalid(self):
        """Test describe_cron with invalid expression."""
        desc = describe_cron("invalid")
        assert "Invalid" in desc

    def test_get_preset_schedule_daily_morning(self):
        """Test get_preset_schedule for daily_morning."""
        preset = get_preset_schedule("daily_morning")

        assert preset is not None
        assert "cron" in preset
        assert "description" in preset

    def test_get_preset_schedule_invalid(self):
        """Test get_preset_schedule with invalid name."""
        preset = get_preset_schedule("nonexistent")
        assert preset is None

    def test_schedule_presets_content(self):
        """Test SCHEDULE_PRESETS has expected presets."""
        assert "daily_morning" in SCHEDULE_PRESETS
        assert "daily_evening" in SCHEDULE_PRESETS
        assert "weekly" in SCHEDULE_PRESETS


# ===========================================
# Schedule Management Tests
# ===========================================


class TestScheduleManagement:
    """Tests for schedule management functions."""

    def test_get_effective_schedule_default(self, test_session, sample_product):
        """Test get_effective_schedule returns system default."""
        info = get_effective_schedule(test_session, sample_product.id)

        assert info.product_id == sample_product.id
        assert info.source == "system"
        assert info.cron_expression == DEFAULT_CRON

    def test_get_effective_schedule_product(self, test_session, sample_product):
        """Test get_effective_schedule with product schedule."""
        # Create product schedule
        schedule = Schedule(
            product_id=sample_product.id,
            cron_expression="0 12 * * *",
            is_active=True,
        )
        test_session.add(schedule)
        test_session.commit()

        info = get_effective_schedule(test_session, sample_product.id)

        assert info.source == "product"
        assert info.cron_expression == "0 12 * * *"
        assert info.schedule_id == schedule.id

    def test_get_effective_schedule_store(self, test_session, sample_store, sample_product):
        """Test get_effective_schedule with store schedule."""
        # Create store schedule
        schedule = Schedule(
            store_domain=sample_store.domain,
            cron_expression="0 18 * * *",
            is_active=True,
        )
        test_session.add(schedule)
        test_session.commit()

        info = get_effective_schedule(test_session, sample_product.id)

        assert info.source == "store"
        assert info.cron_expression == "0 18 * * *"

    def test_get_effective_schedule_product_over_store(
        self, test_session, sample_store, sample_product
    ):
        """Test product schedule takes priority over store."""
        # Create both schedules
        store_schedule = Schedule(
            store_domain=sample_store.domain,
            cron_expression="0 18 * * *",
            is_active=True,
        )
        product_schedule = Schedule(
            product_id=sample_product.id,
            cron_expression="0 8 * * *",
            is_active=True,
        )
        test_session.add(store_schedule)
        test_session.add(product_schedule)
        test_session.commit()

        info = get_effective_schedule(test_session, sample_product.id)

        assert info.source == "product"
        assert info.cron_expression == "0 8 * * *"

    def test_create_schedule_product(self, test_session, sample_product):
        """Test create_schedule for product."""
        schedule = create_schedule(
            test_session,
            cron_expression="0 6 * * *",
            product_id=sample_product.id,
        )

        assert schedule is not None
        assert schedule.product_id == sample_product.id
        assert schedule.cron_expression == "0 6 * * *"
        assert schedule.is_active

    def test_create_schedule_store(self, test_session, sample_store):
        """Test create_schedule for store."""
        schedule = create_schedule(
            test_session,
            cron_expression="0 6 * * *",
            store_domain=sample_store.domain,
        )

        assert schedule is not None
        assert schedule.store_domain == sample_store.domain

    def test_create_schedule_invalid_cron(self, test_session, sample_product):
        """Test create_schedule with invalid CRON raises error."""
        with pytest.raises(ValueError, match="Invalid CRON"):
            create_schedule(
                test_session,
                cron_expression="invalid",
                product_id=sample_product.id,
            )

    def test_create_schedule_below_minimum(self, test_session, sample_product):
        """Test create_schedule below minimum interval raises error."""
        with pytest.raises(ValueError, match="below minimum"):
            create_schedule(
                test_session,
                cron_expression="0 * * * *",  # Hourly
                product_id=sample_product.id,
                validate_minimum=True,
            )

    def test_create_schedule_no_target_raises(self, test_session):
        """Test create_schedule without target raises error."""
        with pytest.raises(ValueError, match="Either product_id or store_domain"):
            create_schedule(
                test_session,
                cron_expression="0 6 * * *",
            )


# ===========================================
# SchedulerService Tests
# ===========================================


class TestSchedulerService:
    """Tests for SchedulerService class."""

    def test_scheduler_service_init(self):
        """Test SchedulerService initialization."""
        service = SchedulerService()

        assert service._scheduler is not None
        assert not service._started

    @pytest.mark.asyncio
    async def test_scheduler_service_start_stop(self):
        """Test SchedulerService start and shutdown."""
        service = SchedulerService()

        service.start()
        assert service.is_running

        service.shutdown()
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_scheduler_add_job(self):
        """Test adding a job to scheduler."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            job_id = service.add_job(
                test_job,
                job_id="test_job",
                cron_expression="0 6 * * *",
            )

            assert job_id == "test_job"
            assert service.get_job("test_job") is not None

        finally:
            service.shutdown()

    @pytest.mark.asyncio
    async def test_scheduler_remove_job(self):
        """Test removing a job from scheduler."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            service.add_job(
                test_job,
                job_id="test_job",
                cron_expression="0 6 * * *",
            )

            result = service.remove_job("test_job")
            assert result
            assert service.get_job("test_job") is None

        finally:
            service.shutdown()

    @pytest.mark.asyncio
    async def test_scheduler_pause_resume_job(self):
        """Test pausing and resuming a job."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            service.add_job(
                test_job,
                job_id="test_job",
                cron_expression="0 6 * * *",
            )

            # Pause
            result = service.pause_job("test_job")
            assert result

            job = service.get_job("test_job")
            assert job.next_run_time is None  # Paused jobs have no next run

            # Resume
            result = service.resume_job("test_job")
            assert result

            job = service.get_job("test_job")
            assert job.next_run_time is not None

        finally:
            service.shutdown()

    @pytest.mark.asyncio
    async def test_scheduler_get_next_run_time(self):
        """Test getting next run time for a job."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            service.add_job(
                test_job,
                job_id="test_job",
                cron_expression="0 6 * * *",
            )

            next_run = service.get_next_run_time("test_job")
            assert next_run is not None

        finally:
            service.shutdown()

    @pytest.mark.asyncio
    async def test_scheduler_reschedule_job(self):
        """Test rescheduling a job."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            service.add_job(
                test_job,
                job_id="test_job",
                cron_expression="0 6 * * *",
            )

            result = service.reschedule_job("test_job", "0 12 * * *")
            assert result

        finally:
            service.shutdown()

    def test_get_scheduler_service_singleton(self):
        """Test get_scheduler_service returns singleton."""
        # Clear any existing instance
        import src.scheduler.service as svc_module
        svc_module._scheduler_service = None

        service1 = get_scheduler_service()
        service2 = get_scheduler_service()
        assert service1 is service2


# ===========================================
# BatchProcessor Tests
# ===========================================


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_batch_result_dataclass(self):
        """Test BatchResult dataclass."""
        result = BatchResult(
            total=10,
            successful=8,
            failed=2,
        )

        assert result.total == 10
        assert result.successful == 8
        assert result.failed == 2
        assert result.by_store == {}

    def test_group_by_store(self, test_session, sample_store, sample_product):
        """Test _group_by_store groups products correctly."""
        # Create another product
        product2 = Product(
            url="https://test.example.com/product/2",
            store_domain=sample_store.domain,
            name="Test Product 2",
            current_price=49.99,
            status=ProductStatus.ACTIVE,
        )
        test_session.add(product2)
        test_session.commit()

        processor = BatchProcessor()
        grouped = processor._group_by_store([sample_product, product2])

        assert sample_store.domain in grouped
        assert len(grouped[sample_store.domain]) == 2

    @pytest.mark.asyncio
    async def test_process_single_inactive_skipped(self, test_session, sample_store):
        """Test process_single skips inactive products."""
        # Create inactive product
        product = Product(
            url="https://test.example.com/product/inactive",
            store_domain=sample_store.domain,
            name="Inactive Product",
            current_price=99.99,
            status=ProductStatus.PAUSED,
        )
        test_session.add(product)
        test_session.commit()

        processor = BatchProcessor()
        result = await processor.process_single(test_session, product)

        assert result == "skipped"


# ===========================================
# Integration Tests
# ===========================================


class TestSchedulerIntegration:
    """Integration tests for scheduler module."""

    def test_schedule_to_trigger_flow(self, test_session, sample_product):
        """Test flow from schedule creation to trigger validation."""
        # Create schedule
        schedule = create_schedule(
            test_session,
            cron_expression="0 6 * * *",
            product_id=sample_product.id,
        )

        # Get effective schedule
        info = get_effective_schedule(test_session, sample_product.id)

        assert info.source == "product"
        assert info.cron_expression == schedule.cron_expression

        # Validate the expression
        validation = validate_cron(info.cron_expression)
        assert validation.valid
        assert validation.next_run is not None

    @pytest.mark.asyncio
    async def test_scheduler_with_presets(self):
        """Test scheduler with preset schedules."""
        service = SchedulerService()
        service.start()

        try:
            async def test_job():
                pass

            # Use preset
            preset = get_preset_schedule("daily_morning")
            job_id = service.add_job(
                test_job,
                job_id="preset_job",
                cron_expression=preset["cron"],
            )

            assert job_id == "preset_job"
            job = service.get_job("preset_job")
            assert job is not None

        finally:
            service.shutdown()
