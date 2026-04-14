"""
Database connection — SQLAlchemy Core engine.

Reads DATABASE_URL from the environment (set via .env or Docker Compose).
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from utils.logger import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Add it to .env or pass via Docker Compose."
            )
        logger.info(f"Creating SQLAlchemy engine: {url.split('@')[-1]}")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


@contextmanager
def get_connection() -> Connection:
    """Yield an open SQLAlchemy connection, committing/rolling back on exit."""
    engine = get_engine()
    with engine.connect() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
