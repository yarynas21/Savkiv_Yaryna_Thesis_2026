"""
Persistence helpers for dashboard-friendly session metrics snapshots.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, select, text, update

from db.connection import get_connection
from db.models import session_metrics, session_metrics_by_model


def upsert_session_metrics(
    *,
    thread_id: str,
    graph_name: str,
    llm_calls_total: int,
    llm_latency_total_ms: float,
    llm_total_cost_usd: float,
    agent_processing_total_ms: float,
    model_active: str | None,
) -> None:
    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "graph_name": graph_name,
        "llm_calls_total": llm_calls_total,
        "llm_latency_total_ms": llm_latency_total_ms,
        "llm_total_cost_usd": llm_total_cost_usd,
        "agent_processing_total_ms": agent_processing_total_ms,
        "model_active": model_active,
        "updated_at": text("NOW()"),
    }
    with get_connection() as conn:
        exists = conn.execute(
            select(session_metrics.c.thread_id).where(session_metrics.c.thread_id == thread_id)
        ).fetchone()
        if exists:
            conn.execute(
                update(session_metrics)
                .where(session_metrics.c.thread_id == thread_id)
                .values(**payload)
            )
        else:
            conn.execute(
                insert(session_metrics).values(**payload, created_at=text("NOW()"))
            )


def replace_session_metrics_by_model(
    *,
    thread_id: str,
    rows: list[dict[str, Any]],
) -> None:
    with get_connection() as conn:
        conn.execute(
            delete(session_metrics_by_model).where(session_metrics_by_model.c.thread_id == thread_id)
        )
        for row in rows:
            conn.execute(
                insert(session_metrics_by_model).values(
                    thread_id=thread_id,
                    model=str(row.get("model", "unknown")),
                    calls_total=int(row.get("calls_total", 0)),
                    input_tokens_total=int(row.get("input_tokens_total", 0)),
                    output_tokens_total=int(row.get("output_tokens_total", 0)),
                    cache_read_tokens_total=int(row.get("cache_read_tokens_total", 0)),
                    cache_creation_tokens_total=int(row.get("cache_creation_tokens_total", 0)),
                    latency_total_ms=float(row.get("latency_total_ms", 0.0)),
                    total_cost_usd=float(row.get("total_cost_usd", 0.0)),
                    updated_at=text("NOW()"),
                )
            )
