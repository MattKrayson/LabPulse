"""Shared FastAPI dependencies."""
from fastapi import HTTPException, Request, status

from app.core.security import COOKIE_NAME, decode_access_token


def require_auth(request: Request) -> str:
    """Dependency that enforces a valid session cookie, returning the username."""
    token = request.cookies.get(COOKIE_NAME)
    username = decode_access_token(token) if token else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return username
