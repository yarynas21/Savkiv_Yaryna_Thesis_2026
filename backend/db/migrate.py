"""
Lightweight migration runner.

Executes every ``backend/db/migrations/*.sql`` file in alphabetical order,
tracking applied files in a ``schema_migrations`` table so re-runs are safe.

Invoked from ``entrypoint.sh`` before uvicorn starts, so the DB is always up
to date with the shipped schema even when the Postgres volume persists across
container restarts (`docker-entrypoint-initdb.d` only runs on a fresh volume).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import text

# Allow running as a module (python -m db.migrate) or standalone script from
# inside the backend/ folder. When invoked directly we need backend/ on sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.connection import get_connection, get_engine  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _ensure_migrations_table() -> None:
    with get_connection() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename    TEXT         PRIMARY KEY,
                    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
                """
            )
        )


def _applied_set() -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(text("SELECT filename FROM schema_migrations")).all()
    return {r[0] for r in rows}


def _pending_files(applied: set[str]) -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql")
        if p.name not in applied
    )


def _apply_file(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    # exec_driver_sql lets us send multi-statement SQL with DO $$ blocks without
    # SQLAlchemy trying to parse parameters from $ placeholders.
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
        conn.exec_driver_sql(
            "INSERT INTO schema_migrations (filename) VALUES (%s) "
            "ON CONFLICT (filename) DO NOTHING",
            (path.name,),
        )
    logger.info("Applied migration: %s", path.name)


def run_migrations() -> None:
    """Apply every pending ``*.sql`` file under ``backend/db/migrations/``."""
    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL not set — skipping migrations")
        return
    _ensure_migrations_table()
    applied = _applied_set()
    pending = _pending_files(applied)
    if not pending:
        logger.info("No pending migrations (%d already applied)", len(applied))
        return
    logger.info("Running %d pending migration(s)...", len(pending))
    for p in pending:
        _apply_file(p)
    logger.info("All migrations applied")


if __name__ == "__main__":
    run_migrations()
