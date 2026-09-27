"""Login/logout endpoints for the single shared admin account."""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.api.deps import require_auth
from app.core.config import get_settings
from app.core.security import COOKIE_NAME, create_access_token, verify_credentials

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory per-IP login rate limiting. Resets on restart, which is fine for a
# single-process homelab deployment; a distributed store would be overkill here.
_MAX_ATTEMPTS = 5
_BASE_LOCKOUT_SECONDS = 30
_MAX_LOCKOUT_SECONDS = 15 * 60
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_locked_until: dict[str, float] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> None:
    locked = _locked_until.get(ip)
    if locked and time.monotonic() < locked:
        retry_after = int(locked - time.monotonic()) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {retry_after}s.",
        )


def _record_failure(ip: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _failed_attempts[ip] if t > now - _MAX_LOCKOUT_SECONDS]
    attempts.append(now)
    _failed_attempts[ip] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        backoff = min(_BASE_LOCKOUT_SECONDS * 2 ** (len(attempts) - _MAX_ATTEMPTS), _MAX_LOCKOUT_SECONDS)
        _locked_until[ip] = now + backoff


def _record_success(ip: str) -> None:
    _failed_attempts.pop(ip, None)
    _locked_until.pop(ip, None)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    ip = _client_ip(request)
    _check_rate_limit(ip)

    if not verify_credentials(body.username, body.password):
        _record_failure(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    _record_success(ip)
    settings = get_settings()
    token = create_access_token(body.username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_expire_minutes * 60,
        path="/",
    )
    return {"username": body.username}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(username: str = Depends(require_auth)) -> dict:
    return {"username": username}
