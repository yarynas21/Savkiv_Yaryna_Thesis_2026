"""
Persisted dashboard metrics tables.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric, String, Table

from db.models import metadata

session_metrics = Table(
    "session_metrics",
    metadata,
    Column("thread_id", String(64), primary_key=True),
    Column("graph_name", String(32), nullable=False),
    Column("llm_calls_total", Integer, nullable=False),
    Column("llm_latency_total_ms", Numeric(18, 2), nullable=False),
    Column("llm_total_cost_usd", Numeric(18, 6), nullable=False),
    Column("agent_processing_total_ms", Numeric(18, 2), nullable=False),
    Column("model_active", String(128)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

session_metrics_by_model = Table(
    "session_metrics_by_model",
    metadata,
    Column("thread_id", String(64), ForeignKey("session_metrics.thread_id", ondelete="CASCADE"), primary_key=True),
    Column("model", String(128), primary_key=True),
    Column("calls_total", Integer, nullable=False),
    Column("input_tokens_total", BigInteger, nullable=False),
    Column("output_tokens_total", BigInteger, nullable=False),
    Column("cache_read_tokens_total", BigInteger, nullable=False, server_default="0"),
    Column("cache_creation_tokens_total", BigInteger, nullable=False, server_default="0"),
    Column("latency_total_ms", Numeric(18, 2), nullable=False),
    Column("total_cost_usd", Numeric(18, 6), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
