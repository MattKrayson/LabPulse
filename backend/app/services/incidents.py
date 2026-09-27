"""Incident correlation.

Simple, deterministic time-based correlation (per the spec: no ML). Events
belonging to the same source that occur close together in time are grouped
into a single incident; a gap of more than ``_CORRELATION_GAP`` between
events (or since the last event of an open incident) starts a new one.
"""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.event import Event, Severity
from app.models.incident import Incident, IncidentEvent, IncidentStatus

_CORRELATION_GAP = timedelta(minutes=5)
_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def correlate_incidents(session: Session, gap: timedelta = _CORRELATION_GAP) -> int:
    """Group any events not yet attached to an incident into incidents.

    Returns the number of events newly attached to an incident.
    """
    linked_event_ids = select(IncidentEvent.event_id)
    unlinked_events = session.exec(
        select(Event)
        .where(~Event.id.in_(linked_event_ids))
        .order_by(Event.source_id, Event.timestamp)
    ).all()

    by_source: dict[str, list[Event]] = {}
    for event in unlinked_events:
        by_source.setdefault(event.source_id, []).append(event)

    attached = 0
    for source_id, events in by_source.items():
        current = session.exec(
            select(Incident)
            .where(Incident.source_id == source_id, Incident.status == IncidentStatus.OPEN)
            .order_by(Incident.started_at.desc())
        ).first()

        for event in events:
            if current is not None and (event.timestamp - current.ended_at) <= gap:
                current.ended_at = event.timestamp
                current.event_count += 1
                current.updated_at = _utcnow()
                if _SEVERITY_RANK[event.severity] > _SEVERITY_RANK[current.severity]:
                    current.severity = event.severity
                session.add(current)
            else:
                if current is not None:
                    current.status = IncidentStatus.RESOLVED
                    session.add(current)
                current = Incident(
                    source_type=event.source_type,
                    source_id=event.source_id,
                    source_name=event.source_name,
                    title=f"{event.source_name} incident",
                    severity=event.severity,
                    status=IncidentStatus.OPEN,
                    started_at=event.timestamp,
                    ended_at=event.timestamp,
                    event_count=1,
                )
                session.add(current)
                session.flush()

            session.add(IncidentEvent(incident_id=current.id, event_id=event.id))
            attached += 1

    session.commit()

    # Incidents with no new events for longer than the gap are done.
    now = _utcnow()
    stale_cutoff = now - gap
    stale_open = session.exec(
        select(Incident).where(
            Incident.status == IncidentStatus.OPEN, Incident.ended_at < stale_cutoff
        )
    ).all()
    for incident in stale_open:
        incident.status = IncidentStatus.RESOLVED
        session.add(incident)
    if stale_open:
        session.commit()

    return attached
