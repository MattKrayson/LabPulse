from sqlmodel import Session, SQLModel, create_engine, select

from app.models.container import Container
from app.services import docker_collector


class FakeContainer:
    """Mimics a docker-py Container object exposing `.attrs`."""

    def __init__(self, attrs):
        self.attrs = attrs


def make_attrs(container_id, name, image="nginx:latest", status="running", health=None):
    state = {
        "Status": status,
        "StartedAt": "2026-01-01T00:00:05.000000",
    }
    if health:
        state["Health"] = {"Status": health}

    return {
        "Id": container_id,
        "Name": f"/{name}",
        "Image": f"sha256:{container_id}",
        "Created": "2026-01-01T00:00:00.000000",
        "RestartCount": 0,
        "Config": {"Image": image},
        "State": state,
    }


class FakeContainersAPI:
    def __init__(self, containers):
        self.containers = containers

    def list(self, all=True):
        return self.containers


class FakeClient:
    def __init__(self, containers):
        self.containers = FakeContainersAPI(containers)


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_discover_containers_upserts(monkeypatch):
    fake = FakeClient([FakeContainer(make_attrs("abc123", "pihole", health="healthy"))])
    monkeypatch.setattr(docker_collector, "get_client", lambda: fake)

    with _session() as session:
        count = docker_collector.discover_containers(session)
        assert count == 1

        container = session.exec(
            select(Container).where(Container.container_id == "abc123")
        ).first()
        assert container is not None
        assert container.name == "pihole"
        assert container.health_status == "healthy"
        assert container.is_present is True


def test_discover_containers_marks_absent_when_removed(monkeypatch):
    fake = FakeClient([FakeContainer(make_attrs("abc123", "pihole"))])
    monkeypatch.setattr(docker_collector, "get_client", lambda: fake)

    with _session() as session:
        docker_collector.discover_containers(session)

        fake.containers.containers = []
        docker_collector.discover_containers(session)

        container = session.exec(
            select(Container).where(Container.container_id == "abc123")
        ).first()
        assert container.is_present is False


def test_discover_containers_skips_malformed_entries(monkeypatch):
    good = FakeContainer(make_attrs("abc123", "pihole"))
    malformed = FakeContainer({"Name": "/broken"})  # missing required "Id" key
    fake = FakeClient([good, malformed])
    monkeypatch.setattr(docker_collector, "get_client", lambda: fake)

    with _session() as session:
        count = docker_collector.discover_containers(session)
        assert count == 1


def test_discover_containers_docker_unavailable(monkeypatch):
    monkeypatch.setattr(docker_collector, "get_client", lambda: None)

    with _session() as session:
        count = docker_collector.discover_containers(session)
        assert count == 0
