"""Container model.

Represents a Docker container discovered on a Host. Rows are updated in
place on each poll (matched by Docker's container_id) rather than
recreated, so `first_seen_at` history survives restarts. Containers that
disappear from Docker are marked `is_present = False` rather than deleted,
so historical association with events/metrics is preserved.
"""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Container(SQLModel, table=True):
    __tablename__ = "containers"

    id: int | None = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="hosts.id", index=True)

    container_id: str = Field(index=True, unique=True)
    name: str = Field(index=True)
    image: str
    image_id: str

    created_at: datetime | None = None
    state: str = Field(index=True)
    status: str
    health_status: str | None = None
    restart_count: int = 0
    started_at: datetime | None = None
    last_error: str | None = None

    is_present: bool = Field(default=True, index=True)
    first_seen_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)
