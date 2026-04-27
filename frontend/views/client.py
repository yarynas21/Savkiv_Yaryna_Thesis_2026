"""
Client view — interview-only UX.

* Left column:  conversation with the ConversationalAgent.
* Right column: progress bar + "my interviews" history.

No access to technologist/validation/generation agents, no metrics, no
Excel download — those live behind the expert role.
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from api_client import api
from common import chat, header
from common.panels import progress_bar

_STATE_KEY_MESSAGES = "client_messages"
_STATE_KEY_INTERVIEW = "client_interview"
_STATE_KEY_HISTORY = "client_history"



def _ensure_state() -> None:
    st.session_state.setdefault(_STATE_KEY_MESSAGES, [])
    st.session_state.setdefault(_STATE_KEY_INTERVIEW, None)
    st.session_state.setdefault(_STATE_KEY_HISTORY, None)


def _reset_active_interview() -> None:
    st.session_state[_STATE_KEY_MESSAGES] = []
    st.session_state[_STATE_KEY_INTERVIEW] = None


def _refresh_history() -> None:
    rows = api("GET", "/api/interviews/me")
    if rows is not None:
        st.session_state[_STATE_KEY_HISTORY] = rows



def _start_new_interview() -> dict | None:
    record = api("POST", "/api/interviews", json={"title": None})
    if record is None:
        return None
    st.session_state[_STATE_KEY_INTERVIEW] = record
    st.session_state[_STATE_KEY_MESSAGES] = []
    _refresh_history()
    return record


def _load_interview(interview_id: str) -> None:
    record = api("GET", f"/api/interviews/{interview_id}")
    if record is None:
        return
    st.session_state[_STATE_KEY_INTERVIEW] = {
        "id": record["id"],
        "thread_id": record["thread_id"],
        "title": record.get("title"),
        "status": record["status"],
        "created_at": record.get("created_at"),
    }
    st.session_state[_STATE_KEY_MESSAGES] = record.get("messages") or []



def _send(user_input: str) -> None:
    active = st.session_state[_STATE_KEY_INTERVIEW]
    if active is None:
        active = _start_new_interview()
        if active is None:
            return

    st.session_state[_STATE_KEY_MESSAGES].append(
        {"role": "user", "content": user_input, "agent_name": ""}
    )
    with st.spinner("🤖 Агент-інтерв'юер обробляє запит…"):
        data = api(
            "POST",
            f"/api/interviews/{active['id']}/messages",
            json={"message": user_input},
            timeout=300.0,
        )
    if data is None:
        return

    st.session_state[_STATE_KEY_MESSAGES] = data.get("messages", [])
    st.session_state[_STATE_KEY_INTERVIEW]["status"] = data.get("status", active.get("status"))
    _refresh_history()
    st.rerun()



def _format_dt(value) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value.strftime("%d.%m.%Y %H:%M")


_STATUS_LABEL = {
    "in_progress": "🟡 Триває",
    "completed":   "✅ Завершено",
    "processed":   "📦 Опрацьовано експертом",
}


def _render_history_panel() -> None:
    st.markdown('<div class="section-title">📚 Мої інтерв\'ю</div>', unsafe_allow_html=True)
    rows = st.session_state.get(_STATE_KEY_HISTORY)
    if rows is None:
        _refresh_history()
        rows = st.session_state.get(_STATE_KEY_HISTORY, [])
    if not rows:
        st.caption("Ще немає жодного інтерв'ю.")
        return
    for r in rows:
        label = r.get("title") or f"Інтерв'ю {r['id'][:8]}"
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.caption(
                f"{_STATUS_LABEL.get(r['status'], r['status'])} · "
                f"{_format_dt(r.get('created_at'))}"
            )
            if st.button("Відкрити", key=f"open_{r['id']}", use_container_width=True):
                _load_interview(r["id"])
                st.rerun()


def _compute_progress(messages: list[dict], status: str) -> int:
    if status == "completed" or status == "processed":
        return 100
    msg_count = len(messages)
    return min(msg_count * 12, 90)


def render() -> None:
    _ensure_state()
    header.render(subtitle="Онлайн-інтерв'ю для збору вимог до замовлення")

    active = st.session_state[_STATE_KEY_INTERVIEW]
    messages = st.session_state[_STATE_KEY_MESSAGES]
    status = (active or {}).get("status", "in_progress")

    col_chat, col_info = st.columns([3, 2], gap="large")

    with col_chat:
        if active is None:
            st.info(
                "Розпочніть нове інтерв'ю — після відповідей на всі запитання "
                "агент збереже вашу заявку, і наш технолог зв'яжеться щодо наступних кроків."
            )
            if st.button("✨ Почати нове інтерв'ю", type="primary", use_container_width=True):
                _start_new_interview()
                st.rerun()
        else:
            st.markdown(
                '<div class="section-title">💬 Інтерв\'ю з агентом</div>',
                unsafe_allow_html=True,
            )
            if not messages:
                chat.render_chat(messages)
            else:
                chat_height = min(480, max(200, 120 + len(messages) * 85))
                with st.container(height=chat_height, border=False):
                    chat.render_chat(messages)

            if status == "in_progress":
                chat.chat_input_form(
                    form_key="client_chat_form",
                    on_send=_send,
                    reset_callback=_reset_active_interview,
                )
            else:
                st.success(
                    "Ваше інтерв'ю збережено. Технолог отримає його найближчим часом "
                    "та опрацює деталі замовлення."
                )
                if st.button("✨ Почати нове інтерв'ю", use_container_width=True):
                    _reset_active_interview()
                    st.rerun()

    with col_info:
        progress_bar(_compute_progress(messages, status), label="📊 Прогрес інтерв'ю")
        _render_history_panel()
