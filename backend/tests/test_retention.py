from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.models.event import Category, Event, Severity
from app.models.incident import Incident, IncidentEvent, IncidentStatus
from app.models.metric import Metric, MetricType
from app.models.snapshot import Snapshot
from app.services import retention


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _make_event(age_days):
    return Event(
        timestamp=datetime.now(timezone.utc) - timedelta(days=age_days),
        severity=Severity.INFO,
        category=Category.DOCKER,
        source_type="container",
        source_id="abc123",
        source_name="pihole",
        title="pihole started",
    )


def test_cleanup_events_removes_old_rows(monkeypatch):
    monkeypatch.setenv("LABPULSE_EVENT_RETENTION_DAYS", "30")
    get_settings.cache_clear()

    try:
        with _session() as session:
            session.add(_make_event(age_days=45))
            session.add(_make_event(age_days=1))
            session.commit()

            deleted = retention.cleanup_events(session)
            assert deleted == 1

            remaining = session.exec(select(Event)).all()
            assert len(remaining) == 1
            assert remaining[0].title == "pihole started"
    finally:
        get_settings.cache_clear()


def _make_metric(age_days):
    return Metric(
        timestamp=datetime.now(timezone.utc) - timedelta(days=age_days),
        container_id="abc123",
        metric_type=MetricType.CPU_PERCENT,
        value=42.0,
    )


def test_cleanup_metrics_removes_old_rows(monkeypatch):
    monkeypatch.setenv("LABPULSE_METRIC_RETENTION_DAYS", "7")
    get_settings.cache_clear()

    try:
        with _session() as session:
            session.add(_make_metric(age_days=10))
            session.add(_make_metric(age_days=1))
            session.commit()

            deleted = retention.cleanup_metrics(session)
            assert deleted == 1

            remaining = session.exec(select(Metric)).all()
            assert len(remaining) == 1
    finally:
        get_settings.cache_clear()


def _make_snapshot(age_days):
    return Snapshot(
        timestamp=datetime.now(timezone.utc) - timedelta(days=age_days),
        container_id="abc123",
        name="pihole",
        image="pihole:latest",
        state="running",
        restart_count=0,
    )


def test_cleanup_snapshots_removes_old_rows(monkeypatch):
    monkeypatch.setenv("LABPULSE_EVENT_RETENTION_DAYS", "30")
    get_settings.cache_clear()

    try:
        with _session() as session:
            session.add(_make_snapshot(age_days=45))
            session.add(_make_snapshot(age_days=1))
            session.commit()

            deleted = retention.cleanup_snapshots(session)
            assert deleted == 1

            remaining = session.exec(select(Snapshot)).all()
            assert len(remaining) == 1
    finally:
        get_settings.cache_clear()


def _make_incident(age_days, status=IncidentStatus.RESOLVED):
    ended_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    return Incident(
        source_type="container",
        source_id="abc123",
        source_name="pihole",
        title="pihole incident",
        severity=Severity.WARNING,
        status=status,
        started_at=ended_at,
        ended_at=ended_at,
        event_count=1,
    )


def test_cleanup_incidents_removes_old_resolved_rows_and_links(monkeypatch):
    monkeypatch.setenv("LABPULSE_EVENT_RETENTION_DAYS", "30")
    get_settings.cache_clear()

    try:
        with _session() as session:
            old_incident = _make_incident(age_days=45)
            recent_incident = _make_incident(age_days=1)
            open_incident = _make_incident(age_days=45, status=IncidentStatus.OPEN)
            session.add(old_incident)
            session.add(recent_incident)
            session.add(open_incident)
            session.commit()
            session.refresh(old_incident)
            session.add(IncidentEvent(incident_id=old_incident.id, event_id=1))
            session.commit()

            deleted = retention.cleanup_incidents(session)
            assert deleted == 1

            remaining = session.exec(select(Incident)).all()
            assert len(remaining) == 2

            remaining_links = session.exec(select(IncidentEvent)).all()
            assert remaining_links == []
    finally:
        get_settings.cache_clear()

