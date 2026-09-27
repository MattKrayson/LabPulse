"""LabPulse FastAPI application entrypoint."""
import asyncio
import contextlib
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.api.deps import require_auth
from app.api.routes import auth, changes, containers, events, health, hosts, incidents, metrics, setup, stats, webhooks
from app.core import database
from app.core.config import get_settings
from app.services.docker_collector import discover_containers
from app.services.docker_events import start_listener, stop_listener
from app.services.incidents import correlate_incidents
from app.services.metrics_collector import collect_metrics
from app.services.retention import cleanup_events, cleanup_incidents, cleanup_metrics, cleanup_snapshots
from app.services.snapshots import capture_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()
logger = logging.getLogger("labpulse.main")
access_logger = logging.getLogger("labpulse.access")

_poll_task: asyncio.Task | None = None
_metrics_task: asyncio.Task | None = None
_retention_task: asyncio.Task | None = None
_snapshot_task: asyncio.Task | None = None
_incident_task: asyncio.Task | None = None
_collection_started = False
_RETENTION_INTERVAL_SECONDS = 3600
_SNAPSHOT_INTERVAL_SECONDS = 3600
_INCIDENT_INTERVAL_SECONDS = 60


async def _poll_loop() -> None:
    """Background task that periodically discovers Docker containers.

    Runs forever until cancelled at shutdown. A failure in a single
    iteration is logged and never stops the loop or crashes the app.
    """
    while True:
        try:
            with Session(database.get_engine()) as session:
                await asyncio.to_thread(discover_containers, session)
        except Exception:  # noqa: BLE001 - never let a bad poll kill the loop
            logger.exception("Docker discovery poll failed")
        await asyncio.sleep(settings.poll_interval)


async def _metrics_loop() -> None:
    """Background task that periodically samples CPU/memory/network usage."""
    while True:
        try:
            with Session(database.get_engine()) as session:
                await asyncio.to_thread(collect_metrics, session)
        except Exception:  # noqa: BLE001 - never let a bad sample kill the loop
            logger.exception("Metrics collection failed")
        await asyncio.sleep(settings.poll_interval)


async def _retention_loop() -> None:
    """Background task that periodically prunes old events, metrics, and snapshots."""
    while True:
        await asyncio.sleep(_RETENTION_INTERVAL_SECONDS)
        try:
            with Session(database.get_engine()) as session:
                deleted_events = await asyncio.to_thread(cleanup_events, session)
                deleted_metrics = await asyncio.to_thread(cleanup_metrics, session)
                deleted_snapshots = await asyncio.to_thread(cleanup_snapshots, session)
                deleted_incidents = await asyncio.to_thread(cleanup_incidents, session)
                if deleted_events:
                    logger.info("Retention cleanup removed %d old event(s)", deleted_events)
                if deleted_metrics:
                    logger.info("Retention cleanup removed %d old metric(s)", deleted_metrics)
                if deleted_snapshots:
                    logger.info("Retention cleanup removed %d old snapshot(s)", deleted_snapshots)
                if deleted_incidents:
                    logger.info("Retention cleanup removed %d old incident(s)", deleted_incidents)
        except Exception:  # noqa: BLE001 - never let cleanup kill the loop
            logger.exception("Retention cleanup failed")


async def _snapshot_loop() -> None:
    """Background task that periodically captures container state snapshots.

    Captures immediately on startup (so a baseline exists right away) and
    then hourly, powering the "What Changed?" comparisons.
    """
    while True:
        try:
            with Session(database.get_engine()) as session:
                await asyncio.to_thread(capture_snapshot, session)
        except Exception:  # noqa: BLE001 - never let a bad snapshot kill the loop
            logger.exception("Snapshot capture failed")
        await asyncio.sleep(_SNAPSHOT_INTERVAL_SECONDS)


async def _incident_loop() -> None:
    """Background task that periodically correlates events into incidents."""
    while True:
        try:
            with Session(database.get_engine()) as session:
                await asyncio.to_thread(correlate_incidents, session)
        except Exception:  # noqa: BLE001 - never let a bad correlation kill the loop
            logger.exception("Incident correlation failed")
        await asyncio.sleep(_INCIDENT_INTERVAL_SECONDS)


def start_collection() -> None:
    """Start background discovery/metrics/retention/snapshot/incident tasks
    and the Docker event listener. Safe to call once the database has been
    configured (either at startup, or right after the setup wizard finishes).
    A no-op if collection has already been started."""
    global _poll_task, _metrics_task, _retention_task, _snapshot_task, _incident_task, _collection_started
    if _collection_started:
        return
    database.init_db()  # safety net if migrations weren't run yet
    _poll_task = asyncio.create_task(_poll_loop())
    _metrics_task = asyncio.create_task(_metrics_loop())
    _retention_task = asyncio.create_task(_retention_loop())
    _snapshot_task = asyncio.create_task(_snapshot_loop())
    _incident_task = asyncio.create_task(_incident_loop())
    start_listener(database.get_engine())
    _collection_started = True


async def _stop_collection() -> None:
    global _collection_started
    if not _collection_started:
        return
    stop_listener()
    for task in (_poll_task, _metrics_task, _retention_task, _snapshot_task, _incident_task):
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    _collection_started = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-configure from LABPULSE_DATABASE_URL or a previously saved setup
    # wizard choice, if either is present. Otherwise the frontend shows the
    # setup wizard and nothing is collected/stored until it completes.
    if database.try_autoconfigure():
        start_collection()

    yield

    await _stop_collection()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with a correlation ID, for tracing issues on a
    monitoring tool that should be at least as observable as what it watches."""
    request_id = uuid.uuid4().hex[:12]
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    access_logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

_auth_dep = [Depends(require_auth)]
app.include_router(setup.router, prefix="/api")
app.include_router(hosts.router, prefix="/api", dependencies=_auth_dep)
app.include_router(containers.router, prefix="/api", dependencies=_auth_dep)
app.include_router(events.router, prefix="/api", dependencies=_auth_dep)
app.include_router(metrics.router, prefix="/api", dependencies=_auth_dep)
app.include_router(stats.router, prefix="/api", dependencies=_auth_dep)
app.include_router(changes.router, prefix="/api", dependencies=_auth_dep)
app.include_router(incidents.router, prefix="/api", dependencies=_auth_dep)
app.include_router(webhooks.router, prefix="/api", dependencies=_auth_dep)



# Serve the built frontend (if present) so the whole app can run from a
# single container. In local development the frontend runs separately via
# `npm run dev` and this block is simply skipped.
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

