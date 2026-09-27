from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.container import Container
from app.models.host import Host


def _seed_container(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        # The background poll task may have already created the local host row.
        host = session.exec(select(Host).where(Host.name == "Local Docker Host")).first()
        if host is None:
            host = Host(name="Local Docker Host", is_local=True)
            session.add(host)
            session.commit()
            session.refresh(host)

        now = datetime.now(timezone.utc)
        container = Container(
            host_id=host.id,
            container_id="abc123",
            name="pihole",
            image="pihole/pihole:latest",
            image_id="sha256:abc",
            state="running",
            status="running",
            restart_count=0,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(container)
        session.commit()


def test_list_containers(client):
    _seed_container(client)

    response = client.get("/api/containers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "pihole"


def test_get_container_by_id(client):
    _seed_container(client)

    response = client.get("/api/containers/abc123")
    assert response.status_code == 200
    assert response.json()["name"] == "pihole"


def test_get_container_not_found(client):
    response = client.get("/api/containers/does-not-exist")
    assert response.status_code == 404


def test_list_hosts(client):
    _seed_container(client)

    response = client.get("/api/hosts")
    assert response.status_code == 200
    body = response.json()
    assert any(h["name"] == "Local Docker Host" for h in body)
