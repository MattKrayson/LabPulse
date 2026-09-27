from datetime import datetime, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.container import Container
from app.models.host import Host
from app.models.snapshot import Snapshot
from app.services.snapshots import capture_snapshot


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _seed_container(session, host, *, container_id, name, is_present=True):
    now = datetime.now(timezone.utc)
    session.add(
        Container(
            host_id=host.id,
            container_id=container_id,
            name=name,
            image=f"{name}:latest",
            image_id=f"sha256:{container_id}",
            state="running",
            status="running",
            restart_count=0,
            is_present=is_present,
            first_seen_at=now,
            last_seen_at=now,
        )
    )


def test_capture_snapshot_only_includes_present_containers():
    with _session() as session:
        host = Host(name="Local Docker Host", is_local=True)
        session.add(host)
        session.commit()
        session.refresh(host)

        _seed_container(session, host, container_id="c1", name="pihole", is_present=True)
        _seed_container(session, host, container_id="c2", name="ghost", is_present=False)
        session.commit()

        written = capture_snapshot(session)
        assert written == 1

        snapshots = session.exec(select(Snapshot)).all()
        assert len(snapshots) == 1
        assert snapshots[0].container_id == "c1"
        assert snapshots[0].name == "pihole"


def test_capture_snapshot_with_no_containers():
    with _session() as session:
        written = capture_snapshot(session)
        assert written == 0
        assert session.exec(select(Snapshot)).all() == []
