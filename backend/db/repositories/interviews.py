"""
Persistence helpers for ``interview_sessions``.

Used by:
* ``services.interview_service``  — client-side CRUD for their own interviews.
* ``services.production_service`` — expert-side inbox, launch, result storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, select, update

from db.connection import get_connection
from db.models import interview_sessions
from utils.logger import get_logger

logger = get_logger(__name__)



def create_interview(
    *,
    client_user_id: str,
    thread_id: str,
    title: str | None = None,
) -> dict:
    """Insert a fresh ``in_progress`` row and return the whole record."""
    with get_connection() as conn:
        row = conn.execute(
            interview_sessions.insert()
            .values(
                thread_id=uuid.UUID(thread_id),
                client_user_id=uuid.UUID(client_user_id),
                title=title,
                status="in_progress",
            )
            .returning(*interview_sessions.c),
        ).mappings().one()
    logger.info("Interview created: id=%s client=%s", row["id"], client_user_id)
    return dict(row)



def get_interview(interview_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            interview_sessions.select().where(interview_sessions.c.id == uuid.UUID(interview_id))
        ).mappings().fetchone()
    return dict(row) if row else None


def get_by_thread_id(thread_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            interview_sessions.select().where(
                interview_sessions.c.thread_id == uuid.UUID(thread_id)
            )
        ).mappings().fetchone()
    return dict(row) if row else None


def list_by_client(client_user_id: str) -> list[dict]:
    """All interviews owned by a particular client user, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            interview_sessions.select()
            .where(interview_sessions.c.client_user_id == uuid.UUID(client_user_id))
            .order_by(interview_sessions.c.created_at.desc())
        ).mappings().all()
    return [dict(r) for r in rows]


def list_inbox(statuses: tuple[str, ...] = ("completed", "processed")) -> list[dict]:
    """Experts' inbox — completed / in-progress-production interviews."""
    with get_connection() as conn:
        rows = conn.execute(
            interview_sessions.select()
            .where(interview_sessions.c.status.in_(statuses))
            .order_by(interview_sessions.c.completed_at.desc().nullslast(),
                      interview_sessions.c.created_at.desc())
        ).mappings().all()
    return [dict(r) for r in rows]



def mark_completed(
    interview_id: str,
    *,
    messages: list[dict],
    collected_data: dict[str, Any] | None,
    title: str | None = None,
) -> dict:
    """Freeze the conversation state and mark status=completed."""
    now = datetime.now(timezone.utc)
    values: dict[str, Any] = {
        "status": "completed",
        "messages": messages,
        "collected_data": collected_data,
        "completed_at": now,
    }
    if title:
        values["title"] = title
    with get_connection() as conn:
        row = conn.execute(
            update(interview_sessions)
            .where(interview_sessions.c.id == uuid.UUID(interview_id))
            .values(**values)
            .returning(*interview_sessions.c)
        ).mappings().one()
    return dict(row)


def save_messages(interview_id: str, messages: list[dict]) -> None:
    """Persist the latest message history (used while status=in_progress)."""
    with get_connection() as conn:
        conn.execute(
            update(interview_sessions)
            .where(interview_sessions.c.id == uuid.UUID(interview_id))
            .values(messages=messages)
        )


def assign_expert(
    interview_id: str,
    *,
    expert_user_id: str,
    production_thread_id: str,
) -> dict:
    """Mark the interview as ``processed`` and attach expert + production thread."""
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        row = conn.execute(
            update(interview_sessions)
            .where(interview_sessions.c.id == uuid.UUID(interview_id))
            .values(
                expert_user_id=uuid.UUID(expert_user_id),
                production_thread_id=uuid.UUID(production_thread_id),
                status="processed",
                processed_at=now,
            )
            .returning(*interview_sessions.c)
        ).mappings().fetchone()
    if row is None:
        raise LookupError("Interview not found")
    return dict(row)


def save_production_output(
    interview_id: str,
    *,
    work_order: dict | None,
    cost_estimates: dict | None,
    excel_bytes: bytes | None,
) -> None:
    """Snapshot the production output (work order + cost + Excel) onto the row."""
    values: dict[str, Any] = {}
    if work_order is not None:
        values["work_order"] = work_order
    if cost_estimates is not None:
        values["cost_estimates"] = cost_estimates
    if excel_bytes is not None:
        values["excel_bytes"] = excel_bytes
    if not values:
        return
    with get_connection() as conn:
        conn.execute(
            update(interview_sessions)
            .where(interview_sessions.c.id == uuid.UUID(interview_id))
            .values(**values)
        )



def is_owner(interview_id: str, client_user_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            select(interview_sessions.c.id).where(
                and_(
                    interview_sessions.c.id == uuid.UUID(interview_id),
                    interview_sessions.c.client_user_id == uuid.UUID(client_user_id),
                )
            )
        ).fetchone()
    return row is not None
