from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from app.models.event import Category, Event, Severity
from app.models.incident import Incident, IncidentEvent, IncidentStatus
from app.services.incidents import correlate_incidents


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _event(session, *, minutes_ago, severity=Severity.INFO, source_id="c1", source_name="pihole", title="event"):
    session.add(
        Event(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            severity=severity,
            category=Category.DOCKER,
            source_type="container",
            source_id=source_id,
            source_name=source_name,
            title=title,
        )
    )


def test_close_events_grouped_into_one_incident():
    with _session() as session:
        _event(session, minutes_ago=10, title="Pi-hole healthcheck failed")
        _event(session, minutes_ago=9, title="Pi-hole restarted")
        _event(session, minutes_ago=8, title="Pi-hole healthy")
        session.commit()

        attached = correlate_incidents(session)
        assert attached == 3

        incidents = session.exec(select(Incident)).all()
        assert len(incidents) == 1
        assert incidents[0].event_count == 3
        assert incidents[0].source_name == "pihole"


def test_far_apart_events_create_separate_incidents():
    with _session() as session:
        _event(session, minutes_ago=120, title="first incident event")
        _event(session, minutes_ago=10, title="second incident event")
        session.commit()

        correlate_incidents(session)

        incidents = session.exec(select(Incident)).all()
        assert len(incidents) == 2


def test_different_sources_create_separate_incidents():
    with _session() as session:
        _event(session, minutes_ago=5, source_id="c1", source_name="pihole")
        _event(session, minutes_ago=5, source_id="c2", source_name="jellyfin")
        session.commit()

        correlate_incidents(session)

        incidents = session.exec(select(Incident)).all()
        assert len(incidents) == 2
        assert {i.source_id for i in incidents} == {"c1", "c2"}


def test_severity_escalates_to_highest_event_severity():
    with _session() as session:
        _event(session, minutes_ago=10, severity=Severity.INFO)
        _event(session, minutes_ago=9, severity=Severity.CRITICAL)
        session.commit()

        correlate_incidents(session)

        incidents = session.exec(select(Incident)).all()
        assert incidents[0].severity == Severity.CRITICAL


def test_new_event_extends_existing_open_incident():
    with _session() as session:
        _event(session, minutes_ago=3)
        session.commit()
        correlate_incidents(session)

        _event(session, minutes_ago=1)
        session.commit()
        attached = correlate_incidents(session)

        assert attached == 1
        incidents = session.exec(select(Incident)).all()
        assert len(incidents) == 1
        assert incidents[0].event_count == 2


def test_stale_open_incident_marked_resolved():
    with _session() as session:
        _event(session, minutes_ago=120)
        session.commit()

        correlate_incidents(session)

        incidents = session.exec(select(Incident)).all()
        assert incidents[0].status == IncidentStatus.RESOLVED


def test_no_events_produces_no_incidents():
    with _session() as session:
        attached = correlate_incidents(session)
        assert attached == 0
        assert session.exec(select(Incident)).all() == []


def test_events_are_linked_via_incident_events_table():
    with _session() as session:
        _event(session, minutes_ago=1)
        session.commit()

        correlate_incidents(session)

        links = session.exec(select(IncidentEvent)).all()
        assert len(links) == 1
