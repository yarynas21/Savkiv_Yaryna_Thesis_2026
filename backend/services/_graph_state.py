"""
Internal helpers for converting between LangGraph state and the plain dicts
the API layer exposes. Shared by ``interview_service``, ``production_service``
and ``metrics_service``.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage

from utils.logger import get_logger

logger = get_logger(__name__)


def initial_state(
    user_message: str,
    *,
    ui_role: Literal["client", "expert"] = "client",
    components_catalog_shown: bool = False,
) -> dict[str, Any]:
    """A fresh ``ProductionState`` seeded with one human message."""
    return {
        "messages": [HumanMessage(content=user_message)],
        "client_requirements": {},
        "product_components": [],
        "production_routes": [],
        "validation_status": "pending",
        "ambiguities": [],
        "human_feedback": None,
        "work_order": None,
        "cost_estimates": None,
        "llm_eval": {"rows": [], "session_call_count": 0},
        "current_agent": "",
        "iteration": 0,
        "requirements_complete": False,
        "conversation_ui_role": ui_role,
        "components_catalog_shown": components_catalog_shown,
    }


def append_message_input(user_message: str) -> dict[str, Any]:
    """Partial state to append one HumanMessage to an existing thread."""
    return {"messages": [HumanMessage(content=user_message)]}


def is_first_invocation(wf, config: dict) -> bool:
    """True if no checkpointed messages exist yet for ``config`` thread."""
    try:
        snapshot = wf.get_state(config)
        if not snapshot or not snapshot.values:
            return True
        return len(snapshot.values.get("messages", [])) == 0
    except Exception:
        return True


def serialize_messages(values: dict) -> list[dict]:
    """Convert LangGraph messages into the plain dicts the frontend consumes."""
    out: list[dict] = []
    current_agent_fallback = values.get("current_agent", "Agent")
    for msg in values.get("messages", []):
        if isinstance(msg, AIMessage):
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if has_tool_calls and not content.strip():
                continue
            out.append(
                {
                    "role": "agent",
                    "content": msg.content,
                    "agent_name": getattr(msg, "name", None) or current_agent_fallback,
                }
            )
        elif isinstance(msg, HumanMessage):
            out.append({"role": "user", "content": msg.content, "agent_name": ""})
    return out


def snapshot_values(wf, config: dict) -> tuple[dict, list[str]]:
    """Return ``(values, next_nodes)`` for this thread or empty defaults."""
    try:
        snapshot = wf.get_state(config)
        values: dict = snapshot.values if isinstance(snapshot.values, dict) else {}
        next_nodes: list = list(snapshot.next) if snapshot.next else []
        return values, next_nodes
    except Exception as exc:  # pragma: no cover — robustness
        logger.warning("Could not read graph snapshot: %s", exc)
        return {}, []


def safe_work_order(values: dict) -> dict | None:
    """Strip ``excel_bytes`` from the work_order before sending over HTTP."""
    raw = values.get("work_order")
    if not raw:
        return None
    return {k: v for k, v in raw.items() if k != "excel_bytes"}


def build_session_state_payload(wf, thread_id: str, config: dict) -> dict:
    """Shared payload-builder for ``SessionState``-shaped responses."""
    values, next_nodes = snapshot_values(wf, config)
    awaiting_human = "human_review" in next_nodes
    work_order_raw = values.get("work_order")
    excel_ready = bool(work_order_raw and work_order_raw.get("excel_bytes"))
    finished = excel_ready or bool(work_order_raw)

    return {
        "thread_id": thread_id,
        "messages": serialize_messages(values),
        "product_components": values.get("product_components", []),
        "production_routes": values.get("production_routes", []),
        "work_order": safe_work_order(values),
        "cost_estimates": values.get("cost_estimates"),
        "awaiting_human": awaiting_human,
        "ambiguities": values.get("ambiguities", []),
        "finished": finished,
        "current_agent": values.get("current_agent", ""),
        "excel_ready": excel_ready,
    }
