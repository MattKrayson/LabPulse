"""Metric model.

Time-series samples (CPU/memory/network) collected per container. Rows
are append-only and pruned by the retention service, never updated in
place, so the table can be indexed purely for time-range scans.
"""
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MetricType(str, Enum):
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    NETWORK_RX_BYTES = "network_rx_bytes"
    NETWORK_TX_BYTES = "network_tx_bytes"


class Metric(SQLModel, table=True):
    __tablename__ = "metrics"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(index=True)
    container_id: str = Field(index=True)
    metric_type: MetricType = Field(index=True)
    value: float
    created_at: datetime = Field(default_factory=_utcnow)
