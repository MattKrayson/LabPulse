"""Docker event -> LabPulse event normalisation and background listener.

Subscribes to the Docker events stream and converts relevant container
lifecycle events into rows in the generic `events` table. The listener
runs in a background daemon thread (the docker-py `events()` call blocks)
that reconnects automatically if Docker becomes unavailable, so a Docker
outage or restart never crashes the app or the listener.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.models.event import Category, Event, Severity
from app.services.docker_collector import get_client, reset_client

logger = logging.getLogger("labpulse.docker_events")

# Only these Docker container "Action"s become LabPulse events; anything
# else (e.g. exec_create, network attach) is noise for the MVP.
_RELEVANT_ACTIONS = {
    "create",
    "start",
    "stop",
    "die",
    "restart",
    "kill",
    "pause",
    "unpause",
    "destroy",
}

_RECONNECT_DELAY_SECONDS = 5

_ACTION_TEXT: dict[str, tuple[str, Severity, str]] = {
    "create": ("created", Severity.INFO, "Container created"),
    "start": ("started", Severity.INFO, "Container started"),
    "stop": ("stopped", Severity.WARNING, "Container stopped"),
    "restart": ("restarted", Severity.WARNING, "Container restarted"),
    "kill": ("killed", Severity.WARNING, "Container received a kill signal"),
    "pause": ("paused", Severity.WARNING, "Container paused"),
    "unpause": ("unpaused", Severity.INFO, "Container unpaused"),
    "destroy": ("removed", Severity.INFO, "Container removed"),
}


def _describe_action(action: str, attributes: dict[str, Any]) -> tuple[str, Severity, str]:
    """Return (verb, severity, description) for a Docker action."""
    if action.startswith("health_status"):
        status = action.split(":", 1)[1].strip() if ":" in action else attributes.get("healthStatus", "unknown")
        if status == "unhealthy":
            return "became unhealthy", Severity.ERROR, "Docker healthcheck failed"
        if status == "healthy":
            return "became healthy", Severity.INFO, "Docker healthcheck passed"
        return f"health status: {status}", Severity.INFO, "Docker healthcheck status changed"

    if action == "die":
        exit_code = str(attributes.get("exitCode", "0"))
        if exit_code != "0":
            return "exited with an error", Severity.ERROR, f"Container exited with code {exit_code}"
        return "stopped", Severity.INFO, "Container exited normally"

    return _ACTION_TEXT.get(action, (action, Severity.INFO, f"Docker action: {action}"))


def _inspect_die_reason(client: Any, container_id: str) -> tuple[bool, str | None]:
    """Best-effort lookup of OOMKilled/Error from `docker inspect`.

    Returns (oom_killed, error_message). Never raises; the die event still
    gets recorded with its exit code alone if the inspect call fails (e.g.
    the container was removed immediately after dying).
    """
    try:
        state = client.api.inspect_container(container_id).get("State") or {}
        return bool(state.get("OOMKilled")), (state.get("Error") or None)
    except Exception as exc:  # noqa: BLE001 - inspect can fail in many ways
        logger.warning("Could not inspect container %s for die reason: %s", container_id, exc)
        return False, None


_LOG_TAIL_LINES = 20
_LOG_TAIL_MAX_CHARS = 2000


def _tail_container_stderr(client: Any, container_id: str) -> str | None:
    """Best-effort grab of the container's last stderr lines at exit time.

    This is the actual application error (stack trace, "address already in
    use", etc.) that the bare exit code doesn't tell you. Returns None if
    the container has no stderr output or the logs can't be read (e.g. it
    was already removed).
    """
    try:
        raw = client.api.logs(container_id, stdout=False, stderr=True, tail=_LOG_TAIL_LINES, timestamps=False)
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return None
        return text[-_LOG_TAIL_MAX_CHARS:]
    except Exception as exc:  # noqa: BLE001 - log retrieval can fail in many ways
        logger.warning("Could not read logs for container %s: %s", container_id, exc)
        return None


def docker_event_to_labpulse(raw: dict[str, Any], client: Any = None) -> Event | None:
    """Convert a raw (decoded) Docker event dict into an Event.

    Returns None for irrelevant event types/actions or malformed payloads,
    so a single bad event never breaks the listener loop. If `client` is
    given, `die` events are enriched with the OOM-killed flag, Docker's own
    error string, and the container's last stderr output via `docker inspect`
    and `docker logs`.
    """
    try:
        if raw.get("Type") != "container":
            return None

        action = raw.get("Action", "")
        base_action = action.split(":", 1)[0]
        if base_action not in _RELEVANT_ACTIONS and not action.startswith("health_status"):
            return None

        actor = raw.get("Actor") or {}
        attributes = actor.get("Attributes") or {}
        container_id = actor.get("ID") or raw.get("id")
        if not container_id:
            return None
        name = attributes.get("name", container_id[:12])

        verb, severity, description = _describe_action(action, attributes)

        oom_killed = False
        docker_error = None
        log_tail = None
        if action == "die" and client is not None:
            oom_killed, docker_error = _inspect_die_reason(client, container_id)
            exit_code = str(attributes.get("exitCode", "0"))
            if oom_killed:
                verb, severity = "was killed (out of memory)", Severity.CRITICAL
                description = "Container was killed by the OOM killer"
            else:
                if docker_error:
                    description = f"{description}: {docker_error}"
                if exit_code != "0":
                    log_tail = _tail_container_stderr(client, container_id)
                    if log_tail:
                        description = f"{description}\n{log_tail}"

        ts = raw.get("time")
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)

        return Event(
            timestamp=timestamp,
            severity=severity,
            category=Category.DOCKER,
            source_type="container",
            source_id=container_id,
            source_name=name,
            title=f"{name} {verb}",
            description=description,
            event_metadata={
                "action": action,
                "image": attributes.get("image"),
                "oom_killed": oom_killed,
                "error": docker_error,
                "log_tail": log_tail,
            },
        )
    except (KeyError, AttributeError, TypeError) as exc:
        logger.warning("Skipping malformed Docker event: %s", exc)
        return None


_stop_flag = threading.Event()
_thread: threading.Thread | None = None


def _listen_loop(engine) -> None:
    while not _stop_flag.is_set():
        client = get_client()
        if client is None:
            _stop_flag.wait(_RECONNECT_DELAY_SECONDS)
            continue

        try:
            for raw in client.events(decode=True):
                if _stop_flag.is_set():
                    break

                event = docker_event_to_labpulse(raw, client=client)
                if event is None:
                    continue

                try:
                    with Session(engine) as session:
                        session.add(event)
                        session.commit()
                except Exception:  # noqa: BLE001 - never let a bad write kill the listener
                    logger.exception("Failed to persist Docker event")
        except Exception as exc:  # noqa: BLE001 - the event stream can fail in many ways
            if not _stop_flag.is_set():
                logger.warning("Docker event stream interrupted, reconnecting: %s", exc)
            reset_client()
            _stop_flag.wait(_RECONNECT_DELAY_SECONDS)


def start_listener(engine) -> None:
    """Start the background Docker event listener thread."""
    global _thread
    _stop_flag.clear()
    _thread = threading.Thread(target=_listen_loop, args=(engine,), daemon=True, name="docker-event-listener")
    _thread.start()


def stop_listener() -> None:
    """Signal the listener thread to stop. Does not block for it to exit."""
    _stop_flag.set()
