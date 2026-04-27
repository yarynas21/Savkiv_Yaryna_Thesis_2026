"""
Database repositories — one module per domain.

* ``kb``         — read helpers for the knowledge base used by agents/tools.
* ``admin``      — CRUD helpers for the admin UI (game_components, cost_rates, papers).
* ``interviews`` — persistence helpers for client interview sessions.
* ``users``      — user administration (list / patch role / deactivate).
"""

from __future__ import annotations

from db.repositories import admin, interviews, kb, users  # noqa: F401

__all__ = ["kb", "admin", "interviews", "users"]
