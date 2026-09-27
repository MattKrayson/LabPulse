"""Event model.

A generic, normalised record of something that happened, regardless of
source (Docker today; host/network/etc. in later milestones). This is the
backbone of the timeline.
"""
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Category(str, Enum):
    DOCKER = "DOCKER"
    HOST = "HOST"
    NETWORK = "NETWORK"
    STORAGE = "STORAGE"
    SERVICE = "SERVICE"
    SYSTEM = "SYSTEM"
    APPLICATION = "APPLICATION"


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(index=True)
    severity: Severity = Field(index=True)
    category: Category = Field(index=True)
    source_type: str = Field(index=True)
    source_id: str = Field(index=True)
    source_name: str
    title: str
    description: str | None = None
    # Named `event_metadata` in Python because `metadata` is reserved by
    # SQLAlchemy's declarative base; the DB column itself is still `metadata`.
    event_metadata: dict | None = Field(default=None, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=_utcnow)
