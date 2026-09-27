"""Small JSON-backed store for the database connection chosen via the
first-run setup wizard (see app/api/routes/setup.py). Kept separate from
environment-variable config so the choice persists across container
restarts without requiring docker-compose/.env edits.
"""
import json
from pathlib import Path

from app.core.config import get_settings


def _config_path() -> Path:
    return Path(get_settings().config_path)


def load_database_url() -> str | None:
    path = _config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("database_url")


def save_database_url(database_url: str) -> None:
    path = _config_path()
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"database_url": database_url}))
