"""
Graph registry — singletons for the three compiled LangGraph variants.

On first access we:
1. Build a shared checkpointer. ``PostgresSaver`` is preferred so graph state
   survives container restarts; if the ``langgraph-checkpoint-postgres``
   package is missing or DB setup fails we fall back to ``MemorySaver`` and
   log a warning (dev / offline mode).
2. Compile all three graphs against that checkpointer.
3. Cache them so subsequent calls are O(1).

Callers use ``get_graph("interview" | "production" | "full")``.
"""

from __future__ import annotations

import os
from threading import RLock
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver

from graph.workflow import (
    build_full_graph,
    build_interview_graph,
    build_production_graph,
)
from utils.logger import get_logger

logger = get_logger(__name__)

GraphName = Literal["interview", "production", "full"]

_lock = RLock()
_checkpointer: Any | None = None
_graphs: dict[str, Any] = {}


def _build_postgres_checkpointer() -> Any | None:
    """Best-effort PostgresSaver construction. Returns None if unavailable."""
    if os.environ.get("USE_POSTGRES_CHECKPOINTER", "1").lower() in {"0", "false", "no"}:
        logger.warning("USE_POSTGRES_CHECKPOINTER=0 → falling back to MemorySaver")
        return None
    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.info("DATABASE_URL not set — skipping PostgresSaver")
        return None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except Exception as exc:  # pragma: no cover — package missing
        logger.warning("langgraph-checkpoint-postgres not available: %s", exc)
        return None

    conn_str = url.replace("postgresql+psycopg2://", "postgresql://")
    host = conn_str.split("@")[-1]
    logger.info("PostgresSaver: opening connection to %s", host)
    try:
        cm = PostgresSaver.from_conn_string(conn_str)
        saver = cm.__enter__()
        logger.info("PostgresSaver: running setup() — creating checkpoint tables…")
        saver.setup()
        logger.info("PostgresSaver: ready on %s", host)
        _postgres_cm_cache.append(cm)
        return saver
    except Exception as exc:
        logger.warning(
            "PostgresSaver setup failed, falling back to MemorySaver: %s", exc,
            exc_info=True,
        )
        return None


_postgres_cm_cache: list[Any] = []


def get_checkpointer() -> Any:
    """Build (once) and return the shared checkpointer."""
    global _checkpointer
    with _lock:
        if _checkpointer is None:
            _checkpointer = _build_postgres_checkpointer() or MemorySaver()
            if isinstance(_checkpointer, MemorySaver):
                logger.warning(
                    "Using MemorySaver — graph state will NOT persist across restarts"
                )
    return _checkpointer


_BUILDERS = {
    "interview": build_interview_graph,
    "production": build_production_graph,
    "full": build_full_graph,
}


def get_graph(name: GraphName) -> Any:
    """Return the compiled graph for ``name``, compiling on first access."""
    if name not in _BUILDERS:
        raise KeyError(f"Unknown graph name: {name!r}")
    with _lock:
        if name not in _graphs:
            logger.info("Compiling %s_graph (first access)…", name)
            ckpt = get_checkpointer()
            _graphs[name] = _BUILDERS[name](ckpt)
            logger.info("%s_graph compiled", name)
    return _graphs[name]


def preload_all() -> None:
    """Eagerly compile all three graphs (call from lifespan startup)."""
    for name in _BUILDERS:
        get_graph(name)  # type: ignore[arg-type]
