"""
User administration helpers (for the admin UI).

Registration / login remain in ``auth.routes`` — this module only supports
admin-side listing, role/flag updates, password resets, and deletion.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import delete, insert, select, update

from auth.utils import hash_password
from db.connection import get_connection
from db.models import users

ALLOWED_ROLES = ("admin", "client", "expert")


def list_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            select(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.role,
                users.c.is_active,
                users.c.created_at,
                users.c.updated_at,
            ).order_by(users.c.created_at.desc())
        ).mappings().all()
    return [dict(r) for r in rows]


def get_by_id(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            select(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.role,
                users.c.is_active,
            ).where(users.c.id == uuid.UUID(user_id))
        ).mappings().fetchone()
    return dict(row) if row else None


def get_by_username(username: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            select(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.role,
                users.c.is_active,
            ).where(users.c.username == username)
        ).mappings().fetchone()
    return dict(row) if row else None


def create_user(
    *,
    email: str,
    username: str,
    password: str,
    role: str = "client",
    is_active: bool = True,
) -> dict:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}")
    with get_connection() as conn:
        row = conn.execute(
            insert(users)
            .values(
                email=email,
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
            )
            .returning(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.role,
                users.c.is_active,
            )
        ).mappings().one()
    return dict(row)


def update_user(
    user_id: str,
    *,
    role: str | None = None,
    is_active: bool | None = None,
    password: str | None = None,
    email: str | None = None,
) -> dict:
    values: dict[str, Any] = {}
    if role is not None:
        if role not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role: {role}")
        values["role"] = role
    if is_active is not None:
        values["is_active"] = is_active
    if password:
        values["password_hash"] = hash_password(password)
    if email is not None:
        values["email"] = email

    if not values:
        existing = get_by_id(user_id)
        if existing is None:
            raise LookupError("User not found")
        return existing

    with get_connection() as conn:
        row = conn.execute(
            update(users)
            .where(users.c.id == uuid.UUID(user_id))
            .values(**values)
            .returning(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.role,
                users.c.is_active,
            )
        ).mappings().fetchone()
    if row is None:
        raise LookupError("User not found")
    return dict(row)


def delete_user(user_id: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(delete(users).where(users.c.id == uuid.UUID(user_id)))
    return result.rowcount > 0
