from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.container import Container
from app.models.host import Host
from app.models.snapshot import Snapshot


def _get_or_create_host(session):
    host = session.exec(select(Host).where(Host.name == "Local Docker Host")).first()
    if host is None:
        host = Host(name="Local Docker Host", is_local=True)
        session.add(host)
        session.commit()
        session.refresh(host)
    return host


def test_changes_endpoint_reports_new_container(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        host = _get_or_create_host(session)
        now = datetime.now(timezone.utc)
        session.add(
            Container(
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
        )
        session.commit()

    response = client.get("/api/changes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["type"] == "new_container"
    assert body[0]["container_name"] == "pihole"


def test_changes_endpoint_reports_container_removed(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        _get_or_create_host(session)
        session.add(
            Snapshot(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=24),
                container_id="c2",
                name="frigate",
                image="frigate:latest",
                state="running",
                restart_count=0,
            )
        )
        session.commit()

    response = client.get("/api/changes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["type"] == "container_removed"


def test_changes_endpoint_with_no_data(client):
    response = client.get("/api/changes")
    assert response.status_code == 200
    assert response.json() == []
