"""Incident model.

An incident is a collection of related events around a significant
occurrence, grouped via simple time-based correlation (see
``app/services/incidents.py``). ``IncidentEvent`` is a link table
recording which events belong to which incident.
"""
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel

from app.models.event import Severity


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class Incident(SQLModel, table=True):
    __tablename__ = "incidents"

    id: int | None = Field(default=None, primary_key=True)
    source_type: str = Field(index=True)
    source_id: str = Field(index=True)
    source_name: str
    title: str
    severity: Severity = Field(index=True)
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, index=True)
    started_at: datetime = Field(index=True)
    ended_at: datetime
    event_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class IncidentEvent(SQLModel, table=True):
    __tablename__ = "incident_events"

    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incidents.id", index=True)
    event_id: int = Field(foreign_key="events.id", index=True, unique=True)
