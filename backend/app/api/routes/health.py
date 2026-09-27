"""Health check endpoint.

Used by Docker healthchecks and the frontend to confirm the API is up (and,
once configured, that the database is reachable).
"""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text
from sqlmodel import Session

from app.core import database
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()

    if not database.is_configured():
        return {
            "status": "setup_required",
            "app": settings.app_name,
            "version": settings.version,
            "database": "not_configured",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    db_ok = True
    try:
        with Session(database.get_engine()) as session:
            session.exec(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "database": "ok" if db_ok else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
