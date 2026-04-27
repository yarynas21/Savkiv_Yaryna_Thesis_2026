"""
Persisted client interview sessions.

Populated by the client-facing flow (``interview_graph``) and consumed by the
expert-facing flow (``production_graph``) when a technologist picks one up.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    LargeBinary,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

from db.models import metadata

interview_sessions = Table(
    "interview_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("thread_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "client_user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("title", Text),
    Column("status", String(20), nullable=False),
    Column("messages", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("collected_data", JSONB),
    Column(
        "expert_user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    ),
    Column("production_thread_id", UUID(as_uuid=True)),
    Column("work_order", JSONB),
    Column("cost_estimates", JSONB),
    Column("excel_bytes", LargeBinary),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("completed_at", TIMESTAMP(timezone=True)),
    Column("processed_at", TIMESTAMP(timezone=True)),
    CheckConstraint(
        "status IN ('in_progress', 'completed', 'processed')",
        name="interview_sessions_status_check",
    ),
)
