"""Container endpoints.

Returns discovered Docker containers. Paginated to avoid ever returning an
unbounded result set.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.container import Container

router = APIRouter(tags=["containers"])


@router.get("/containers", response_model=list[Container])
def list_containers(
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_absent: bool = Query(False, description="Include containers no longer seen by Docker"),
) -> list[Container]:
    query = select(Container)
    if not include_absent:
        query = query.where(Container.is_present == True)  # noqa: E712
    query = query.order_by(Container.name).offset(offset).limit(limit)
    return session.exec(query).all()


@router.get("/containers/{container_id}", response_model=Container)
def get_container(container_id: str, session: Session = Depends(get_session)) -> Container:
    container = session.exec(
        select(Container).where(Container.container_id == container_id)
    ).first()
    if container is None:
        raise HTTPException(status_code=404, detail="Container not found")
    return container
