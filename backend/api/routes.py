"""
API routes for the Dyz-Art MAS backend.

All graph state is persisted by LangGraph's MemorySaver keyed on thread_id,
so the compiled workflow stored in app.state is the single source of truth.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from langchain_core.messages import AIMessage, HumanMessage

from tools.llm_eval_metrics import (
    calculate_cost_from_rows,
    calculate_latency_metrics,
    gpt_4o_pricing,
)
from api.schemas import (
    MessageRequest,
    MetricsOverview,
    ReviewRequest,
    SessionCreated,
    SessionMetrics,
    SessionState,
)
from auth.dependencies import get_current_user
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
_KNOWN_THREAD_IDS: set[str] = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_wf(request: Request):
    return request.app.state.workflow


def _is_first_invocation(wf: Any, config: dict) -> bool:
    """Return True if no checkpointed messages exist for this thread yet."""
    try:
        snapshot = wf.get_state(config)
        if not snapshot or not snapshot.values:
            return True
        messages = snapshot.values.get("messages", [])
        return len(messages) == 0
    except Exception:
        return True


def _build_state(wf: Any, config: dict, thread_id: str) -> SessionState:
    """Read the current LangGraph checkpoint and convert it to SessionState."""
    try:
        snapshot = wf.get_state(config)
        values: dict = snapshot.values if isinstance(snapshot.values, dict) else {}
        next_nodes: list = list(snapshot.next) if snapshot.next else []
    except Exception as exc:
        logger.warning(f"Could not read graph snapshot: {exc}")
        values = {}
        next_nodes = []

    awaiting_human = "human_review" in next_nodes

    work_order_raw = values.get("work_order")
    excel_ready = bool(
        work_order_raw and work_order_raw.get("excel_bytes")
    )
    finished = excel_ready or bool(work_order_raw)

    # Serialise messages — strip excel_bytes from work_order before returning
    messages: list[dict] = []
    for msg in values.get("messages", []):
        if isinstance(msg, AIMessage):
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if has_tool_calls and not content.strip():
                continue
            messages.append(
                {
                    "role": "agent",
                    "content": msg.content,
                    "agent_name": (
                        getattr(msg, "name", None)
                        or values.get("current_agent", "Agent")
                    ),
                }
            )
        elif isinstance(msg, HumanMessage):
            messages.append(
                {"role": "user", "content": msg.content, "agent_name": ""}
            )

    work_order_safe = None
    if work_order_raw:
        work_order_safe = {
            k: v for k, v in work_order_raw.items() if k != "excel_bytes"
        }

    return SessionState(
        thread_id=thread_id,
        messages=messages,
        product_components=values.get("product_components", []),
        production_routes=values.get("production_routes", []),
        work_order=work_order_safe,
        cost_estimates=values.get("cost_estimates"),
        awaiting_human=awaiting_human,
        ambiguities=values.get("ambiguities", []),
        finished=finished,
        current_agent=values.get("current_agent", ""),
        excel_ready=excel_ready,
    )


def _session_metrics_from_snapshot(values: dict, thread_id: str) -> SessionMetrics:
    llm_eval = values.get("llm_eval") or {}
    rows = llm_eval.get("rows", [])
    latency_values = [float(r.get("latency_ms", 0.0)) for r in rows]
    latency = calculate_latency_metrics(latency_values, scope="conversation")
    cost = calculate_cost_from_rows(rows, gpt_4o_pricing(), scope="conversation")
    estimated = any(bool(r.get("estimated", False)) for r in rows)
    return SessionMetrics(
        thread_id=thread_id,
        call_count=int(llm_eval.get("session_call_count", len(rows))),
        estimated=estimated,
        core={},
        latency=latency,
        cost=cost,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=SessionCreated, status_code=201)
def create_session(
    _: dict = Depends(get_current_user),
) -> SessionCreated:
    """Create a new session and return a unique thread_id."""
    thread_id = str(uuid.uuid4())
    _KNOWN_THREAD_IDS.add(thread_id)
    logger.info(f"New session created: {thread_id}")
    return SessionCreated(thread_id=thread_id)


@router.post("/sessions/{thread_id}/messages", response_model=SessionState)
def send_message(
    thread_id: str, body: MessageRequest, request: Request,
    _: dict = Depends(get_current_user),
) -> SessionState:
    """
    Send a user message and advance the workflow.

    - First call: starts a fresh graph run with the full initial state.
    - Subsequent calls: appends only the new HumanMessage; LangGraph merges it
      via the add_messages reducer from the stored checkpoint.
    """
    wf = _get_wf(request)
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"[{thread_id}] Received message: {body.message[:100]}")

    if _is_first_invocation(wf, config):
        logger.info(f"[{thread_id}] First invocation — starting fresh graph run")
        invoke_input = {
            "messages": [HumanMessage(content=body.message)],
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
        }
    else:
        logger.info(f"[{thread_id}] Subsequent invocation — appending message")
        invoke_input = {"messages": [HumanMessage(content=body.message)]}

    try:
        wf.invoke(invoke_input, config=config)
    except Exception as exc:
        logger.error(f"[{thread_id}] Workflow error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return _build_state(wf, config, thread_id)


@router.get("/sessions/{thread_id}/metrics", response_model=SessionMetrics)
def get_session_metrics(
    thread_id: str,
    request: Request,
    _: dict = Depends(get_current_user),
) -> SessionMetrics:
    wf = _get_wf(request)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = wf.get_state(config)
        values: dict = snapshot.values if isinstance(snapshot.values, dict) else {}
    except Exception as exc:
        logger.error(f"[{thread_id}] Failed to read metrics snapshot: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    return _session_metrics_from_snapshot(values, thread_id)


@router.get("/metrics/overview", response_model=MetricsOverview)
def get_metrics_overview(
    request: Request,
    _: dict = Depends(get_current_user),
) -> MetricsOverview:
    wf = _get_wf(request)
    all_rows: list[dict[str, Any]] = []
    per_session_cost: list[dict[str, float | str]] = []
    sessions_total = 0

    for thread_id in sorted(_KNOWN_THREAD_IDS):
        config = {"configurable": {"thread_id": thread_id}}
        with_context = True
        try:
            snapshot = wf.get_state(config)
            values = snapshot.values if isinstance(snapshot.values, dict) else {}
        except Exception:
            with_context = False
            values = {}
        if not with_context:
            continue
        sessions_total += 1
        metrics = _session_metrics_from_snapshot(values, thread_id)
        all_rows.extend(metrics.rows)
        per_session_cost.append({"thread_id": thread_id, "total_cost_usd": metrics.cost["total_cost_usd"]})

    latency = calculate_latency_metrics([float(r.get("latency_ms", 0.0)) for r in all_rows])
    cost = calculate_cost_from_rows(all_rows, gpt_4o_pricing())
    return MetricsOverview(
        sessions_total=sessions_total,
        calls_total=len(all_rows),
        estimated=any(bool(r.get("estimated", False)) for r in all_rows),
        core={},
        latency=latency,
        cost=cost,
        per_session_cost=per_session_cost,
    )


@router.post("/sessions/{thread_id}/review", response_model=SessionState)
def submit_review(
    thread_id: str, body: ReviewRequest, request: Request,
    current_user: dict = Depends(get_current_user),
) -> SessionState:
    """
    Inject expert feedback and resume the graph from the human_review interrupt.

    Uses the interrupt_before pattern:
      1. update_state() — writes human_feedback into the current checkpoint
      2. invoke(None)   — resumes execution from the paused human_review node
    """
    wf = _get_wf(request)
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"[{thread_id}] Expert review received: {body.feedback[:100]}")

    try:
        wf.update_state(config, {"human_feedback": body.feedback})
        wf.invoke(None, config=config)
    except Exception as exc:
        logger.error(f"[{thread_id}] Review workflow error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return _build_state(wf, config, thread_id)


@router.get("/sessions/{thread_id}/excel")
def get_excel(
    thread_id: str,
    request: Request,
    _: dict = Depends(get_current_user),
) -> Response:
    """Return the generated Excel work order as a binary download."""
    wf = _get_wf(request)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = wf.get_state(config)
        values: dict = snapshot.values if isinstance(snapshot.values, dict) else {}
        work_order = values.get("work_order") or {}
        excel_bytes: bytes | None = work_order.get("excel_bytes")
    except Exception as exc:
        logger.error(f"[{thread_id}] Failed to read Excel from state: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    if not excel_bytes:
        raise HTTPException(status_code=404, detail="Excel file not ready yet")

    order_no = work_order.get("order_number", "work_order")
    logger.info(f"[{thread_id}] Serving Excel: {order_no}.xlsx ({len(excel_bytes)} bytes)")

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{order_no}.xlsx"'},
    )
