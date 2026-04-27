"""Client-side interview flow — runs interview_graph and persists the conversation."""

from __future__ import annotations

import uuid
from typing import Any

from db.repositories import interviews as interviews_repo
from graph.registry import get_graph
from services._graph_state import (
    append_message_input,
    build_session_state_payload,
    initial_state,
    is_first_invocation,
    serialize_messages,
    snapshot_values,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def create_interview(client_user_id: str, title: str | None = None) -> dict:
    thread_id = str(uuid.uuid4())
    return interviews_repo.create_interview(
        client_user_id=client_user_id,
        thread_id=thread_id,
        title=title,
    )


def list_my_interviews(client_user_id: str) -> list[dict]:
    return interviews_repo.list_by_client(client_user_id)


def get_interview(interview_id: str) -> dict | None:
    return interviews_repo.get_interview(interview_id)


def send_message(interview_id: str, user_message: str) -> dict[str, Any]:
    """Advance the interview_graph one turn; persist progress; return payload."""
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise LookupError("Interview not found")
    if record["status"] == "processed":
        raise PermissionError("Interview already handed off to an expert")

    thread_id = str(record["thread_id"])
    logger.info("[%s] interview turn started (thread=%s)", interview_id, thread_id)
    wf = get_graph("interview")
    config = {"configurable": {"thread_id": thread_id}}

    if is_first_invocation(wf, config):
        wf.invoke(initial_state(user_message, ui_role="client"), config=config)
    else:
        wf.invoke(append_message_input(user_message), config=config)
    logger.info("[%s] graph invoke returned", interview_id)

    values, _ = snapshot_values(wf, config)
    messages = serialize_messages(values)

    # Always snapshot so DB stays in sync with the checkpointer.
    interviews_repo.save_messages(interview_id, messages)

    if record["status"] == "in_progress" and values.get("requirements_complete"):
        title = _derive_title(messages) or record["title"]
        record = interviews_repo.mark_completed(
            interview_id,
            messages=messages,
            collected_data={
                "client_requirements": values.get("client_requirements", {}),
                "product_components": values.get("product_components", []),
                "ambiguities": values.get("ambiguities", []),
            },
            title=title,
        )

    payload = build_session_state_payload(wf, thread_id, config)
    payload["interview_id"] = str(record["id"])
    payload["status"] = record["status"]
    logger.info(
        "[%s] interview turn finished (status=%s, messages=%s)",
        interview_id,
        payload["status"],
        len(payload.get("messages") or []),
    )
    return payload


def _derive_title(messages: list[dict]) -> str | None:
    """Use the first user message as interview title."""
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            text = str(m["content"]).strip().splitlines()[0]
            return text[:120]
    return None
