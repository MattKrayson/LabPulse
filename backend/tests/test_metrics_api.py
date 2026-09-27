from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.models.metric import Metric, MetricType


def _seed_metrics(client):
    import app.core.database as database

    now = datetime.now(timezone.utc)
    with Session(database.get_engine()) as session:
        session.add(Metric(timestamp=now - timedelta(minutes=2), container_id="abc123", metric_type=MetricType.CPU_PERCENT, value=10.0))
        session.add(Metric(timestamp=now - timedelta(minutes=1), container_id="abc123", metric_type=MetricType.CPU_PERCENT, value=20.0))
        session.add(Metric(timestamp=now, container_id="abc123", metric_type=MetricType.MEMORY_PERCENT, value=30.0))
        session.add(Metric(timestamp=now, container_id="other456", metric_type=MetricType.CPU_PERCENT, value=99.0))
        session.commit()


def test_list_metrics_requires_container_id(client):
    response = client.get("/api/metrics")
    assert response.status_code == 422


def test_list_metrics_filters_by_container_and_type(client):
    _seed_metrics(client)

    response = client.get("/api/metrics", params={"container_id": "abc123", "metric_type": "cpu_percent"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # Returned chronologically (oldest first) for direct charting.
    assert body[0]["value"] == 10.0
    assert body[1]["value"] == 20.0


def test_list_metrics_only_returns_requested_container(client):
    _seed_metrics(client)

    response = client.get("/api/metrics", params={"container_id": "other456"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["container_id"] == "other456"
