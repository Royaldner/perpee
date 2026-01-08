"""
Alembic environment configuration for SQLModel.
Uses synchronous migrations for SQLite compatibility.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

from alembic import context

# Load settings
from config.settings import settings

# Import all models to ensure they're registered with SQLModel.metadata
from src.database.models import (  # noqa: F401
    Alert,
    CanonicalProduct,
    Notification,
    PriceHistory,
    Product,
    Schedule,
    ScrapeLog,
    Store,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url from our settings
# Convert async URL to sync for Alembic
database_url = settings.database_url
if database_url.startswith("sqlite+aiosqlite"):
    sync_url = database_url.replace("sqlite+aiosqlite", "sqlite")
else:
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

config.set_main_option("sqlalchemy.url", sync_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata for autogenerate support
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
