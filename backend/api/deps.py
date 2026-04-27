"""Shared FastAPI dependencies for the API layer."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from auth.dependencies import get_current_user, require_role  # re-exports
from db.repositories.users import get_by_username


def get_current_user_db(payload: dict = Depends(get_current_user)) -> dict:
    """Return the DB record for the authenticated user (raises 401 if gone)."""
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = get_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )
    return user


__all__ = [
    "get_current_user",
    "get_current_user_db",
    "require_role",
]
