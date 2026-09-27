from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.container import Container
from app.models.event import Category, Event, Severity
from app.models.host import Host


def _get_or_create_host(session):
    host = session.exec(select(Host).where(Host.name == "Local Docker Host")).first()
    if host is None:
        host = Host(name="Local Docker Host", is_local=True)
        session.add(host)
        session.commit()
        session.refresh(host)
    return host


def _seed_container(session, host, *, container_id, name, state, health_status=None):
    now = datetime.now(timezone.utc)
    session.add(
        Container(
            host_id=host.id,
            container_id=container_id,
            name=name,
            image=f"{name}:latest",
            image_id=f"sha256:{container_id}",
            state=state,
            status=state,
            health_status=health_status,
            restart_count=0,
            first_seen_at=now,
            last_seen_at=now,
        )
    )


def test_stats_counts_containers_and_recent_errors(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        host = _get_or_create_host(session)
        _seed_container(session, host, container_id="c1", name="pihole", state="running")
        _seed_container(
            session, host, container_id="c2", name="jellyfin", state="running", health_status="unhealthy"
        )
        _seed_container(session, host, container_id="c3", name="frigate", state="exited")
        session.commit()

        session.add(
            Event(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                severity=Severity.ERROR,
                category=Category.DOCKER,
                source_type="container",
                source_id="c3",
                source_name="frigate",
                title="frigate exited with an error",
            )
        )
        session.add(
            Event(
                timestamp=datetime.now(timezone.utc) - timedelta(days=2),
                severity=Severity.ERROR,
                category=Category.DOCKER,
                source_type="container",
                source_id="c3",
                source_name="frigate",
                title="old error, outside the 24h window",
            )
        )
        session.commit()

    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_containers"] == 3
    assert body["healthy"] == 1
    assert body["warning"] == 1
    assert body["critical"] == 1
    assert body["recent_errors"] == 1
    assert body["recent_incidents"] == 0


def test_stats_with_no_data(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_containers"] == 0
    assert body["healthy"] == 0
    assert body["warning"] == 0
    assert body["critical"] == 0
    assert body["recent_errors"] == 0
    assert body["recent_incidents"] == 0
