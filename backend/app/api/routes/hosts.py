"""Host endpoints."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.host import Host

router = APIRouter(tags=["hosts"])


@router.get("/hosts", response_model=list[Host])
def list_hosts(session: Session = Depends(get_session)) -> list[Host]:
    return session.exec(select(Host)).all()
