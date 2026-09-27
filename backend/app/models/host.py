"""Host model.

A Host represents a machine LabPulse monitors. Milestone 1 only needs the
table to exist so the database schema and migrations are established; the
local Docker host row is created in Milestone 2 during container discovery.
"""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Host(SQLModel, table=True):
    __tablename__ = "hosts"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    hostname: str | None = None
    is_local: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
