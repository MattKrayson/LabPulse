"""Host endpoints.

Remote hosts connect over the Docker Engine API (a TCP or SSH URL) rather
than the local Unix socket the app itself always uses for its own host.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.container import Container
from app.models.host import Host
from app.services.docker_collector import reset_client_for_host, test_connection

router = APIRouter(tags=["hosts"])


class HostCreate(BaseModel):
    name: str
    connection_url: str
    hostname: str | None = None
    tls_ca_cert: str | None = None
    tls_client_cert: str | None = None
    tls_client_key: str | None = None


def _validate_tls_fields(body: HostCreate) -> None:
    if bool(body.tls_client_cert) != bool(body.tls_client_key):
        raise HTTPException(
            status_code=422, detail="tls_client_cert and tls_client_key must be provided together"
        )


@router.get("/hosts", response_model=list[Host])
def list_hosts(session: Session = Depends(get_session)) -> list[Host]:
    return session.exec(select(Host)).all()


@router.post("/hosts", response_model=Host)
def create_host(body: HostCreate, session: Session = Depends(get_session)) -> Host:
    existing = session.exec(select(Host).where(Host.name == body.name)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A host with this name already exists")
    _validate_tls_fields(body)

    ok, error = test_connection(
        body.connection_url, body.tls_ca_cert, body.tls_client_cert, body.tls_client_key
    )
    host = Host(
        name=body.name,
        hostname=body.hostname,
        is_local=False,
        connection_url=body.connection_url,
        tls_ca_cert=body.tls_ca_cert,
        tls_client_cert=body.tls_client_cert,
        tls_client_key=body.tls_client_key,
        status="connected" if ok else "error",
        last_error=None if ok else error,
        last_checked_at=datetime.now(timezone.utc),
    )
    session.add(host)
    session.commit()
    session.refresh(host)
    return host


@router.post("/hosts/{host_id}/test", response_model=Host)
def test_host(host_id: int, session: Session = Depends(get_session)) -> Host:
    host = session.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    if host.is_local:
        raise HTTPException(status_code=400, detail="The local host is always connected")

    reset_client_for_host(host.id)
    ok, error = test_connection(host.connection_url, host.tls_ca_cert, host.tls_client_cert, host.tls_client_key)
    host.status = "connected" if ok else "error"
    host.last_error = None if ok else error
    host.last_checked_at = datetime.now(timezone.utc)
    session.add(host)
    session.commit()
    session.refresh(host)
    return host


@router.delete("/hosts/{host_id}", status_code=204)
def delete_host(host_id: int, session: Session = Depends(get_session)) -> None:
    host = session.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    if host.is_local:
        raise HTTPException(status_code=400, detail="Cannot remove the local host")

    # Remove its containers too (they'd otherwise violate the host_id foreign
    # key); events/incidents referencing them by name/id are left untouched
    # so history survives the host being removed.
    containers = session.exec(select(Container).where(Container.host_id == host_id)).all()
    for container in containers:
        session.delete(container)

    reset_client_for_host(host_id)
    session.delete(host)
    session.commit()
