from sqlmodel import Session, SQLModel, create_engine, select

from app.models.metric import Metric, MetricType
from app.services import metrics_collector


class FakeContainer:
    def __init__(self, container_id, stats):
        self.id = container_id
        self._stats = stats

    def stats(self, stream=False):
        return self._stats


class FakeContainersAPI:
    def __init__(self, containers):
        self._containers = containers

    def list(self, filters=None):
        return self._containers


class FakeClient:
    def __init__(self, containers):
        self.containers = FakeContainersAPI(containers)


def make_stats(cpu_delta=50, system_delta=200, online_cpus=2, mem_usage=512, mem_limit=1024, cache=12, rx=1000, tx=2000):
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": cpu_delta + 100},
            "system_cpu_usage": system_delta + 1000,
            "online_cpus": online_cpus,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
        },
        "memory_stats": {"usage": mem_usage, "limit": mem_limit, "stats": {"cache": cache}},
        "networks": {
            "eth0": {"rx_bytes": rx, "tx_bytes": tx},
        },
    }


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_collect_metrics_writes_all_metric_types(monkeypatch):
    fake = FakeClient([FakeContainer("abc123", make_stats())])
    monkeypatch.setattr(metrics_collector, "get_client", lambda: fake)

    with _session() as session:
        written = metrics_collector.collect_metrics(session)
        assert written == 4

        rows = session.exec(select(Metric).where(Metric.container_id == "abc123")).all()
        types = {row.metric_type for row in rows}
        assert types == {
            MetricType.CPU_PERCENT,
            MetricType.MEMORY_PERCENT,
            MetricType.NETWORK_RX_BYTES,
            MetricType.NETWORK_TX_BYTES,
        }


def test_collect_metrics_docker_unavailable(monkeypatch):
    monkeypatch.setattr(metrics_collector, "get_client", lambda: None)

    with _session() as session:
        assert metrics_collector.collect_metrics(session) == 0


def test_collect_metrics_skips_malformed_stats(monkeypatch):
    fake = FakeClient([FakeContainer("abc123", {"cpu_stats": {}, "precpu_stats": {}, "memory_stats": {}})])
    monkeypatch.setattr(metrics_collector, "get_client", lambda: fake)

    with _session() as session:
        written = metrics_collector.collect_metrics(session)
        # No cpu/memory could be computed, but network defaults to 0 for both directions.
        assert written == 2

        rows = session.exec(select(Metric).where(Metric.container_id == "abc123")).all()
        types = {row.metric_type for row in rows}
        assert types == {MetricType.NETWORK_RX_BYTES, MetricType.NETWORK_TX_BYTES}
