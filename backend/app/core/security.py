"""Session-token creation/verification and credential checking for the single
shared admin account. Tokens are signed JWTs stored in an HttpOnly cookie
(see app/api/routes/auth.py) - there is no per-user database, per spec (MVP
is a private single-admin homelab tool).
"""
import hmac
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

COOKIE_NAME = "labpulse_session"
_ALGORITHM = "HS256"


def verify_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


def create_access_token(username: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_expire_minutes)
    payload = {"sub": username, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the username encoded in a valid token, or None if invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
