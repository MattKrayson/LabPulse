"""Webhook CRUD and test-delivery endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.event import Severity
from app.models.incident import Incident, IncidentStatus
from app.models.webhook import Webhook

router = APIRouter(tags=["webhooks"])

_VALID_FORMATS = {"generic", "discord", "slack", "ntfy"}


class WebhookCreate(BaseModel):
    name: str
    url: str
    format: str = Field(default="generic")
    enabled: bool = True
    notify_on_open: bool = True
    notify_on_resolve: bool = False


@router.get("/webhooks", response_model=list[Webhook])
def list_webhooks(session: Session = Depends(get_session)) -> list[Webhook]:
    return session.exec(select(Webhook)).all()


@router.post("/webhooks", response_model=Webhook)
def create_webhook(body: WebhookCreate, session: Session = Depends(get_session)) -> Webhook:
    if body.format not in _VALID_FORMATS:
        raise HTTPException(status_code=422, detail=f"format must be one of {sorted(_VALID_FORMATS)}")
    webhook = Webhook(**body.model_dump())
    session.add(webhook)
    session.commit()
    session.refresh(webhook)
    return webhook


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: int, session: Session = Depends(get_session)) -> None:
    webhook = session.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    session.delete(webhook)
    session.commit()


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, session: Session = Depends(get_session)) -> dict:
    webhook = session.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    now = datetime.now()
    fake_incident = Incident(
        id=0,
        source_type="test",
        source_id="labpulse-test",
        source_name="LabPulse",
        title="Test notification",
        severity=Severity.INFO,
        status=IncidentStatus.OPEN,
        started_at=now,
        ended_at=now,
        event_count=1,
    )
    notify_incident_for_test(session, webhook, fake_incident)
    session.refresh(webhook)
    if webhook.last_error:
        raise HTTPException(status_code=502, detail=webhook.last_error)
    return {"ok": True}


def notify_incident_for_test(session: Session, webhook: Webhook, incident: Incident) -> None:
    """Send a single test notification, bypassing the enabled/notify_on_* filters
    used for real incident delivery."""
    from app.services.webhooks import _deliver  # local import to avoid a public API surface

    _deliver(webhook, incident, "incident.opened")
    session.add(webhook)
    session.commit()
