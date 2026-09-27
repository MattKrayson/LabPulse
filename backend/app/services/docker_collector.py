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
from app.models.event import Category, Event, Severity
from app.models.host import Host

logger = logging.getLogger("labpulse.docker_collector")

LOCAL_HOST_NAME = "Local Docker Host"

_client: docker.DockerClient | None = None
_client_failed = False
_client_error: str | None = None
_remote_clients: dict[int, docker.DockerClient] = {}
_remote_client_failed: set[int] = set()
_remote_client_errors: dict[int, str] = {}


def get_client() -> docker.DockerClient | None:
    """Return a cached Docker client for the local host, or None if unreachable."""
    global _client, _client_failed, _client_error

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
        _client_error = str(exc)
        return None

    _client = client
    return client


def reset_client() -> None:
    """Force re-connection on the next call (e.g. after Docker restarts)."""
    global _client, _client_failed, _client_error
    _client = None
    _client_failed = False
    _client_error = None


def get_client_for_host(host: Host) -> docker.DockerClient | None:
    """Return a cached Docker client for `host` (local or remote), or None if unreachable."""
    if host.is_local or not host.connection_url:
        return get_client()

    if host.id in _remote_clients:
        return _remote_clients[host.id]
    if host.id in _remote_client_failed:
        return None

    try:
        client = docker.DockerClient(base_url=host.connection_url, timeout=5)
        client.ping()
    except Exception as exc:  # noqa: BLE001 - docker-py raises a wide variety of errors
        logger.warning("Remote host %s (%s) is unreachable: %s", host.name, host.connection_url, exc)
        _remote_client_failed.add(host.id)
        _remote_client_errors[host.id] = str(exc)
        return None

    _remote_clients[host.id] = client
    _remote_client_errors.pop(host.id, None)
    return client


def reset_client_for_host(host_id: int) -> None:
    """Force re-connection to a remote host on its next poll."""
    _remote_clients.pop(host_id, None)
    _remote_client_failed.discard(host_id)
    _remote_client_errors.pop(host_id, None)


def last_connection_error(host: Host) -> str | None:
    """Return the most recent connection error for `host`, if it's currently unreachable."""
    if host.is_local:
        return _client_error if _client_failed else None
    return _remote_client_errors.get(host.id)


def test_connection(connection_url: str) -> tuple[bool, str | None]:
    """Try connecting to a remote Docker Engine API URL. Returns (ok, error)."""
    try:
        client = docker.DockerClient(base_url=connection_url, timeout=5)
        try:
            client.ping()
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001 - docker-py raises a wide variety of errors
        return False, str(exc)
    return True, None


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
            "last_error": state.get("Error") or None,
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


def _discover_for_host(session: Session, host: Host, now: datetime) -> int:
    """Poll one host and upsert its container rows. Returns containers seen."""
    client = get_client_for_host(host)
    if client is None:
        host.status = "error"
        host.last_error = last_connection_error(host)
        host.last_checked_at = now
        session.add(host)
        return 0

    try:
        containers = client.containers.list(all=True)
    except DockerException as exc:
        logger.warning("Failed to list containers on host %s: %s", host.name, exc)
        if host.is_local:
            reset_client()
        else:
            reset_client_for_host(host.id)
        return 0

    seen_ids: set[str] = set()

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

        previous_error = existing.last_error if existing is not None else None

        if existing is None:
            existing = Container(host_id=host.id, first_seen_at=now, **fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)

        existing.host_id = host.id
        existing.last_seen_at = now
        existing.is_present = True
        session.add(existing)

        new_error = existing.last_error
        if new_error and new_error != previous_error:
            # Some start failures (e.g. port already allocated) never reach the
            # Docker events stream at all, so this is the only place they surface.
            session.add(
                Event(
                    timestamp=now,
                    severity=Severity.CRITICAL,
                    category=Category.DOCKER,
                    source_type="container",
                    source_id=existing.container_id,
                    source_name=existing.name,
                    title=f"{existing.name} failed to start",
                    description=new_error,
                    event_metadata={"source": "poll", "error": new_error},
                )
            )

    # Mark containers no longer reported by this host's Docker as absent
    # without deleting their history (events/metrics may still reference them).
    previously_present = session.exec(
        select(Container).where(Container.host_id == host.id, Container.is_present == True)  # noqa: E712
    ).all()
    for container in previously_present:
        if container.container_id not in seen_ids:
            container.is_present = False
            session.add(container)

    host.status = "connected"
    host.last_error = None
    host.last_checked_at = now
    session.add(host)

    return len(seen_ids)


def discover_containers(session: Session) -> int:
    """Poll every configured host once and upsert their container rows.

    Returns the total number of containers currently reported across all
    hosts (0 if none are reachable, which is not treated as an error).
    """
    local_host = ensure_local_host(session)
    remote_hosts = session.exec(select(Host).where(Host.is_local == False)).all()  # noqa: E712

    now = datetime.now(timezone.utc)
    total_seen = 0
    for host in (local_host, *remote_hosts):
        total_seen += _discover_for_host(session, host, now)

    session.commit()
    return total_seen

