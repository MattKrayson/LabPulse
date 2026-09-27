import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("LABPULSE_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("LABPULSE_CONFIG_PATH", str(tmp_path / "labpulse_config.json"))

    # Settings and engine are created at import time, so caches must be
    # cleared and modules reloaded after the env var is set.
    from app.core.config import get_settings

    get_settings.cache_clear()

    import importlib

    import app.core.database as database

    importlib.reload(database)

    import app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        settings = get_settings()
        login_response = test_client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert login_response.status_code == 200
        yield test_client
