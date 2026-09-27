"""Webhook delivery for incident open/resolve notifications.

Fires a best-effort HTTP POST to every enabled webhook when an incident is
opened or resolved. Delivery failures are logged and recorded on the
webhook row, but never raise - a broken webhook must not stop incident
correlation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from sqlmodel import Session, select

from app.models.incident import Incident
from app.models.webhook import Webhook

logger = logging.getLogger("labpulse.webhooks")

_REQUEST_TIMEOUT_SECONDS = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_payload(webhook: Webhook, incident: Incident, event_type: str) -> dict:
    """Shape the outgoing JSON body for the webhook's target format."""
    verb = "opened" if event_type == "incident.opened" else "resolved"
    text = (
        f"[LabPulse] {incident.title} {verb} "
        f"({incident.severity.value}, {incident.event_count} event(s))"
    )

    if webhook.format == "discord":
        return {"content": text}
    if webhook.format == "slack":
        return {"text": text}
    if webhook.format == "ntfy":
        return {"message": text, "title": "LabPulse", "priority": "urgent" if verb == "opened" else "default"}

    # generic: raw structured payload for custom integrations
    return {
        "event": event_type,
        "incident": {
            "id": incident.id,
            "source_type": incident.source_type,
            "source_id": incident.source_id,
            "source_name": incident.source_name,
            "title": incident.title,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "started_at": incident.started_at.isoformat(),
            "ended_at": incident.ended_at.isoformat(),
            "event_count": incident.event_count,
        },
    }


def _deliver(webhook: Webhook, incident: Incident, event_type: str) -> None:
    payload = _build_payload(webhook, incident, event_type)
    headers = {"Content-Type": "application/json"} if webhook.format == "ntfy" else None
    try:
        response = requests.post(webhook.url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        webhook.last_error = None
    except requests.RequestException as exc:
        webhook.last_error = str(exc)
        logger.warning("Webhook %s (%s) delivery failed: %s", webhook.id, webhook.name, exc)
    webhook.last_triggered_at = _utcnow()


def notify_incident(session: Session, incident: Incident, event_type: str) -> None:
    """Send `incident` to every enabled webhook subscribed to `event_type`
    ("incident.opened" or "incident.resolved")."""
    field = "notify_on_open" if event_type == "incident.opened" else "notify_on_resolve"
    webhooks = session.exec(
        select(Webhook).where(Webhook.enabled == True, getattr(Webhook, field) == True)  # noqa: E712
    ).all()
    if not webhooks:
        return
    for webhook in webhooks:
        _deliver(webhook, incident, event_type)
        session.add(webhook)
    session.commit()
