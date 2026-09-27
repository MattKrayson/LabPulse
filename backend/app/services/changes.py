"""Deterministic "What Changed?" comparison logic (Milestone 7).

Compares the current state of the world against the closest `Snapshot`
taken at or before `since_hours` ago (default 24h) and reports meaningful
differences using simple, deterministic rules — no ML/anomaly detection,
per spec section 20.
"""
from datetime import datetime, timedelta, timezone
from statistics import fmean
from typing import TypedDict

from sqlmodel import Session, select

from app.models.container import Container
from app.models.metric import Metric, MetricType
from app.models.snapshot import Snapshot

# Minimum change in average CPU%/memory% (percentage points) worth reporting.
_RESOURCE_DELTA_THRESHOLD = 15.0
_METRIC_WINDOW_MINUTES = 60


class Change(TypedDict):
    type: str
    container_id: str
    container_name: str
    description: str
    detail: str | None


def _closest_snapshots(session: Session, cutoff: datetime) -> dict[str, Snapshot]:
    """For each container_id, the most recent snapshot at or before cutoff."""
    rows = session.exec(
        select(Snapshot)
        .where(Snapshot.timestamp <= cutoff)
        .order_by(Snapshot.timestamp.desc())
    ).all()
    closest: dict[str, Snapshot] = {}
    for row in rows:
        closest.setdefault(row.container_id, row)
    return closest


def _avg_metric(
    session: Session, container_id: str, metric_type: MetricType, reference: datetime
) -> float | None:
    start = reference - timedelta(minutes=_METRIC_WINDOW_MINUTES)
    values = session.exec(
        select(Metric.value).where(
            Metric.container_id == container_id,
            Metric.metric_type == metric_type,
            Metric.timestamp >= start,
            Metric.timestamp <= reference,
        )
    ).all()
    return fmean(values) if values else None


def compute_changes(session: Session, since_hours: int = 24) -> list[Change]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=since_hours)

    snapshots = _closest_snapshots(session, cutoff)
    current_containers = {
        c.container_id: c
        for c in session.exec(
            select(Container).where(Container.is_present == True)  # noqa: E712
        ).all()
    }

    changes: list[Change] = []

    for container_id, container in current_containers.items():
        snapshot = snapshots.get(container_id)

        if snapshot is None:
            changes.append(
                Change(
                    type="new_container",
                    container_id=container_id,
                    container_name=container.name,
                    description=f"New container detected: {container.name}",
                    detail=f"Image: {container.image} · state: {container.state}",
                )
            )
            continue

        if snapshot.image != container.image:
            changes.append(
                Change(
                    type="image_changed",
                    container_id=container_id,
                    container_name=container.name,
                    description=(
                        f"{container.name} image changed "
                        f"({snapshot.image} → {container.image})"
                    ),
                    detail=None,
                )
            )

        restart_delta = container.restart_count - snapshot.restart_count
        if restart_delta > 0:
            changes.append(
                Change(
                    type="restarted",
                    container_id=container_id,
                    container_name=container.name,
                    description=(
                        f"{container.name} restarted "
                        f"({restart_delta}x in the last {since_hours}h)"
                    ),
                    detail=f"Total restart count: {container.restart_count}",
                )
            )

        for metric_type, label in (
            (MetricType.CPU_PERCENT, "CPU"),
            (MetricType.MEMORY_PERCENT, "memory"),
        ):
            before = _avg_metric(session, container_id, metric_type, cutoff)
            after = _avg_metric(session, container_id, metric_type, now)
            if before is None or after is None:
                continue
            delta = after - before
            if abs(delta) >= _RESOURCE_DELTA_THRESHOLD:
                direction = "increased" if delta > 0 else "decreased"
                changes.append(
                    Change(
                        type=f"{metric_type.value}_{direction}",
                        container_id=container_id,
                        container_name=container.name,
                        description=(
                            f"{container.name} {label} usage {direction} "
                            f"({before:.1f}% → {after:.1f}%)"
                        ),
                        detail=f"Average over the trailing hour, compared {since_hours}h apart",
                    )
                )

    for container_id, snapshot in snapshots.items():
        if container_id not in current_containers:
            changes.append(
                Change(
                    type="container_removed",
                    container_id=container_id,
                    container_name=snapshot.name,
                    description=f"Container removed: {snapshot.name}",
                    detail=f"Last known image: {snapshot.image}",
                )
            )

    changes.sort(key=lambda c: c["container_name"])
    return changes
