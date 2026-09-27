"""Snapshot model.

A lightweight point-in-time capture of a container's key attributes,
taken periodically (hourly). Snapshots exist purely to power deterministic
"What Changed?" comparisons (e.g. now vs 24 hours ago) — they are not a
full audit log and do not replace the `containers` table as the source of
truth for current state.
"""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Snapshot(SQLModel, table=True):
    __tablename__ = "snapshots"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=_utcnow, index=True)

    container_id: str = Field(index=True)
    name: str
    image: str
    state: str
    health_status: str | None = None
    restart_count: int = 0

    created_at: datetime = Field(default_factory=_utcnow)
