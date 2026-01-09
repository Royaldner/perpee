"""
Pydantic AI agent for Perpee price monitoring.
Configures the agent with OpenRouter models and all tools.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
)
from pydantic_ai.models.openai import OpenAIModel

from config.settings import settings

from .dependencies import AgentDependencies
from .guardrails import (
    get_input_validator,
    get_rate_limiter,
    get_token_tracker,
)
from .tools import (
    compare_prices,
    create_schedule,
    get_price_history,
    list_products,
    remove_product,
    scan_website,
    scrape_product,
    search_products,
    set_alert,
    web_search,
)

logger = logging.getLogger(__name__)

# ===========================================
# System Prompt
# ===========================================

PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_file = PROMPTS_DIR / "system.txt"
    if prompt_file.exists():
        return prompt_file.read_text()

    # Fallback prompt if file not found
    return """You are Perpee, an AI-powered price monitoring assistant for Canadian online retailers.
Help users track product prices, set alerts, and find the best deals."""


# ===========================================
# Conversation Memory
# ===========================================


@dataclass
class ConversationMemory:
    """
    Window-based conversation memory.

    Keeps the last N messages for context.
    Session-only: not persisted to database.
    """

    max_messages: int = field(default_factory=lambda: settings.conversation_window_size)
    messages: list[ModelMessage] = field(default_factory=list)

    def add_request(self, request: ModelRequest) -> None:
        """Add a user request to memory."""
        self.messages.append(request)
        self._trim()

    def add_response(self, response: ModelResponse) -> None:
        """Add a model response to memory."""
        self.messages.append(response)
        self._trim()

    def _trim(self) -> None:
        """Trim messages to max size."""
        if len(self.messages) > self.max_messages:
            # Keep the most recent messages
            self.messages = self.messages[-self.max_messages :]

    def get_history(self) -> list[ModelMessage]:
        """Get conversation history for context."""
        return list(self.messages)

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []


# ===========================================
# Model Configuration
# ===========================================


def create_openrouter_model(model_name: str) -> OpenAIModel:
    """
    Create an OpenRouter-compatible model.

    OpenRouter uses OpenAI-compatible API.

    Args:
        model_name: OpenRouter model identifier

    Returns:
        OpenAIModel configured for OpenRouter
    """
    return OpenAIModel(
        model_name,
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def get_model_chain() -> list[OpenAIModel]:
    """
    Get the model fallback chain.

    Returns:
        List of models in priority order
    """
    models = []

    # Primary: Gemini 2.0 Flash (free)
    if settings.primary_model:
        models.append(create_openrouter_model(settings.primary_model))

    # Fallback 1: Llama 3.3 70B (free)
    if settings.fallback_model_1:
        models.append(create_openrouter_model(settings.fallback_model_1))

    # Fallback 2: Claude 3.5 Haiku (paid)
    if settings.fallback_model_2:
        models.append(create_openrouter_model(settings.fallback_model_2))

    if not models:
        raise ValueError("No models configured. Set OPENROUTER_API_KEY and model settings.")

    return models


# ===========================================
# Agent Setup
# ===========================================

# Create the agent with primary model
_agent: Agent[AgentDependencies, str] | None = None


def get_agent() -> Agent[AgentDependencies, str]:
    """
    Get the configured Pydantic AI agent.

    Returns:
        Configured agent instance
    """
    global _agent

    if _agent is not None:
        return _agent

    # Load system prompt
    system_prompt = load_system_prompt()

    # Get primary model
    models = get_model_chain()
    primary_model = models[0]

    # Create agent
    _agent = Agent(
        model=primary_model,
        system_prompt=system_prompt,
        deps_type=AgentDependencies,
        result_type=str,
    )

    # Register tools
    _register_tools(_agent)

    return _agent


def _register_tools(agent: Agent[AgentDependencies, str]) -> None:
    """Register all agent tools."""

    @agent.tool
    async def tool_scrape_product(
        ctx,
        url: str,
    ):
        """
        Add a product to track by URL.

        Args:
            url: The product page URL to scrape and track
        """
        return await scrape_product(ctx, url)

    @agent.tool
    async def tool_scan_website(
        ctx,
        url: str,
    ):
        """
        Analyze an unknown website to check if it can be tracked.

        Args:
            url: URL to analyze
        """
        return await scan_website(ctx, url)

    @agent.tool
    async def tool_search_products(
        ctx,
        query: str,
        store: str | None = None,
        limit: int = 10,
    ):
        """
        Search tracked products.

        Args:
            query: Search query (natural language)
            store: Optional store domain to filter by
            limit: Maximum number of results (default 10)
        """
        return await search_products(ctx, query, store, limit)

    @agent.tool
    async def tool_web_search(
        ctx,
        query: str,
    ):
        """
        Search the web for product URLs.

        Args:
            query: Product search query
        """
        return await web_search(ctx, query)

    @agent.tool
    async def tool_get_price_history(
        ctx,
        product_id: int,
        days: int = 30,
    ):
        """
        Get price history for a tracked product.

        Args:
            product_id: The product ID
            days: Number of days of history (default 30)
        """
        return await get_price_history(ctx, product_id, days)

    @agent.tool
    async def tool_create_schedule(
        ctx,
        product_id: int,
        cron_expression: str,
    ):
        """
        Create a custom monitoring schedule for a product.

        Args:
            product_id: The product ID
            cron_expression: Cron expression (e.g., "0 6 * * *" for 6 AM daily)
        """
        return await create_schedule(ctx, product_id, cron_expression)

    @agent.tool
    async def tool_set_alert(
        ctx,
        product_id: int,
        alert_type: str,
        target_value: float | None = None,
    ):
        """
        Create a price alert for a product.

        Args:
            product_id: The product ID
            alert_type: Type of alert (target_price, percent_drop, any_change, back_in_stock)
            target_value: Target value for target_price (price threshold) or percent_drop (percentage)
        """
        return await set_alert(ctx, product_id, alert_type, target_value)

    @agent.tool
    async def tool_compare_prices(
        ctx,
        canonical_id: int,
    ):
        """
        Compare prices across stores for the same product.

        Args:
            canonical_id: The canonical product ID (groups same products from different stores)
        """
        return await compare_prices(ctx, canonical_id)

    @agent.tool
    async def tool_list_products(
        ctx,
        store: str | None = None,
        limit: int = 20,
    ):
        """
        List all tracked products.

        Args:
            store: Optional store domain to filter by
            limit: Maximum number of results (default 20)
        """
        return await list_products(ctx, store, limit)

    @agent.tool
    async def tool_remove_product(
        ctx,
        product_id: int,
    ):
        """
        Stop tracking a product.

        Args:
            product_id: The product ID to remove
        """
        return await remove_product(ctx, product_id)


# ===========================================
# Agent Runner
# ===========================================


@dataclass
class AgentResponse:
    """Response from the agent."""

    text: str
    success: bool = True
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    error: str | None = None


class PerpeeAgent:
    """
    High-level agent interface with memory and guardrails.

    Usage:
        agent = PerpeeAgent()
        response = await agent.chat(deps, "Track this product: ...")
    """

    def __init__(self):
        self.agent = get_agent()
        self.memory = ConversationMemory()
        self.token_tracker = get_token_tracker()
        self.rate_limiter = get_rate_limiter()
        self.input_validator = get_input_validator()

    async def chat(
        self,
        deps: AgentDependencies,
        message: str,
        *,
        use_history: bool = True,
    ) -> AgentResponse:
        """
        Send a message to the agent and get a response.

        Args:
            deps: Agent dependencies
            message: User message
            use_history: Whether to include conversation history

        Returns:
            AgentResponse with the agent's reply
        """
        try:
            # Validate input
            message = self.input_validator.validate_input(message)

            # Check rate limit
            await self.rate_limiter.acquire()

            # Estimate tokens and check budget
            estimated_tokens = self.input_validator.estimate_tokens(message) + 500
            self.token_tracker.enforce_limit(estimated_tokens)

            # Get conversation history
            message_history = self.memory.get_history() if use_history else None

            # Run the agent
            result = await self.agent.run(
                message,
                deps=deps,
                message_history=message_history,
            )

            # Record token usage (estimate from response)
            response_tokens = self.input_validator.estimate_tokens(result.data)
            total_tokens = estimated_tokens + response_tokens
            self.token_tracker.record_usage(total_tokens)

            # Update memory
            if result.new_messages():
                for msg in result.new_messages():
                    if isinstance(msg, ModelRequest):
                        self.memory.add_request(msg)
                    elif isinstance(msg, ModelResponse):
                        self.memory.add_response(msg)

            return AgentResponse(
                text=result.data,
                success=True,
                tokens_used=total_tokens,
            )

        except Exception as e:
            logger.error(f"Agent error: {e}")
            return AgentResponse(
                text="",
                success=False,
                error=str(e),
            )

    def clear_memory(self) -> None:
        """Clear conversation history."""
        self.memory.clear()


# ===========================================
# Convenience Functions
# ===========================================

_perpee_agent: PerpeeAgent | None = None


def get_perpee_agent() -> PerpeeAgent:
    """Get the global PerpeeAgent instance."""
    global _perpee_agent
    if _perpee_agent is None:
        _perpee_agent = PerpeeAgent()
    return _perpee_agent


def reset_agent() -> None:
    """Reset the global agent instances (for testing)."""
    global _agent, _perpee_agent
    _agent = None
    _perpee_agent = None
