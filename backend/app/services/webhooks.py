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

# Severity accent colors, keyed for a freshly-opened incident. Resolved
# incidents always render green regardless of severity, since the point is
# "this is over now". Discord wants decimal ints, Slack wants hex strings.
_SEVERITY_COLORS_DECIMAL = {
    "critical": 0xE74C3C,  # red
    "warning": 0xF1C40F,   # yellow
    "info": 0x3498DB,      # blue
}
_RESOLVED_COLOR_DECIMAL = 0x2ECC71  # green

_SEVERITY_COLORS_HEX = {
    "critical": "#E74C3C",
    "warning": "#F1C40F",
    "info": "#3498DB",
}
_RESOLVED_COLOR_HEX = "#2ECC71"

# ntfy emoji tags (https://docs.ntfy.sh/emojis/) keyed by severity for an
# opened incident; resolved incidents always use the checkmark.
_NTFY_SEVERITY_TAGS = {
    "critical": "rotating_light",
    "warning": "warning",
    "info": "information_source",
}
_NTFY_RESOLVED_TAG = "white_check_mark"
_NTFY_SEVERITY_PRIORITY = {
    "critical": "urgent",
    "warning": "high",
    "info": "default",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _accent_color(incident: Incident, event_type: str, *, hex_format: bool) -> str | int:
    colors = _SEVERITY_COLORS_HEX if hex_format else _SEVERITY_COLORS_DECIMAL
    resolved_color = _RESOLVED_COLOR_HEX if hex_format else _RESOLVED_COLOR_DECIMAL
    if event_type != "incident.opened":
        return resolved_color
    return colors.get(incident.severity.value, colors["info"])


def _build_discord_payload(incident: Incident, event_type: str) -> dict:
    """Rich embed for Discord: title, colored side-bar, and fields instead
    of a single line of plain text."""
    opened = event_type == "incident.opened"
    verb = "opened" if opened else "resolved"

    fields = [
        {"name": "Severity", "value": incident.severity.value.title(), "inline": True},
        {"name": "Status", "value": incident.status.value.title(), "inline": True},
        {"name": "Events", "value": str(incident.event_count), "inline": True},
        {"name": "Source", "value": incident.source_name or incident.source_type, "inline": True},
        {"name": "Started", "value": incident.started_at.isoformat(), "inline": True},
    ]
    if not opened and incident.ended_at:
        fields.append({"name": "Ended", "value": incident.ended_at.isoformat(), "inline": True})

    embed = {
        "title": f"{'🔴' if opened else '✅'} Incident {verb}",
        "description": incident.title,
        "color": _accent_color(incident, event_type, hex_format=False),
        "fields": fields,
        "footer": {"text": "LabPulse"},
        "timestamp": _utcnow().isoformat(),
    }

    return {"embeds": [embed]}


def _build_slack_payload(incident: Incident, event_type: str) -> dict:
    """Slack Block Kit message: header, field grid, and a colored side-bar
    via a single-block attachment, instead of a plain `text` string."""
    opened = event_type == "incident.opened"
    verb = "Opened" if opened else "Resolved"
    emoji = "🔴" if opened else "✅"

    fields = [
        {"type": "mrkdwn", "text": f"*Severity*\n{incident.severity.value.title()}"},
        {"type": "mrkdwn", "text": f"*Status*\n{incident.status.value.title()}"},
        {"type": "mrkdwn", "text": f"*Events*\n{incident.event_count}"},
        {"type": "mrkdwn", "text": f"*Source*\n{incident.source_name or incident.source_type}"},
    ]

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} Incident {verb}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{incident.title}*"}},
        {"type": "section", "fields": fields},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"LabPulse • {_utcnow().strftime('%b %d, %H:%M UTC')}"}],
        },
    ]

    fallback_text = f"[LabPulse] {incident.title} {verb.lower()} ({incident.severity.value})"
    return {
        "text": fallback_text,
        "attachments": [{"color": _accent_color(incident, event_type, hex_format=True), "blocks": blocks}],
    }


def _build_ntfy_payload(incident: Incident, event_type: str) -> dict:
    """ntfy JSON publish format with emoji tags and severity-based priority
    instead of a flat, untagged message."""
    opened = event_type == "incident.opened"
    tag = _NTFY_SEVERITY_TAGS.get(incident.severity.value, "information_source") if opened else _NTFY_RESOLVED_TAG
    priority = _NTFY_SEVERITY_PRIORITY.get(incident.severity.value, "default") if opened else "default"

    return {
        "title": f"{'Incident opened' if opened else 'Incident resolved'} · {incident.severity.value.title()}",
        "message": (
            f"{incident.title}\n"
            f"Source: {incident.source_name or incident.source_type} · {incident.event_count} event(s)"
        ),
        "priority": priority,
        "tags": [tag],
    }


def _build_payload(webhook: Webhook, incident: Incident, event_type: str) -> dict:
    """Shape the outgoing JSON body for the webhook's target format."""
    if webhook.format == "discord":
        return _build_discord_payload(incident, event_type)
    if webhook.format == "slack":
        return _build_slack_payload(incident, event_type)
    if webhook.format == "ntfy":
        return _build_ntfy_payload(incident, event_type)

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