from datetime import datetime, timezone

from sqlmodel import Session

from app.models.event import Category, Event, Severity


def _seed_events(client):
    import app.core.database as database

    now = datetime.now(timezone.utc)
    events = [
        Event(
            timestamp=now,
            severity=Severity.ERROR,
            category=Category.DOCKER,
            source_type="container",
            source_id="abc123",
            source_name="pihole",
            title="pihole became unhealthy",
            description="Docker healthcheck failed",
        ),
        Event(
            timestamp=now,
            severity=Severity.INFO,
            category=Category.DOCKER,
            source_type="container",
            source_id="def456",
            source_name="jellyfin",
            title="jellyfin started",
            description="Container started",
        ),
    ]

    with Session(database.get_engine()) as session:
        for event in events:
            session.add(event)
        session.commit()


def test_list_events(client):
    _seed_events(client)

    response = client.get("/api/events")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2


def test_filter_events_by_severity(client):
    _seed_events(client)

    response = client.get("/api/events", params={"severity": "ERROR"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["source_name"] == "pihole"


def test_filter_events_by_source_id(client):
    _seed_events(client)

    response = client.get("/api/events", params={"source_id": "def456"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "jellyfin started"


def test_search_events_by_title(client):
    _seed_events(client)

    response = client.get("/api/events", params={"q": "unhealthy"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1


def test_get_event_by_id(client):
    _seed_events(client)

    listed = client.get("/api/events").json()
    event_id = listed[0]["id"]

    response = client.get(f"/api/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id


def test_get_event_not_found(client):
    response = client.get("/api/events/999999")
    assert response.status_code == 404
