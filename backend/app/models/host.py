"""Host model.

A Host represents a machine LabPulse monitors. The local Docker host row
(``is_local=True``) is created automatically during container discovery.
Remote hosts are added via the "Hosts" settings page and connect over the
Docker Engine API (e.g. ``tcp://192.168.1.20:2375`` or an SSH URL) rather
than the local Unix socket.
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

    # Docker Engine API URL for remote hosts (e.g. "tcp://192.168.1.20:2375" or
    # "ssh://user@192.168.1.20"). None for the local host, which always
    # connects via the Unix socket instead.
    connection_url: str | None = None
    status: str = Field(default="unknown")  # "connected" | "error" | "unknown"
    last_error: str | None = None
    last_checked_at: datetime | None = None
