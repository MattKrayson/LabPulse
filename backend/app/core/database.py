"""Database engine and session management.

The database connection is configured dynamically rather than fixed at
import time: on startup, LabPulse tries to auto-configure from either an
explicit ``LABPULSE_DATABASE_URL`` env var or a previously saved setup-wizard
choice (see app/core/db_config_store.py). If neither is present, no engine
exists yet and API routes that need one return 503 until the admin completes
the first-run setup wizard (``/api/setup/*``), which tests the chosen
connection, runs migrations against it, and only then makes the engine
available - so nothing is collected/stored before a working database has
been confirmed.
"""
from collections.abc import Generator
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core import db_config_store
from app.core.config import get_settings

_engine: Engine | None = None
_current_url: str | None = None


def _make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    if database_url.startswith("sqlite"):
        db_path = database_url.removeprefix("sqlite:///")
        parent = Path(db_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, echo=False, connect_args=connect_args)


def is_configured() -> bool:
    return _engine is not None


def get_current_url_masked() -> str | None:
    """Return the active database URL with any password redacted, for display only."""
    if _current_url is None:
        return None
    if "://" not in _current_url:
        return _current_url
    scheme, rest = _current_url.split("://", 1)
    if "@" not in rest:
        return _current_url
    creds, host_part = rest.rsplit("@", 1)
    user = creds.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host_part}"


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database is not configured yet")
    return _engine


def test_connection(database_url: str) -> None:
    """Raise if a connection cannot be established. Does not persist anything."""
    engine = _make_engine(database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def _run_migrations(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config as AlembicConfig

    backend_dir = Path(__file__).resolve().parent.parent.parent
    alembic_cfg = AlembicConfig(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    # migrations/env.py prefers this attribute over the env-derived settings URL.
    alembic_cfg.attributes["sqlalchemy_url"] = database_url
    command.upgrade(alembic_cfg, "head")


def configure_database(database_url: str, persist: bool = True) -> None:
    """Test the connection, run migrations, and switch the app over to it."""
    global _engine, _current_url
    test_connection(database_url)
    _run_migrations(database_url)
    _engine = _make_engine(database_url)
    _current_url = database_url
    if persist:
        db_config_store.save_database_url(database_url)


def try_autoconfigure() -> bool:
    """Configure the DB at startup if a URL is already known, so existing
    deployments (LABPULSE_DATABASE_URL set, or a previously completed setup
    wizard) keep working without re-prompting. Returns True if configured."""
    settings = get_settings()
    database_url = settings.database_url_override or db_config_store.load_database_url()
    if not database_url:
        return False
    try:
        configure_database(database_url, persist=False)
        return True
    except Exception:  # noqa: BLE001 - fall back to setup wizard on any failure
        return False


def init_db() -> None:
    """Create database tables if they do not already exist.

    Real schema evolution is handled by Alembic migrations (see
    ``backend/migrations``). This call is a safety net for first-run and for
    environments where migrations have not been executed yet.
    """
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    if _engine is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    with Session(_engine) as session:
        yield session
