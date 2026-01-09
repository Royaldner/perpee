"""
Tests for the Agent module (Phase 4).
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.agent.agent import (
    AgentResponse,
    ConversationMemory,
    load_system_prompt,
)
from src.agent.dependencies import AgentDependencies
from src.agent.guardrails import (
    DailyTokenTracker,
    InputValidator,
    LLMRateLimiter,
    TokenUsage,
    reset_guardrails,
    with_timeout,
)
from src.agent.tools import (
    AlertResult,
    CompareResult,
    PriceHistoryResult,
    ProductResult,
    ScheduleResult,
    SearchResult,
)
from src.core.exceptions import RateLimitError, TokenLimitError

# ===========================================
# Guardrails Tests
# ===========================================


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_token_usage_total(self):
        """Test total token calculation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total == 150

    def test_token_usage_empty(self):
        """Test empty token usage."""
        usage = TokenUsage()
        assert usage.total == 0


class TestDailyTokenTracker:
    """Tests for DailyTokenTracker."""

    def setup_method(self):
        """Reset guardrails before each test."""
        reset_guardrails()

    def test_tracker_initial_state(self):
        """Test initial state of token tracker."""
        tracker = DailyTokenTracker(daily_limit=1000)
        assert tracker.remaining == 1000
        assert tracker.usage_percent == 0.0

    def test_record_usage(self):
        """Test recording token usage."""
        tracker = DailyTokenTracker(daily_limit=1000)
        tracker.record_usage(100)
        assert tracker.remaining == 900
        assert tracker.usage_percent == 10.0

    def test_check_available(self):
        """Test checking token availability."""
        tracker = DailyTokenTracker(daily_limit=1000)
        assert tracker.check_available(500) is True
        assert tracker.check_available(1500) is False

    def test_enforce_limit_success(self):
        """Test enforce_limit when within budget."""
        tracker = DailyTokenTracker(daily_limit=1000)
        tracker.enforce_limit(500)  # Should not raise

    def test_enforce_limit_exceeded(self):
        """Test enforce_limit when over budget."""
        tracker = DailyTokenTracker(daily_limit=100)
        with pytest.raises(TokenLimitError):
            tracker.enforce_limit(500)

    def test_daily_reset(self):
        """Test that usage resets on new day."""
        tracker = DailyTokenTracker(daily_limit=1000)
        tracker.record_usage(500)

        # Simulate day change by adjusting reset timestamp
        tracker._reset_timestamp = (
            datetime.now(UTC) - timedelta(days=2)
        ).timestamp()

        assert tracker.remaining == 1000  # Should reset


class TestLLMRateLimiter:
    """Tests for LLMRateLimiter."""

    def setup_method(self):
        """Reset guardrails before each test."""
        reset_guardrails()

    def test_initial_state(self):
        """Test initial rate limiter state."""
        limiter = LLMRateLimiter(max_requests_per_minute=10)
        assert limiter.can_make_request is True
        assert limiter.requests_in_window == 0

    def test_record_request(self):
        """Test recording requests."""
        limiter = LLMRateLimiter(max_requests_per_minute=10)
        limiter.record_request()
        assert limiter.requests_in_window == 1

    def test_rate_limit_reached(self):
        """Test rate limit being reached."""
        limiter = LLMRateLimiter(max_requests_per_minute=3)

        for _ in range(3):
            limiter.record_request()

        assert limiter.can_make_request is False

    def test_enforce_limit_success(self):
        """Test enforce_limit when under limit."""
        limiter = LLMRateLimiter(max_requests_per_minute=10)
        limiter.enforce_limit()  # Should not raise

    def test_enforce_limit_exceeded(self):
        """Test enforce_limit when over limit."""
        limiter = LLMRateLimiter(max_requests_per_minute=1)
        limiter.record_request()

        with pytest.raises(RateLimitError):
            limiter.enforce_limit()

    @pytest.mark.asyncio
    async def test_acquire_waits(self):
        """Test that acquire waits when limit reached."""
        limiter = LLMRateLimiter(max_requests_per_minute=1)
        limiter.record_request()

        # Manually expire the timestamp
        limiter._timestamps[0] = limiter._timestamps[0] - 61

        # Should be able to acquire now
        await limiter.acquire()
        assert limiter.requests_in_window == 1  # Old one expired, new one added


class TestInputValidator:
    """Tests for InputValidator."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        validator = InputValidator()
        text = "Hello, world!"  # 13 chars
        assert validator.estimate_tokens(text) == 4  # 13 // 4 + 1

    def test_validate_input_short(self):
        """Test validation of short input."""
        validator = InputValidator(max_input_tokens=1000)
        text = "Short message"
        result = validator.validate_input(text)
        assert result == text

    def test_validate_input_truncate(self):
        """Test truncation of long input."""
        validator = InputValidator(max_input_tokens=10)  # Very low limit
        text = "A" * 1000  # 1000 chars = ~250 tokens
        result = validator.validate_input(text)
        assert len(result) <= 40  # 10 tokens * 4 chars

    def test_get_max_output_tokens(self):
        """Test getting max output tokens."""
        validator = InputValidator(max_output_tokens=500)
        assert validator.get_max_output_tokens() == 500


class TestWithTimeout:
    """Tests for with_timeout decorator."""

    @pytest.mark.asyncio
    async def test_timeout_success(self):
        """Test successful execution within timeout."""

        @with_timeout(5)
        async def quick_operation():
            return "done"

        result = await quick_operation()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test timeout being exceeded."""

        @with_timeout(1)
        async def slow_operation():
            await asyncio.sleep(5)
            return "done"

        with pytest.raises(TimeoutError):
            await slow_operation()


# ===========================================
# Conversation Memory Tests
# ===========================================


class TestConversationMemory:
    """Tests for ConversationMemory."""

    def test_initial_state(self):
        """Test initial memory state."""
        memory = ConversationMemory(max_messages=10)
        assert len(memory.messages) == 0
        assert memory.get_history() == []

    def test_add_and_retrieve(self):
        """Test adding and retrieving messages."""
        memory = ConversationMemory(max_messages=10)

        # Add mock messages
        mock_request = MagicMock()
        mock_response = MagicMock()

        memory.add_request(mock_request)
        memory.add_response(mock_response)

        history = memory.get_history()
        assert len(history) == 2
        assert history[0] == mock_request
        assert history[1] == mock_response

    def test_trim_to_max(self):
        """Test that memory is trimmed to max size."""
        memory = ConversationMemory(max_messages=3)

        # Add 5 messages
        for i in range(5):
            mock_msg = MagicMock()
            mock_msg.index = i
            memory.add_request(mock_msg)

        # Should only have last 3
        assert len(memory.messages) == 3
        assert memory.messages[0].index == 2
        assert memory.messages[2].index == 4

    def test_clear(self):
        """Test clearing memory."""
        memory = ConversationMemory(max_messages=10)
        memory.add_request(MagicMock())
        memory.add_request(MagicMock())

        memory.clear()
        assert len(memory.messages) == 0


# ===========================================
# Tool Result Types Tests
# ===========================================


class TestToolResultTypes:
    """Tests for tool result dataclasses."""

    def test_product_result(self):
        """Test ProductResult."""
        result = ProductResult(
            success=True,
            product_id=1,
            name="Test Product",
            price=29.99,
            store="amazon.ca",
            message="Added",
            url="https://amazon.ca/product/1",
        )
        assert result.success is True
        assert result.product_id == 1
        assert result.price == 29.99

    def test_search_result(self):
        """Test SearchResult."""
        result = SearchResult(
            products=[{"id": 1, "name": "Test"}],
            total=1,
            query="test query",
        )
        assert result.total == 1
        assert len(result.products) == 1

    def test_price_history_result(self):
        """Test PriceHistoryResult."""
        result = PriceHistoryResult(
            product_id=1,
            product_name="Test",
            history=[{"price": 29.99, "date": "2024-01-01"}],
            min_price=25.99,
            max_price=35.99,
            current_price=29.99,
        )
        assert result.min_price == 25.99
        assert result.max_price == 35.99

    def test_alert_result(self):
        """Test AlertResult."""
        result = AlertResult(
            success=True,
            alert_id=1,
            message="Alert created",
        )
        assert result.success is True
        assert result.alert_id == 1

    def test_schedule_result(self):
        """Test ScheduleResult."""
        result = ScheduleResult(
            success=True,
            schedule_id=1,
            message="Schedule created",
        )
        assert result.success is True
        assert result.schedule_id == 1

    def test_compare_result(self):
        """Test CompareResult."""
        result = CompareResult(
            product_name="Test Product",
            prices=[
                {"store": "amazon.ca", "price": 29.99},
                {"store": "bestbuy.ca", "price": 34.99},
            ],
            lowest_price=29.99,
            lowest_store="amazon.ca",
        )
        assert result.lowest_price == 29.99
        assert result.lowest_store == "amazon.ca"


# ===========================================
# Agent Dependencies Tests
# ===========================================


class TestAgentDependencies:
    """Tests for AgentDependencies."""

    def test_create_with_all_deps(self):
        """Test creating dependencies with all services."""
        session = MagicMock()
        scraper = MagicMock()
        search = MagicMock()
        sync = MagicMock()

        deps = AgentDependencies(
            session=session,
            scraper=scraper,
            search_service=search,
            sync_service=sync,
        )

        assert deps.session == session
        assert deps.scraper == scraper
        assert deps.search_service == search
        assert deps.sync_service == sync

    def test_create_with_defaults(self):
        """Test creating dependencies with default services."""
        session = MagicMock()

        # Mock the global service getters at their source modules
        with patch("src.scraper.engine.get_scraper_engine") as mock_scraper, \
             patch("src.rag.search.get_search_service") as mock_search, \
             patch("src.rag.sync.get_sync_service") as mock_sync:

            mock_scraper.return_value = MagicMock()
            mock_search.return_value = MagicMock()
            mock_sync.return_value = MagicMock()

            deps = AgentDependencies.create(session)

            assert deps.session == session
            mock_scraper.assert_called_once()
            mock_search.assert_called_once()
            mock_sync.assert_called_once()


# ===========================================
# Agent Response Tests
# ===========================================


class TestAgentResponse:
    """Tests for AgentResponse."""

    def test_success_response(self):
        """Test successful response."""
        response = AgentResponse(
            text="Hello!",
            success=True,
            tokens_used=50,
        )
        assert response.success is True
        assert response.text == "Hello!"
        assert response.tokens_used == 50
        assert response.error is None

    def test_error_response(self):
        """Test error response."""
        response = AgentResponse(
            text="",
            success=False,
            error="Something went wrong",
        )
        assert response.success is False
        assert response.error == "Something went wrong"


# ===========================================
# System Prompt Tests
# ===========================================


class TestSystemPrompt:
    """Tests for system prompt loading."""

    def test_load_system_prompt_from_file(self):
        """Test loading system prompt from file."""
        prompt = load_system_prompt()
        assert "Perpee" in prompt
        assert "price" in prompt.lower()

    def test_prompt_contains_tools(self):
        """Test that prompt mentions available tools."""
        prompt = load_system_prompt()
        assert "scrape_product" in prompt
        assert "search_products" in prompt
        assert "set_alert" in prompt


# ===========================================
# Integration Tests (Mocked)
# ===========================================


class TestAgentIntegration:
    """Integration tests with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_product_result_formatting(self):
        """Test that ProductResult formats correctly."""
        result = ProductResult(
            success=True,
            product_id=123,
            name="Sony WH-1000XM4",
            price=299.99,
            store="bestbuy.ca",
            message="Product is now being tracked!",
            url="https://bestbuy.ca/product/123",
        )

        assert "Sony WH-1000XM4" in result.name
        assert result.price == 299.99
        assert result.store == "bestbuy.ca"

    @pytest.mark.asyncio
    async def test_guardrails_integration(self):
        """Test guardrails work together."""
        reset_guardrails()

        tracker = DailyTokenTracker(daily_limit=1000)
        limiter = LLMRateLimiter(max_requests_per_minute=10)
        validator = InputValidator(max_input_tokens=500)

        # Validate input
        message = "Track this product for me please"
        validated = validator.validate_input(message)

        # Check rate limit
        assert limiter.can_make_request is True

        # Estimate and check tokens
        estimated = validator.estimate_tokens(validated)
        assert tracker.check_available(estimated) is True

        # Record usage
        limiter.record_request()
        tracker.record_usage(estimated + 100)  # Include response estimate

        assert limiter.requests_in_window == 1
        assert tracker.remaining < 1000


# ===========================================
# Edge Cases
# ===========================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_input(self):
        """Test handling empty input."""
        validator = InputValidator()
        result = validator.validate_input("")
        assert result == ""

    def test_very_long_input(self):
        """Test handling very long input."""
        validator = InputValidator(max_input_tokens=100)
        long_text = "A" * 10000
        result = validator.validate_input(long_text)
        assert len(result) <= 400  # 100 tokens * 4 chars

    def test_memory_with_single_message(self):
        """Test memory with just one message."""
        memory = ConversationMemory(max_messages=15)
        memory.add_request(MagicMock())
        assert len(memory.messages) == 1

    def test_rate_limiter_exact_limit(self):
        """Test rate limiter at exact limit."""
        limiter = LLMRateLimiter(max_requests_per_minute=5)

        for _ in range(5):
            assert limiter.can_make_request is True
            limiter.record_request()

        assert limiter.can_make_request is False
