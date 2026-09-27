"""Metrics (time-series) endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.metric import Metric, MetricType

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=list[Metric])
def list_metrics(
    session: Session = Depends(get_session),
    container_id: str = Query(..., description="Docker container ID to fetch metrics for"),
    metric_type: MetricType | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
) -> list[Metric]:
    query = select(Metric).where(Metric.container_id == container_id)
    if metric_type is not None:
        query = query.where(Metric.metric_type == metric_type)
    if since is not None:
        query = query.where(Metric.timestamp >= since)
    if until is not None:
        query = query.where(Metric.timestamp <= until)

    # Order newest-first for the limit to keep the most recent window, then
    # return chronologically so callers can plot the series directly.
    query = query.order_by(Metric.timestamp.desc()).limit(limit)
    rows = session.exec(query).all()
    return list(reversed(rows))
