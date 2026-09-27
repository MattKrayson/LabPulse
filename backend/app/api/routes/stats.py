"""Dashboard summary statistics.

Aggregates container health and recent event counts into a single
response so the dashboard can render its status cards with one request.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.database import get_session
from app.models.container import Container
from app.models.event import Event, Severity
from app.models.incident import Incident, IncidentStatus

router = APIRouter(tags=["stats"])

_RECENT_EVENTS_WINDOW = timedelta(hours=24)


class StatsResponse(BaseModel):
    total_containers: int
    healthy: int
    warning: int
    critical: int
    recent_errors: int
    recent_incidents: int


def _classify(container: Container) -> str:
    if container.state == "running":
        if container.health_status == "unhealthy":
            return "warning"
        return "healthy"
    if container.state in ("restarting", "paused"):
        return "warning"
    if container.state in ("exited", "dead"):
        return "critical"
    return "warning"


@router.get("/stats", response_model=StatsResponse)
def get_stats(session: Session = Depends(get_session)) -> StatsResponse:
    containers = session.exec(
        select(Container).where(Container.is_present == True)  # noqa: E712
    ).all()

    healthy = warning = critical = 0
    for container in containers:
        status = _classify(container)
        if status == "healthy":
            healthy += 1
        elif status == "warning":
            warning += 1
        else:
            critical += 1

    cutoff = datetime.now(timezone.utc) - _RECENT_EVENTS_WINDOW
    recent_errors = session.exec(
        select(func.count()).select_from(Event).where(
            Event.timestamp >= cutoff,
            Event.severity.in_([Severity.ERROR, Severity.CRITICAL]),
        )
    ).one()
    recent_incidents = session.exec(
        select(func.count()).select_from(Incident).where(
            Incident.started_at >= cutoff,
            Incident.status == IncidentStatus.OPEN,
        )
    ).one()

    return StatsResponse(
        total_containers=len(containers),
        healthy=healthy,
        warning=warning,
        critical=critical,
        recent_errors=recent_errors,
        recent_incidents=recent_incidents,
    )
