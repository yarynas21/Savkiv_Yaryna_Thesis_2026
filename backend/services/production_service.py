"""Expert-side flows for production graph management and review."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from db.repositories import interviews as interviews_repo
from graph.registry import GraphName, get_graph
from services import metrics_service
from services._graph_state import (
    append_message_input,
    build_session_state_payload,
    initial_state,
    is_first_invocation,
    snapshot_values,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def create_full_session() -> dict[str, Any]:
    """Return {"thread_id": ...} for a new full_graph thread."""
    thread_id = str(uuid.uuid4())
    logger.info("New full_graph session: %s", thread_id)
    return {"thread_id": thread_id}


def launch_from_interview(interview_id: str, expert_user_id: str) -> dict[str, Any]:
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise LookupError("Interview not found")
    if record["status"] == "in_progress":
        raise PermissionError("Interview is not yet completed by the client")

    production_thread_id = str(record.get("production_thread_id") or uuid.uuid4())
    wf = get_graph("production")
    config = {"configurable": {"thread_id": production_thread_id}}

    if is_first_invocation(wf, config):
        collected = record.get("collected_data") or {}
        messages_in = _messages_to_langchain(record.get("messages") or [])
        seed_state: dict[str, Any] = {
            "messages": messages_in,
            "client_requirements": collected.get("client_requirements", {}),
            "product_components": collected.get("product_components", []),
            "production_routes": [],
            "validation_status": "pending",
            "ambiguities": collected.get("ambiguities", []),
            "human_feedback": None,
            "work_order": None,
            "cost_estimates": None,
            "llm_eval": {"rows": [], "session_call_count": 0},
            "current_agent": "",
            "iteration": 0,
            "requirements_complete": True,
            "conversation_ui_role": "expert",
            "components_catalog_shown": True,
        }
        logger.info(
            "[%s] Launching production for interview %s (expert=%s)",
            production_thread_id, interview_id, expert_user_id,
        )
        wf.invoke(seed_state, config=config)

    interviews_repo.assign_expert(
        interview_id,
        expert_user_id=expert_user_id,
        production_thread_id=production_thread_id,
    )

    _snapshot_to_interview(wf, config, interview_id)

    payload = build_session_state_payload(wf, production_thread_id, config)
    metrics_service.register_thread(production_thread_id, graph="production")
    metrics_service.persist_session_snapshot(production_thread_id, graph="production")
    payload["interview_id"] = interview_id
    return payload


def send_message(
    thread_id: str,
    user_message: str,
    *,
    graph: GraphName = "full",
) -> dict[str, Any]:
    wf = get_graph(graph)
    config = {"configurable": {"thread_id": thread_id}}
    if is_first_invocation(wf, config):
        ui_role: Literal["client", "expert"] = "expert" if graph == "full" else "client"
        wf.invoke(initial_state(user_message, ui_role=ui_role), config=config)
    else:
        wf.invoke(append_message_input(user_message), config=config)
    metrics_service.register_thread(thread_id, graph=graph)
    metrics_service.persist_session_snapshot(thread_id, graph=graph)
    return build_session_state_payload(wf, thread_id, config)


def submit_review(
    thread_id: str,
    feedback: str,
    *,
    graph: GraphName = "full",
    interview_id: str | None = None,
) -> dict[str, Any]:
    wf = get_graph(graph)
    config = {"configurable": {"thread_id": thread_id}}
    wf.update_state(config, {"human_feedback": feedback})
    wf.invoke(None, config=config)
    if interview_id:
        _snapshot_to_interview(wf, config, interview_id)
    metrics_service.register_thread(thread_id, graph=graph)
    metrics_service.persist_session_snapshot(thread_id, graph=graph)
    return build_session_state_payload(wf, thread_id, config)


def get_excel_bytes(thread_id: str, *, graph: GraphName = "full") -> tuple[bytes, str]:
    wf = get_graph(graph)
    config = {"configurable": {"thread_id": thread_id}}
    values, _ = snapshot_values(wf, config)
    work_order = values.get("work_order") or {}
    excel_bytes: bytes | None = work_order.get("excel_bytes")
    if not excel_bytes:
        raise LookupError("Excel file not ready yet")
    order_no = work_order.get("order_number", "work_order")
    return excel_bytes, order_no


def _messages_to_langchain(messages: list[dict]) -> list[Any]:
    """Restore HumanMessages from stored plain dicts (user turns only)."""
    restored: list[Any] = []
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            restored.append(HumanMessage(content=str(m["content"])))
    return restored


def _snapshot_to_interview(wf, config, interview_id: str) -> None:
    """Copy work_order / cost / Excel bytes into the interview row if present."""
    values, _ = snapshot_values(wf, config)
    work_order = values.get("work_order") or None
    cost_estimates = values.get("cost_estimates") or None

    excel_bytes = None
    work_order_for_db: dict | None = None
    if work_order:
        excel_bytes = work_order.get("excel_bytes")
        work_order_for_db = {k: v for k, v in work_order.items() if k != "excel_bytes"}

    interviews_repo.save_production_output(
        interview_id,
        work_order=work_order_for_db,
        cost_estimates=cost_estimates,
        excel_bytes=excel_bytes,
    )
