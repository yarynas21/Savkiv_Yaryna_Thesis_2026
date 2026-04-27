"""
Agent-status UI: icon/label table, card renderer, queue marker refresher.

Shared between the expert and full_graph-based views. Clients don't see the
pipeline — they only interact with the conversational agent.
"""

from __future__ import annotations

import streamlit as st

AGENT_LABELS: dict[str, tuple[str, str]] = {
    "ClientInterfaceAgent": ("💬", "Агент-інтерв'юер"),
    "TechnologistAgent":    ("⚙️", "Технолог"),
    "ValidationAgent":      ("🔍", "Валідатор"),
    "HumanExpert":          ("👤", "Експерт (Human-in-the-Loop)"),
    "GenerationAgent":      ("📄", "Генератор документів"),
}

AGENT_EXECUTION_ORDER: list[str] = [
    "ClientInterfaceAgent",
    "TechnologistAgent",
    "ValidationAgent",
    "HumanExpert",
    "GenerationAgent",
]


def initial_agent_steps() -> dict[str, str]:
    return {k: "pending" for k in AGENT_EXECUTION_ORDER}


def agent_card(agent_id: str, status: str) -> str:
    icon, label = AGENT_LABELS.get(agent_id, ("🤖", agent_id))
    card_cls = {
        "active":  "agent-card agent-card-active",
        "done":    "agent-card agent-card-done",
        "waiting": "agent-card agent-card-waiting",
        "pending": "agent-card agent-card-pending",
    }.get(status, "agent-card agent-card-pending")
    dot_cls = {
        "active":  "agent-dot dot-active",
        "done":    "agent-dot dot-done",
        "waiting": "agent-dot dot-waiting",
        "pending": "agent-dot dot-pending",
    }.get(status, "agent-dot dot-pending")
    status_text, status_cls = {
        "active":  ("▶ Активний", "status-active"),
        "done":    ("✓ Виконано", "status-done"),
        "waiting": ("⏸ Очікує",   "status-waiting"),
        "pending": ("· У черзі",  "status-pending"),
    }.get(status, ("·", "status-pending"))
    return (
        f'<div class="{card_cls}">'
        f'<span class="{dot_cls}"></span>'
        f'<span class="agent-label">{icon} {label}</span>'
        f'<span class="agent-status-text {status_cls}">{status_text}</span>'
        f'</div>'
    )


def refresh_queue_status(steps: dict[str, str], awaiting_human: bool) -> None:
    """Mark the next pipeline slot as ``waiting`` (or HumanExpert if paused)."""
    for key in list(steps.keys()):
        if steps[key] == "waiting":
            steps[key] = "pending"

    if awaiting_human and steps.get("HumanExpert") not in ("done", "active"):
        steps["HumanExpert"] = "waiting"
        return

    for idx, agent in enumerate(AGENT_EXECUTION_ORDER):
        if steps.get(agent) == "active":
            for next_agent in AGENT_EXECUTION_ORDER[idx + 1:]:
                if steps.get(next_agent) == "pending":
                    steps[next_agent] = "waiting"
                    break
            return

    for agent in AGENT_EXECUTION_ORDER:
        if steps.get(agent) == "pending":
            steps[agent] = "waiting"
            break


def update_agent_status(steps: dict[str, str], agent_name: str, finished: bool) -> None:
    """Flip the named agent to ``active`` (or ``done`` if the run is finished)."""
    for key in steps:
        if steps[key] == "active":
            steps[key] = "done"
    if agent_name in steps:
        steps[agent_name] = "done" if finished else "active"


def render_agent_panel(steps: dict[str, str]) -> None:
    st.markdown('<div class="section-title">🤖 Статус агентів</div>', unsafe_allow_html=True)
    for agent_id in AGENT_LABELS:
        st.markdown(agent_card(agent_id, steps.get(agent_id, "pending")), unsafe_allow_html=True)
