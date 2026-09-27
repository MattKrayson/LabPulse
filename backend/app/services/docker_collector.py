"""Docker discovery and container polling.

Connects to the local Docker daemon via its socket (never TCP), lists
containers, and keeps the `containers` table in sync. Designed to survive:

* Docker being temporarily unavailable
* containers disappearing or restarting mid-poll
* malformed/unexpected container data

A single failure never crashes the caller; it just yields zero discovered
containers for that poll.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import docker
from docker.errors import DockerException
from sqlmodel import Session, select

from app.models.container import Container
from app.models.host import Host

logger = logging.getLogger("labpulse.docker_collector")

LOCAL_HOST_NAME = "Local Docker Host"

_client: docker.DockerClient | None = None
_client_failed = False


def get_client() -> docker.DockerClient | None:
    """Return a cached Docker client, or None if Docker is unreachable."""
    global _client, _client_failed

    if _client is not None:
        return _client
    if _client_failed:
        return None

    try:
        client = docker.from_env(timeout=5)
        client.ping()
    except Exception as exc:  # noqa: BLE001 - docker-py raises a wide variety of errors
        logger.warning("Docker is unavailable: %s", exc)
        _client_failed = True
        return None

    _client = client
    return client


def reset_client() -> None:
    """Force re-connection on the next call (e.g. after Docker restarts)."""
    global _client, _client_failed
    _client = None
    _client_failed = False


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _extract_fields(attrs: dict[str, Any]) -> dict[str, Any] | None:
    """Defensively pull the fields we care about out of raw Docker attrs."""
    try:
        container_id = attrs["Id"]
        name = attrs.get("Name", "").lstrip("/") or container_id[:12]
        config = attrs.get("Config") or {}
        state = attrs.get("State") or {}
        health = state.get("Health") or {}

        return {
            "container_id": container_id,
            "name": name,
            "image": config.get("Image", "unknown"),
            "image_id": attrs.get("Image", "unknown"),
            "created_at": _parse_datetime(attrs.get("Created")),
            "state": state.get("Status", "unknown"),
            "status": state.get("Status", "unknown"),
            "health_status": health.get("Status"),
            "restart_count": attrs.get("RestartCount", 0) or 0,
            "started_at": _parse_datetime(state.get("StartedAt")),
        }
    except (KeyError, AttributeError, TypeError) as exc:
        logger.warning("Skipping malformed container data: %s", exc)
        return None


def ensure_local_host(session: Session) -> Host:
    host = session.exec(select(Host).where(Host.name == LOCAL_HOST_NAME)).first()
    if host is None:
        host = Host(name=LOCAL_HOST_NAME, hostname=None, is_local=True)
        session.add(host)
        session.commit()
        session.refresh(host)
    return host


def discover_containers(session: Session) -> int:
    """Poll Docker once and upsert container rows.

    Returns the number of containers currently reported by Docker (0 if
    Docker is unavailable, which is not treated as an error).
    """
    host = ensure_local_host(session)

    client = get_client()
    if client is None:
        return 0

    try:
        containers = client.containers.list(all=True)
    except DockerException as exc:
        logger.warning("Failed to list containers: %s", exc)
        reset_client()
        return 0

    seen_ids: set[str] = set()
    now = datetime.now(timezone.utc)

    for raw in containers:
        try:
            attrs = raw.attrs
        except DockerException as exc:
            # The container disappeared between list() and reading its attrs.
            logger.warning("Container disappeared mid-poll: %s", exc)
            continue

        fields = _extract_fields(attrs)
        if fields is None:
            continue

        seen_ids.add(fields["container_id"])

        existing = session.exec(
            select(Container).where(Container.container_id == fields["container_id"])
        ).first()

        if existing is None:
            existing = Container(host_id=host.id, first_seen_at=now, **fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)

        existing.last_seen_at = now
        existing.is_present = True
        session.add(existing)

    # Mark containers no longer reported by Docker as absent without deleting
    # their history (events/metrics may still reference them).
    previously_present = session.exec(
        select(Container).where(Container.host_id == host.id, Container.is_present == True)  # noqa: E712
    ).all()
    for container in previously_present:
        if container.container_id not in seen_ids:
            container.is_present = False
            session.add(container)

    session.commit()
    return len(seen_ids)
