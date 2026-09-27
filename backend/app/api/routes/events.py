"""Event (timeline) endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.event import Category, Event, Severity

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[Event])
def list_events(
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    severity: Severity | None = Query(None),
    category: Category | None = Query(None),
    source_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    q: str | None = Query(None, description="Search event titles"),
) -> list[Event]:
    query = select(Event)
    if severity is not None:
        query = query.where(Event.severity == severity)
    if category is not None:
        query = query.where(Event.category == category)
    if source_id is not None:
        query = query.where(Event.source_id == source_id)
    if since is not None:
        query = query.where(Event.timestamp >= since)
    if until is not None:
        query = query.where(Event.timestamp <= until)
    if q:
        query = query.where(Event.title.ilike(f"%{q}%"))

    query = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    return session.exec(query).all()


@router.get("/events/{event_id}", response_model=Event)
def get_event(event_id: int, session: Session = Depends(get_session)) -> Event:
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
