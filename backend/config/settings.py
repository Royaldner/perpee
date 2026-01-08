"""
Application settings using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # LLM Configuration
    # ===========================================
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    primary_model: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="Primary LLM model",
    )
    fallback_model_1: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        description="First fallback model",
    )
    fallback_model_2: str = Field(
        default="anthropic/claude-3.5-haiku",
        description="Second fallback model (paid)",
    )

    # ===========================================
    # OpenAI (Embeddings)
    # ===========================================
    openai_api_key: str = Field(default="", description="OpenAI API key for embeddings")

    # ===========================================
    # Email Configuration
    # ===========================================
    resend_api_key: str = Field(default="", description="Resend API key")
    user_email: str = Field(default="", description="User email for notifications")
    from_email: str = Field(default="alerts@perpee.app", description="From email address")

    # ===========================================
    # Rate Limits & Guardrails
    # ===========================================
    daily_token_limit: int = Field(default=100_000, description="Daily token budget")
    max_scrapes_per_minute: int = Field(default=10, description="Max scrapes per minute")
    max_llm_requests_per_minute: int = Field(default=30, description="Max LLM requests per minute")
    request_timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    operation_timeout_seconds: int = Field(default=120, description="Operation timeout in seconds")

    # Agent limits
    input_token_limit: int = Field(default=4000, description="Max input tokens")
    output_token_limit: int = Field(default=1000, description="Max output tokens")
    conversation_window_size: int = Field(default=15, description="Messages to keep in memory")

    # ===========================================
    # Database
    # ===========================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/perpee.db",
        description="Database connection URL",
    )
    chromadb_path: str = Field(
        default="./data/chromadb",
        description="ChromaDB storage path",
    )

    # ===========================================
    # Application
    # ===========================================
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment name",
    )

    # ===========================================
    # Scheduler
    # ===========================================
    default_check_hour: int = Field(default=6, ge=0, le=23, description="Default check hour (24h)")
    scheduler_timezone: str = Field(default="UTC", description="Scheduler timezone")

    # ===========================================
    # Scraper
    # ===========================================
    max_concurrent_browsers: int = Field(default=3, description="Max concurrent browsers")
    memory_threshold_percent: float = Field(default=0.7, description="Memory threshold for dispatcher")
    page_load_delay_seconds: float = Field(default=1.0, description="Delay before extracting HTML")

    # ===========================================
    # Self-Healing
    # ===========================================
    max_consecutive_failures: int = Field(default=3, description="Failures before pause")
    max_healing_attempts: int = Field(default=3, description="Max selector regeneration attempts")
    store_failure_threshold: float = Field(default=0.5, description="Store flagging threshold")

    # ===========================================
    # Data Retention
    # ===========================================
    scrape_log_retention_days: int = Field(default=30, description="Days to keep scrape logs")
    notification_retention_days: int = Field(default=90, description="Days to keep notifications")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is valid."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path("./data")

    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        return self.data_dir / "logs"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid re-reading env vars on every call.
    """
    return Settings()


# Convenience alias
settings = get_settings()
