"""Alembic environment configuration for LabPulse.

Uses the application's own settings (``LABPULSE_DATABASE`` env var) as the
source of truth for the database URL, and SQLModel metadata for autogenerate
support.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Import models so they are registered on SQLModel.metadata.
import app.models  # noqa: F401
from app.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# app/core/database.py passes an explicit URL via this attribute when running
# migrations programmatically against a not-yet-persisted setup-wizard choice;
# plain `alembic upgrade head` from the CLI falls back to the settings-derived URL.
url = config.attributes.get("sqlalchemy_url") or settings.database_url
config.set_main_option("sqlalchemy.url", url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
