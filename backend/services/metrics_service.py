"""
LLM-eval metrics aggregation — reads from the LangGraph checkpointer.

Kept isolated from routers so that metric calculation can be reused from
admin and expert views alike.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from db.repositories import metrics as metrics_repo
from graph.registry import GraphName, get_graph
from services._graph_state import snapshot_values
from tools.llm_eval_metrics import (
    calculate_cost_usd,
    calculate_cost_from_rows,
    calculate_latency_metrics,
    gpt_4o_pricing,
    pricing_for_model,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# In-memory tracker so ``overview`` knows which thread_ids to scan. This is
# intentionally *not* persisted — it just prevents the expensive O(DB size)
# enumeration of every checkpointed thread.
_KNOWN_THREAD_IDS: set[tuple[str, str]] = set()


def register_thread(thread_id: str, graph: GraphName = "full") -> None:
    _KNOWN_THREAD_IDS.add((graph, thread_id))


def session_metrics(thread_id: str, *, graph: GraphName = "full") -> dict[str, Any]:
    wf = get_graph(graph)
    values, _ = snapshot_values(wf, {"configurable": {"thread_id": thread_id}})
    metrics = _metrics_from_values(values, thread_id)
    _persist_metrics_snapshot(thread_id, graph, metrics)
    return metrics


def overview() -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    per_session_cost: list[dict[str, float | str]] = []
    sessions_total = 0

    for graph_name, thread_id in sorted(_KNOWN_THREAD_IDS):
        wf = get_graph(graph_name)  # type: ignore[arg-type]
        try:
            values, _ = snapshot_values(wf, {"configurable": {"thread_id": thread_id}})
        except Exception:
            continue
        sessions_total += 1
        metrics = _metrics_from_values(values, thread_id)
        all_rows.extend(metrics["rows"])
        per_session_cost.append(
            {"thread_id": thread_id, "total_cost_usd": metrics["cost"]["total_cost_usd"]}
        )

    latency_values = [float(r.get("latency_ms", 0.0)) for r in all_rows]
    latency = calculate_latency_metrics(latency_values)
    by_model = _build_by_model(all_rows)
    total_cost_usd = sum(float(x["total_cost_usd"]) for x in by_model)
    cost = calculate_cost_from_rows(all_rows, gpt_4o_pricing())
    cost["total_cost_usd"] = round(total_cost_usd, 6)
    core = _build_core_metrics(all_rows, len(all_rows), cost["total_cost_usd"], latency_values)
    return {
        "sessions_total": sessions_total,
        "calls_total": len(all_rows),
        "estimated": any(bool(r.get("estimated", False)) for r in all_rows),
        "core": core,
        "latency": latency,
        "cost": cost,
        "by_model": by_model,
        "per_session_cost": per_session_cost,
    }


def _metrics_from_values(values: dict, thread_id: str) -> dict[str, Any]:
    llm_eval = values.get("llm_eval") or {}
    rows = llm_eval.get("rows", [])
    call_count = int(llm_eval.get("session_call_count", len(rows)))
    latency_values = [float(r.get("latency_ms", 0.0)) for r in rows]
    latency = calculate_latency_metrics(latency_values, scope="conversation")
    by_model = _build_by_model(rows)
    total_cost_usd = sum(float(x["total_cost_usd"]) for x in by_model)
    cost = calculate_cost_from_rows(rows, gpt_4o_pricing(), scope="conversation")
    cost["total_cost_usd"] = round(total_cost_usd, 6)
    core = _build_core_metrics(rows, call_count, cost["total_cost_usd"], latency_values)
    estimated = any(bool(r.get("estimated", False)) for r in rows)
    return {
        "thread_id": thread_id,
        "call_count": call_count,
        "estimated": estimated,
        "core": core,
        "latency": latency,
        "cost": cost,
        "by_model": by_model,
        "rows": rows,
    }


def _build_core_metrics(
    rows: list[dict[str, Any]],
    call_count: int,
    total_cost_usd: float,
    latency_values: list[float],
) -> dict[str, float]:
    agent_processing_total_ms = sum(float(r.get("agent_processing_ms", 0.0)) for r in rows)
    llm_latency_total_ms = sum(x for x in latency_values if x >= 0)
    return {
        "agent_processing_total_ms": round(agent_processing_total_ms, 2),
        "agent_processing_total_min": round(agent_processing_total_ms / 60_000, 4),
        "llm_latency_total_ms": round(llm_latency_total_ms, 2),
        "llm_latency_total_min": round(llm_latency_total_ms / 60_000, 4),
        "llm_total_cost_usd": round(float(total_cost_usd), 6),
        "llm_calls_total": float(call_count),
    }


def _build_by_model(rows: list[dict[str, Any]]) -> list[dict[str, float | str]]:
    grouped: dict[str, dict[str, float]] = defaultdict(
        lambda: {"calls_total": 0.0, "input_tokens_total": 0.0, "output_tokens_total": 0.0,
                 "cache_read_tokens_total": 0.0, "cache_creation_tokens_total": 0.0,
                 "latency_total_ms": 0.0}
    )
    for row in rows:
        model = str(row.get("model") or "unknown")
        bucket = grouped[model]
        bucket["calls_total"] += 1.0
        bucket["input_tokens_total"] += float(row.get("input_tokens", 0) or 0)
        bucket["output_tokens_total"] += float(row.get("output_tokens", 0) or 0)
        bucket["cache_read_tokens_total"] += float(row.get("cache_read_tokens", 0) or 0)
        bucket["cache_creation_tokens_total"] += float(row.get("cache_creation_tokens", 0) or 0)
        bucket["latency_total_ms"] += float(row.get("latency_ms", 0.0) or 0.0)

    out: list[dict[str, float | str]] = []
    for model in sorted(grouped.keys()):
        values = grouped[model]
        pricing = pricing_for_model(model)
        total_cost_usd = calculate_cost_usd(
            int(values["input_tokens_total"]),
            int(values["output_tokens_total"]),
            pricing,
            cache_read_tokens=int(values["cache_read_tokens_total"]),
            cache_creation_tokens=int(values["cache_creation_tokens_total"]),
        )
        out.append(
            {
                "model": model,
                "calls_total": round(values["calls_total"], 0),
                "input_tokens_total": round(values["input_tokens_total"], 0),
                "output_tokens_total": round(values["output_tokens_total"], 0),
                "cache_read_tokens_total": round(values["cache_read_tokens_total"], 0),
                "cache_creation_tokens_total": round(values["cache_creation_tokens_total"], 0),
                "latency_total_ms": round(values["latency_total_ms"], 2),
                "total_cost_usd": total_cost_usd,
            }
        )
    return out


def persist_session_snapshot(thread_id: str, *, graph: GraphName = "full") -> None:
    """Persist latest session metrics to DB snapshot tables for dashboards."""
    wf = get_graph(graph)
    values, _ = snapshot_values(wf, {"configurable": {"thread_id": thread_id}})
    metrics = _metrics_from_values(values, thread_id)
    _persist_metrics_snapshot(thread_id, graph, metrics)


def _persist_metrics_snapshot(thread_id: str, graph: GraphName, metrics: dict[str, Any]) -> None:
    try:
        core = metrics.get("core") or {}
        metrics_repo.upsert_session_metrics(
            thread_id=thread_id,
            graph_name=graph,
            llm_calls_total=int(core.get("llm_calls_total", metrics.get("call_count", 0))),
            llm_latency_total_ms=float(core.get("llm_latency_total_ms", 0.0)),
            llm_total_cost_usd=float(core.get("llm_total_cost_usd", 0.0)),
            agent_processing_total_ms=float(core.get("agent_processing_total_ms", 0.0)),
            model_active=_active_model(metrics.get("rows", [])),
        )
        metrics_repo.replace_session_metrics_by_model(
            thread_id=thread_id,
            rows=list(metrics.get("by_model") or []),
        )
    except Exception as exc:
        logger.warning("Could not persist metrics snapshot for %s: %s", thread_id, exc)


def _active_model(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    for row in reversed(rows):
        model = str(row.get("model") or "").strip()
        if model:
            return model
    return None
