"""
Expert (technologist) view — three panels (Inbox / New interview / Session):

1. **Inbox** — completed client interviews. Can be "launched" into the
   production graph to generate a work order.
2. **New interview** — run the full_graph from scratch (expert on the phone
   with the client, filling in requirements themselves).
3. **Open session** — continue an already-started full_graph / production
   thread, including HITL review and Excel download.
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from api_client import api, api_bytes
from common import agents as agents_ui
from common import chat, header
from common.panels import (
    excel_download,
    progress_bar,
    render_components,
    render_cost_estimates,
    render_routes,
)

_STATE = "expert_state"
_EXPERT_TAB = "expert_tab"  # "inbox" | "new" | "session" — st.tabs cannot switch programmatically



def _ensure_state() -> None:
    st.session_state.setdefault(_EXPERT_TAB, "inbox")
    if _STATE not in st.session_state:
        st.session_state[_STATE] = {
            "active_source": None,            # "interview" | "session"
            "interview_id": None,
            "thread_id": None,
            "graph": "full",                  # "full" | "production"
            "messages": [],
            "agent_steps": agents_ui.initial_agent_steps(),
            "awaiting_human": False,
            "finished": False,
            "excel_ready": False,
            "product_components": [],
            "production_routes": [],
            "work_order": None,
            "cost_estimates": None,
            "ambiguities": [],
            "current_agent": "",
            "excel_bytes": None,
            # DB row status for client-sourced interviews: completed | processed (progress bar)
            "interview_status": None,
        }


def _reset_active() -> None:
    if _STATE in st.session_state:
        del st.session_state[_STATE]
    _ensure_state()


def _apply_state_payload(data: dict) -> None:
    state = st.session_state[_STATE]
    steps = state["agent_steps"]

    previous_count = len(state["messages"])
    new_messages = data.get("messages", [])
    state["messages"] = new_messages
    for msg in new_messages[previous_count:]:
        if msg.get("role") == "agent":
            agents_ui.update_agent_status(
                steps, msg.get("agent_name", ""), data.get("finished", False)
            )

    state["awaiting_human"] = data.get("awaiting_human", False)
    state["finished"] = data.get("finished", False)
    state["excel_ready"] = data.get("excel_ready", False)
    state["product_components"] = data.get("product_components", [])
    state["production_routes"] = data.get("production_routes", [])
    state["ambiguities"] = data.get("ambiguities", [])
    state["current_agent"] = data.get("current_agent", "")

    if data.get("work_order"):
        state["work_order"] = data["work_order"]
    if data.get("cost_estimates"):
        state["cost_estimates"] = data["cost_estimates"]

    agents_ui.refresh_queue_status(steps, state["awaiting_human"])


def _fetch_excel() -> None:
    state = st.session_state[_STATE]
    if state["excel_bytes"] or not state["excel_ready"]:
        return
    if state["active_source"] == "interview" and state["interview_id"]:
        path = f"/api/inbox/{state['interview_id']}/excel"
    elif state["active_source"] == "session" and state["thread_id"]:
        path = f"/api/sessions/{state['thread_id']}/excel"
    else:
        return
    data = api_bytes("GET", path)
    if data:
        state["excel_bytes"] = data


# Tab 1: Inbox

_STATUS_LABEL = {
    "in_progress": "🟡 Триває",
    "completed":   "✅ Завершено клієнтом",
    "processed":   "📦 У роботі (запущено)",
}


def _format_dt(value) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value.strftime("%d.%m.%Y %H:%M")


def _inbox_card(r: dict, *, allow_launch: bool) -> None:
    """One inbox row: details + optional launch (only for client-completed, not yet started)."""
    title = r.get("title") or f"Інтерв'ю {r['id'][:8]}"
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"**{title}**")
            st.caption(
                f"{_STATUS_LABEL.get(r['status'], r['status'])} · "
                f"створено {_format_dt(r.get('created_at'))}"
            )
        with right:
            if st.button("🔍 Деталі", key=f"view_{r['id']}", use_container_width=True):
                _load_interview_details(r["id"])
                st.session_state[_EXPERT_TAB] = "session"
                st.rerun()
            if allow_launch and st.button(
                "🚀 Опрацювати",
                key=f"launch_{r['id']}",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner("🚀 Запускаємо виробничий пайплайн…"):
                    _launch_interview(r["id"])
                st.session_state[_EXPERT_TAB] = "session"
                st.rerun()


def _tab_inbox() -> None:
    rows = api("GET", "/api/inbox")
    if rows is None:
        return
    if not rows:
        st.info("Наразі немає завершених клієнтських інтерв'ю.")
        return

    # Inbox lists both completed and processed rows; status changes after launch.
    queued = [r for r in rows if r.get("status") == "completed"]
    in_flight = [r for r in rows if r.get("status") == "processed"]

    st.markdown("##### Очікують запуску")
    st.caption("Клієнт завершив інтерв'ю — тут лише заявки, які ще не запускали в виробничий пайплайн.")
    if not queued:
        st.info("Немає нових заявок у черзі.")
    else:
        for r in queued:
            _inbox_card(r, allow_launch=True)

    st.divider()
    st.markdown("##### У роботі (вже запущено)")
    st.caption(
        "Після натискання «Опрацювати» заявка переходить сюди. Відкрий **Сесія** через «Деталі», "
        "щоб продовжити HITL або завантажити Excel."
    )
    if not in_flight:
        st.caption("Поки порожньо.")
    else:
        for r in in_flight:
            _inbox_card(r, allow_launch=False)


def _load_interview_details(interview_id: str) -> None:
    detail = api("GET", f"/api/inbox/{interview_id}")
    if detail is None:
        return
    _reset_active()
    state = st.session_state[_STATE]
    state.update(
        active_source="interview",
        interview_id=detail["id"],
        thread_id=detail.get("production_thread_id"),
        graph="production",
        interview_status=detail.get("status"),
        messages=detail.get("messages") or [],
        product_components=(detail.get("collected_data") or {}).get("product_components", []),
        ambiguities=(detail.get("collected_data") or {}).get("ambiguities", []),
        work_order=detail.get("work_order"),
        cost_estimates=detail.get("cost_estimates"),
        excel_ready=bool(detail.get("excel_ready") or detail.get("work_order")),
        finished=detail["status"] == "processed" and bool(detail.get("work_order")),
    )


def _launch_interview(interview_id: str) -> None:
    data = api("POST", f"/api/inbox/{interview_id}/launch", timeout=300.0)
    if data is None:
        return
    _reset_active()
    state = st.session_state[_STATE]
    state["active_source"] = "interview"
    state["interview_id"] = data["interview_id"]
    state["thread_id"] = data["production_thread_id"]
    state["graph"] = "production"
    state["interview_status"] = "processed"
    _apply_state_payload(data)
    _fetch_excel()



def _start_full_session() -> None:
    data = api("POST", "/api/sessions")
    if data is None:
        return
    _reset_active()
    state = st.session_state[_STATE]
    state["active_source"] = "session"
    state["thread_id"] = data["thread_id"]
    state["graph"] = "full"


def _tab_new_session() -> None:
    state = st.session_state[_STATE]
    st.caption(
        "Проведіть інтерв'ю з клієнтом самостійно (наприклад, по телефону) — "
        "пайплайн пройде повний цикл: інтерв'ю → технолог → валідація → генерація."
    )
    if state["active_source"] != "session" or not state["thread_id"]:
        if st.button(
            "✨ Створити нову сесію", type="primary", use_container_width=True,
            key="btn_new_session",
        ):
            _start_full_session()
            st.session_state[_EXPERT_TAB] = "session"
            st.rerun()
    else:
        st.success(
            f"Активна сесія: `{state['thread_id']}` — перейдіть на вкладку **Сесія** "
            "(або вона відкриється автоматично після створення)."
        )



def _send_session_message(user_input: str) -> None:
    state = st.session_state[_STATE]
    if not state["thread_id"]:
        return
    state["messages"].append({"role": "user", "content": user_input, "agent_name": ""})
    path = f"/api/sessions/{state['thread_id']}/messages"
    with st.spinner("🤖 Агенти обробляють запит…"):
        data = api("POST", path, json={"message": user_input}, timeout=300.0)
    if data is None:
        return
    _apply_state_payload(data)
    _fetch_excel()
    st.rerun()


def _submit_session_review(feedback: str) -> None:
    state = st.session_state[_STATE]
    if not state["thread_id"]:
        return
    state["messages"].append(
        {"role": "user", "content": f"**[Експерт]:** {feedback}", "agent_name": "HumanExpert"}
    )
    state["awaiting_human"] = False
    state["agent_steps"]["HumanExpert"] = "done"
    path = f"/api/sessions/{state['thread_id']}/review"
    with st.spinner("⚙️ Обробка відповіді експерта…"):
        data = api("POST", path, json={"feedback": feedback})
    if data is None:
        return
    _apply_state_payload(data)
    _fetch_excel()
    st.rerun()


def _tab_session() -> None:
    state = st.session_state[_STATE]
    if not state["thread_id"] and not state["interview_id"]:
        st.info("Оберіть запис у **Inbox** або почніть нову сесію у вкладці **Нове інтерв'ю**.")
        return

    col_chat, col_info = st.columns([3, 2], gap="large")

    with col_chat:
        st.markdown('<div class="section-title">💬 Чат із системою</div>', unsafe_allow_html=True)
        msgs = state["messages"]
        if not msgs:
            chat.render_chat(msgs)
        else:
            chat_height = min(480, max(200, 120 + len(msgs) * 85))
            with st.container(height=chat_height, border=False):
                chat.render_chat(msgs)

        if state["awaiting_human"]:
            chat.hitl_form(
                form_key="expert_hitl_form",
                ambiguities=state["ambiguities"],
                on_submit=_submit_session_review,
            )
        elif state["finished"]:
            chat.done_banner(on_restart=_reset_active)
        elif state["active_source"] == "session":
            chat.chat_input_form(
                form_key="expert_chat_form",
                on_send=_send_session_message,
                reset_callback=_reset_active,
            )
        else:
            st.caption("Запуск виробничого пайплайну з клієнтського інтерв'ю.")
            if st.button("🚀 Запустити обробку", type="primary", use_container_width=True):
                _launch_interview(state["interview_id"])
                st.rerun()

    with col_info:
        progress_bar(_compute_progress(state), label="📊 Прогрес замовлення")
        agents_ui.render_agent_panel(state["agent_steps"])
        render_components(state["product_components"])
        render_routes(state["production_routes"])
        render_cost_estimates(state["cost_estimates"])

        order_no = (state.get("work_order") or {}).get("order_number", "work_order")
        excel_download(state["excel_bytes"], file_name=order_no)


def _compute_progress(state: dict) -> int:
    if state.get("finished"):
        return 100
    if (
        state.get("active_source") == "interview"
        and state.get("interview_status") == "completed"
    ):
        return 100
    steps = state["agent_steps"]
    done_or_active = sum(1 for v in steps.values() if v in ("done", "active"))
    if state["product_components"]:
        return min(40 + int(done_or_active / len(steps) * 50), 95)
    return min(len(state["messages"]) * 8, 35)



def render() -> None:
    _ensure_state()
    header.render(subtitle="Робоче місце технолога — інтерв'ю, опрацювання заявок, HITL")

    # Buttons instead of st.tabs so navigation can switch to the session tab after actions.
    tab = st.session_state.get(_EXPERT_TAB, "inbox")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "📥 Inbox",
            use_container_width=True,
            type="primary" if tab == "inbox" else "secondary",
            key="expert_nav_inbox",
        ):
            st.session_state[_EXPERT_TAB] = "inbox"
            st.rerun()
    with c2:
        if st.button(
            "✨ Нове інтерв'ю",
            use_container_width=True,
            type="primary" if tab == "new" else "secondary",
            key="expert_nav_new",
        ):
            st.session_state[_EXPERT_TAB] = "new"
            st.rerun()
    with c3:
        if st.button(
            "💬 Сесія",
            use_container_width=True,
            type="primary" if tab == "session" else "secondary",
            key="expert_nav_session",
        ):
            st.session_state[_EXPERT_TAB] = "session"
            st.rerun()

    if tab == "inbox":
        _tab_inbox()
    elif tab == "new":
        _tab_new_session()
    else:
        _tab_session()
