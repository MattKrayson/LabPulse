"""First-run database setup wizard endpoints.

Lets the logged-in admin choose an internal (SQLite) or custom (e.g.
PostgreSQL) database, test the connection, then apply it: applying tests the
connection again, runs Alembic migrations against it, and persists the
choice - so nothing is collected/stored before a working database has been
confirmed. Applying successfully then restarts the whole container (process
exit + the `restart: unless-stopped` Compose policy) rather than hot-swapping
the engine in-process, so every background task/collector starts clean
against the new database. Requires auth since only the admin should be able
to (re)point LabPulse at a different database.
"""
import os
import threading
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_auth
from app.core import database
from app.core.config import get_settings

router = APIRouter(prefix="/setup", tags=["setup"])


class DatabaseConfigRequest(BaseModel):
    mode: str  # "internal" or "custom"
    database_url: str | None = None  # required when mode == "custom"


def _resolve_url(body: DatabaseConfigRequest) -> str:
    if body.mode == "internal":
        return get_settings().database_url
    if body.mode == "custom":
        if not body.database_url:
            raise HTTPException(status_code=400, detail="database_url is required for custom mode")
        return body.database_url
    raise HTTPException(status_code=400, detail="mode must be 'internal' or 'custom'")


@router.get("/status")
def get_status(username: str = Depends(require_auth)) -> dict:
    return {
        "configured": database.is_configured(),
        "database_url_masked": database.get_current_url_masked(),
    }


@router.post("/test")
def test(body: DatabaseConfigRequest, username: str = Depends(require_auth)) -> dict:
    url = _resolve_url(body)
    try:
        database.test_connection(url)
    except Exception as exc:  # noqa: BLE001 - surface the driver's error message
        raise HTTPException(status_code=400, detail=f"Could not connect: {exc}") from None
    return {"ok": True}


def _restart_container() -> None:
    """Give the HTTP response time to reach the client, then exit so Docker's
    restart policy relaunches the container with a fresh process/engine."""

    def _exit_after_delay() -> None:
        time.sleep(1.5)
        os._exit(0)

    threading.Thread(target=_exit_after_delay, daemon=True).start()


@router.post("/configure")
def configure(body: DatabaseConfigRequest, background_tasks: BackgroundTasks, username: str = Depends(require_auth)) -> dict:
    url = _resolve_url(body)
    try:
        database.configure_database(url)
    except Exception as exc:  # noqa: BLE001 - surface the driver's/migration error message
        raise HTTPException(status_code=400, detail=f"Could not set up database: {exc}") from None

    background_tasks.add_task(_restart_container)
    return {"ok": True, "restarting": True}
