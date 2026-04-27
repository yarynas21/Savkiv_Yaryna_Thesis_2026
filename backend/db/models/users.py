"""
Users table (authentication + role-based access control).
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from db.models import metadata

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("email", String(255), nullable=False, unique=True),
    Column("username", String(100), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column(
        "role",
        String(20),
        nullable=False,
        server_default=text("'client'"),
    ),
    Column("is_active", Boolean, nullable=False, server_default=text("TRUE")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("role IN ('admin', 'client', 'expert')", name="users_role_check"),
)
