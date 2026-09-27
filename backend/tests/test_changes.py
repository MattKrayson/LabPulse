from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.container import Container
from app.models.host import Host
from app.models.metric import Metric, MetricType
from app.models.snapshot import Snapshot
from app.services.changes import compute_changes


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _host(session):
    host = Host(name="Local Docker Host", is_local=True)
    session.add(host)
    session.commit()
    session.refresh(host)
    return host


def _container(session, host, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        host_id=host.id,
        container_id="c1",
        name="pihole",
        image="pihole:latest",
        image_id="sha256:c1",
        state="running",
        status="running",
        restart_count=0,
        is_present=True,
        first_seen_at=now,
        last_seen_at=now,
    )
    defaults.update(overrides)
    session.add(Container(**defaults))


def _snapshot(session, age_hours=24, **overrides):
    defaults = dict(
        timestamp=datetime.now(timezone.utc) - timedelta(hours=age_hours),
        container_id="c1",
        name="pihole",
        image="pihole:latest",
        state="running",
        restart_count=0,
    )
    defaults.update(overrides)
    session.add(Snapshot(**defaults))


def test_new_container_detected_when_no_prior_snapshot():
    with _session() as session:
        host = _host(session)
        _container(session, host)
        session.commit()

        changes = compute_changes(session, since_hours=24)
        assert len(changes) == 1
        assert changes[0]["type"] == "new_container"
        assert changes[0]["container_name"] == "pihole"


def test_container_removed_when_snapshot_exists_but_not_present():
    with _session() as session:
        _host(session)
        _snapshot(session, age_hours=24)
        session.commit()

        changes = compute_changes(session, since_hours=24)
        assert len(changes) == 1
        assert changes[0]["type"] == "container_removed"
        assert changes[0]["container_name"] == "pihole"


def test_image_changed_detected():
    with _session() as session:
        host = _host(session)
        _container(session, host, image="pihole:2024")
        _snapshot(session, age_hours=24, image="pihole:2023")
        session.commit()

        changes = compute_changes(session, since_hours=24)
        types = [c["type"] for c in changes]
        assert "image_changed" in types


def test_restart_count_increase_detected():
    with _session() as session:
        host = _host(session)
        _container(session, host, restart_count=3)
        _snapshot(session, age_hours=24, restart_count=1)
        session.commit()

        changes = compute_changes(session, since_hours=24)
        restart_changes = [c for c in changes if c["type"] == "restarted"]
        assert len(restart_changes) == 1
        assert "2x" in restart_changes[0]["description"]


def test_memory_increase_detected_from_metrics():
    with _session() as session:
        host = _host(session)
        _container(session, host)
        _snapshot(session, age_hours=24)

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        session.add(Metric(timestamp=cutoff, container_id="c1", metric_type=MetricType.MEMORY_PERCENT, value=10.0))
        session.add(Metric(timestamp=now, container_id="c1", metric_type=MetricType.MEMORY_PERCENT, value=60.0))
        session.commit()

        changes = compute_changes(session, since_hours=24)
        memory_changes = [c for c in changes if c["type"] == "memory_percent_increased"]
        assert len(memory_changes) == 1


def test_no_changes_when_nothing_differs():
    with _session() as session:
        host = _host(session)
        _container(session, host)
        _snapshot(session, age_hours=24)
        session.commit()

        changes = compute_changes(session, since_hours=24)
        assert changes == []
