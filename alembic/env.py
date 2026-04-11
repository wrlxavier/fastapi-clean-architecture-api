"""Alembic environment for SQLAlchemy metadata-driven migrations."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool
from sqlalchemy.engine import Connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "app" / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_database_settings():
    """Load database settings after the source directory is on sys.path."""
    from infrastructure.config.settings import DatabaseSettings

    return DatabaseSettings()


def load_target_metadata() -> MetaData:
    """Load the SQLAlchemy metadata tracked by Alembic."""
    from infrastructure.database import Base

    return Base.metadata


target_metadata = load_target_metadata()


def get_database_url() -> str:
    """Resolve the target database URL for Alembic commands."""
    configured_url = config.attributes.get("database_url")
    if configured_url is not None:
        return str(configured_url)
    return load_database_settings().sqlalchemy_database_url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live SQLAlchemy engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        run_migrations_with_connection(connection)


def run_migrations_with_connection(connection: Connection) -> None:
    """Run migrations within an existing SQLAlchemy connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
