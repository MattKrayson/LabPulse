"""Periodic snapshot capture for "What Changed?" comparisons (Milestone 7)."""
from sqlmodel import Session, select

from app.models.container import Container
from app.models.snapshot import Snapshot


def capture_snapshot(session: Session) -> int:
    """Insert one Snapshot row per currently-present container.

    Returns the number of rows written.
    """
    containers = session.exec(
        select(Container).where(Container.is_present == True)  # noqa: E712
    ).all()

    for container in containers:
        session.add(
            Snapshot(
                container_id=container.container_id,
                name=container.name,
                image=container.image,
                state=container.state,
                health_status=container.health_status,
                restart_count=container.restart_count,
            )
        )
    session.commit()
    return len(containers)
