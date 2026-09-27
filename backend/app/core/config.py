"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LabPulse runtime settings.

    All settings can be overridden via environment variables, matching the
    ``LABPULSE_*`` naming convention used throughout the project.
    """

    model_config = SettingsConfigDict(env_prefix="LABPULSE_", env_file=".env", extra="ignore")

    app_name: str = "LabPulse"
    version: str = "0.2.1"

    # Database
    database: str = "./data/labpulse.db"
    # Full SQLAlchemy URL (e.g. postgresql+psycopg2://user:pass@host:5432/db).
    # When set (LABPULSE_DATABASE_URL), this takes precedence over `database` (sqlite path)
    # and skips the first-run setup wizard (useful for automated/non-interactive deploys).
    database_url_override: str | None = Field(default=None, validation_alias="LABPULSE_DATABASE_URL")
    # Where the setup wizard's chosen database connection is persisted across restarts.
    config_path: str = "./data/labpulse_config.json"

    # Retention
    event_retention_days: int = 30
    metric_retention_days: int = 7

    # Collection
    poll_interval: int = 15

    # CORS - only relevant when the frontend is served separately (dev mode)
    cors_origins: list[str] = ["http://localhost:5173"]

    # Authentication (single shared admin account, credentials set via env)
    admin_username: str = "admin"
    admin_password: str = "admin"
    # Signs session tokens - set a real random value in production via LABPULSE_SECRET_KEY.
    secret_key: str = "insecure-dev-secret-change-me"
    # 7 days, with no refresh/rotation - a deliberate tradeoff for a homelab tool
    # you log into occasionally rather than a multi-user product, so sessions
    # outlive short browser sessions. Lower this if that tradeoff doesn't suit you.
    session_expire_minutes: int = 60 * 24 * 7

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        db_path = Path(self.database)
        if db_path.parent and str(db_path.parent) not in ("", "."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
