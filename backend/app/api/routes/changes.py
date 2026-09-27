""""What Changed?" endpoint (Milestone 7)."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.services.changes import compute_changes

router = APIRouter(tags=["changes"])


class ChangeEntry(BaseModel):
    type: str
    container_id: str
    container_name: str
    description: str
    detail: str | None = None


@router.get("/changes", response_model=list[ChangeEntry])
def get_changes(
    session: Session = Depends(get_session),
    since_hours: int = Query(
        24, ge=1, le=24 * 30, description="Compare current state against this many hours ago"
    ),
) -> list[ChangeEntry]:
    return compute_changes(session, since_hours=since_hours)
