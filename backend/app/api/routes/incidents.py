"""Incident endpoints.

An incident detail response nests its correlated events (most recent
first) so the frontend can render the timeline shown in the spec's example.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.event import Event, Severity
from app.models.incident import Incident, IncidentEvent, IncidentStatus

router = APIRouter(tags=["incidents"])


class IncidentSummary(BaseModel):
    id: int
    source_type: str
    source_id: str
    source_name: str
    title: str
    severity: Severity
    status: IncidentStatus
    started_at: datetime
    ended_at: datetime
    event_count: int


class IncidentDetail(IncidentSummary):
    events: list[Event]


@router.get("/incidents", response_model=list[IncidentSummary])
def list_incidents(
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: IncidentStatus | None = Query(None),
    source_id: str | None = Query(None),
    since: datetime | None = Query(None),
) -> list[Incident]:
    query = select(Incident)
    if status is not None:
        query = query.where(Incident.status == status)
    if source_id is not None:
        query = query.where(Incident.source_id == source_id)
    if since is not None:
        query = query.where(Incident.started_at >= since)

    query = query.order_by(Incident.started_at.desc()).offset(offset).limit(limit)
    return session.exec(query).all()


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: int, session: Session = Depends(get_session)) -> IncidentDetail:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    events = session.exec(
        select(Event)
        .join(IncidentEvent, IncidentEvent.event_id == Event.id)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(Event.timestamp.desc())
    ).all()

    return IncidentDetail(**incident.model_dump(), events=events)
