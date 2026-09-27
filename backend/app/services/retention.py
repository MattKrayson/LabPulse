"""Automatic data retention.

Keeps the SQLite database from growing indefinitely by deleting events
older than `LABPULSE_EVENT_RETENTION_DAYS` and metrics older than
`LABPULSE_METRIC_RETENTION_DAYS`. Snapshots (one row per container per
hour) are pruned on the same schedule as events, since they're needed for
"What Changed?" comparisons over similar timeframes and no dedicated
retention setting is warranted for the MVP. Resolved incidents (and their
event links) older than the event retention window are pruned the same
way; open incidents are never pruned.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.event import Event
from app.models.incident import Incident, IncidentEvent, IncidentStatus
from app.models.metric import Metric
from app.models.snapshot import Snapshot


def cleanup_events(session: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.event_retention_days)
    result = session.execute(delete(Event).where(Event.timestamp < cutoff))
    session.commit()
    return result.rowcount or 0


def cleanup_metrics(session: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.metric_retention_days)
    result = session.execute(delete(Metric).where(Metric.timestamp < cutoff))
    session.commit()
    return result.rowcount or 0


def cleanup_snapshots(session: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.event_retention_days)
    result = session.execute(delete(Snapshot).where(Snapshot.timestamp < cutoff))
    session.commit()
    return result.rowcount or 0


def cleanup_incidents(session: Session) -> int:
    """Delete resolved incidents (and their event links) past the event
    retention window; open incidents are never pruned.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.event_retention_days)
    stale_ids = session.execute(
        select(Incident.id).where(
            Incident.status == IncidentStatus.RESOLVED, Incident.ended_at < cutoff
        )
    ).scalars().all()
    if not stale_ids:
        return 0
    session.execute(delete(IncidentEvent).where(IncidentEvent.incident_id.in_(stale_ids)))
    result = session.execute(delete(Incident).where(Incident.id.in_(stale_ids)))
    session.commit()
    return result.rowcount or 0
