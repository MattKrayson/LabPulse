from app.models.event import Category, Severity
from app.services.docker_events import docker_event_to_labpulse


def make_raw_event(action, container_id="abc123def456", name="pihole", **attributes):
    return {
        "Type": "container",
        "Action": action,
        "time": 1_700_000_000,
        "Actor": {
            "ID": container_id,
            "Attributes": {"name": name, **attributes},
        },
    }


def test_start_event_is_info():
    event = docker_event_to_labpulse(make_raw_event("start"))
    assert event is not None
    assert event.severity == Severity.INFO
    assert event.category == Category.DOCKER
    assert event.source_id == "abc123def456"
    assert event.title == "pihole started"


def test_die_with_zero_exit_code_is_info():
    event = docker_event_to_labpulse(make_raw_event("die", exitCode="0"))
    assert event.severity == Severity.INFO


def test_die_with_nonzero_exit_code_is_error():
    event = docker_event_to_labpulse(make_raw_event("die", exitCode="1"))
    assert event.severity == Severity.ERROR
    assert "error" in event.title


def test_health_status_unhealthy_is_error():
    event = docker_event_to_labpulse(make_raw_event("health_status: unhealthy"))
    assert event.severity == Severity.ERROR
    assert "unhealthy" in event.title


def test_health_status_healthy_is_info():
    event = docker_event_to_labpulse(make_raw_event("health_status: healthy"))
    assert event.severity == Severity.INFO
    assert "healthy" in event.title


def test_irrelevant_type_is_ignored():
    raw = {"Type": "network", "Action": "connect"}
    assert docker_event_to_labpulse(raw) is None


def test_irrelevant_action_is_ignored():
    event = docker_event_to_labpulse(make_raw_event("exec_create"))
    assert event is None


def test_malformed_event_is_skipped():
    raw = {"Type": "container", "Action": "start", "Actor": None}
    assert docker_event_to_labpulse(raw) is None
