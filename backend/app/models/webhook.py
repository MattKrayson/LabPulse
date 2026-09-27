"""Webhook model.

A Webhook is a URL LabPulse notifies whenever an incident opens or resolves,
so alerts reach somewhere people actually look (Discord/Slack/ntfy/a generic
HTTP endpoint) rather than only appearing on the dashboard.
"""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Webhook(SQLModel, table=True):
    __tablename__ = "webhooks"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    url: str
    # Payload shape to send: "generic" (raw JSON), "discord", "slack", or "ntfy".
    format: str = Field(default="generic")
    enabled: bool = Field(default=True)
    notify_on_open: bool = Field(default=True)
    notify_on_resolve: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)
    last_triggered_at: datetime | None = None
    last_error: str | None = None
