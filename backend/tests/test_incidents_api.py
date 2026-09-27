from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.models.event import Category, Event, Severity
from app.services.incidents import correlate_incidents


def _seed_event(session, *, minutes_ago, severity=Severity.WARNING, title="Pi-hole restarted"):
    session.add(
        Event(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            severity=severity,
            category=Category.DOCKER,
            source_type="container",
            source_id="c1",
            source_name="pihole",
            title=title,
        )
    )


def test_incidents_endpoint_lists_correlated_incident(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        _seed_event(session, minutes_ago=10, title="Pi-hole healthcheck failed")
        _seed_event(session, minutes_ago=9, title="Pi-hole restarted")
        session.commit()
        correlate_incidents(session)

    response = client.get("/api/incidents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["source_name"] == "pihole"
    assert body[0]["event_count"] == 2


def test_incidents_endpoint_filters_by_status(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        _seed_event(session, minutes_ago=120)
        session.commit()
        correlate_incidents(session)

    response = client.get("/api/incidents", params={"status": "RESOLVED"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/api/incidents", params={"status": "OPEN"})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_incident_detail_includes_events(client):
    import app.core.database as database

    with Session(database.get_engine()) as session:
        _seed_event(session, minutes_ago=10, title="Pi-hole healthcheck failed")
        _seed_event(session, minutes_ago=9, title="Pi-hole restarted")
        session.commit()
        correlate_incidents(session)

    incident_id = client.get("/api/incidents").json()[0]["id"]
    response = client.get(f"/api/incidents/{incident_id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 2
    assert body["events"][0]["title"] == "Pi-hole restarted"


def test_get_incident_not_found(client):
    response = client.get("/api/incidents/999")
    assert response.status_code == 404


def test_incidents_endpoint_with_no_data(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert response.json() == []
