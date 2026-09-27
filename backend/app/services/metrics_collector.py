"""Metrics collection.

Samples CPU/memory/network usage for running containers via the Docker
stats API and persists them as `Metric` rows. Runs on the same cadence as
container discovery (`LABPULSE_POLL_INTERVAL`). A failure sampling one
container never aborts the whole collection pass.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from docker.errors import DockerException
from sqlmodel import Session

from app.models.metric import Metric, MetricType
from app.services.docker_collector import get_client, reset_client

logger = logging.getLogger("labpulse.metrics_collector")


def _cpu_percent(stats: dict[str, Any]) -> float | None:
    try:
        cpu_usage = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        precpu_usage = stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_usage = stats["cpu_stats"]["system_cpu_usage"]
        presystem_usage = stats["precpu_stats"]["system_cpu_usage"]

        cpu_delta = cpu_usage - precpu_usage
        system_delta = system_usage - presystem_usage
        online_cpus = stats["cpu_stats"].get("online_cpus") or len(
            stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or [1]
        )

        if system_delta <= 0 or cpu_delta < 0:
            return None
        return (cpu_delta / system_delta) * online_cpus * 100.0
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _memory_percent(stats: dict[str, Any]) -> float | None:
    try:
        memory_stats = stats["memory_stats"]
        usage = memory_stats["usage"]
        cache = (memory_stats.get("stats") or {}).get("cache", 0)
        limit = memory_stats["limit"]
        if not limit:
            return None
        return ((usage - cache) / limit) * 100.0
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _network_bytes(stats: dict[str, Any]) -> tuple[float, float]:
    networks = stats.get("networks") or {}
    rx = sum(iface.get("rx_bytes", 0) for iface in networks.values())
    tx = sum(iface.get("tx_bytes", 0) for iface in networks.values())
    return float(rx), float(tx)


def collect_metrics(session: Session) -> int:
    """Sample metrics for all running containers.

    Returns the number of metric rows written (0 if Docker is unavailable).
    """
    client = get_client()
    if client is None:
        return 0

    try:
        running = client.containers.list(filters={"status": "running"})
    except DockerException as exc:
        logger.warning("Failed to list running containers for metrics: %s", exc)
        reset_client()
        return 0

    now = datetime.now(timezone.utc)
    written = 0

    for container in running:
        try:
            stats = container.stats(stream=False)
        except DockerException as exc:
            logger.warning("Failed to read stats for %s: %s", container.id, exc)
            continue

        samples: list[tuple[MetricType, float | None]] = [
            (MetricType.CPU_PERCENT, _cpu_percent(stats)),
            (MetricType.MEMORY_PERCENT, _memory_percent(stats)),
        ]
        rx, tx = _network_bytes(stats)
        samples.append((MetricType.NETWORK_RX_BYTES, rx))
        samples.append((MetricType.NETWORK_TX_BYTES, tx))

        for metric_type, value in samples:
            if value is None:
                continue
            session.add(
                Metric(
                    timestamp=now,
                    container_id=container.id,
                    metric_type=metric_type,
                    value=value,
                )
            )
            written += 1

    session.commit()
    return written
