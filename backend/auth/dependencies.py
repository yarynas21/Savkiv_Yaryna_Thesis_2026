"""FastAPI dependencies for authentication."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.utils import decode_access_token
from utils.logger import get_logger

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Validate the Bearer JWT and return the decoded payload."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        username: str | None = payload.get("sub")
        if not username:
            raise credentials_exception
        return payload
    except Exception as exc:
        logger.warning(f"JWT validation failed: {exc}")
        raise credentials_exception


def require_role(*roles: str):
    """Dependency factory — raises 403 if the user's role is not in the allowed set."""
    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(roles)}",
            )
        return current_user
    return _check
