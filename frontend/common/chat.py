"""
Chat rendering + input form + Human-in-the-Loop expert form.

Consumes the plain-dict ``messages`` list produced by the backend
(``{role, content, agent_name}``).
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from common.agents import AGENT_LABELS


def render_chat(messages: list[dict], *, empty_hint: str | None = None) -> None:
    """Render the scrollable chat history."""
    if not messages:
        hint = empty_hint or (
            "Опишіть ваше замовлення — наприклад, тираж, вид продукції, дедлайн."
        )
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #EFF6FF, #F5F3FF);
                border: 1px solid #DBEAFE;
                border-radius: 14px; padding: 20px 24px;
                text-align: center; color: #374151;
            ">
                <div style="font-size:2rem;margin-bottom:8px">👋</div>
                <div style="font-weight:600;font-size:0.95rem;margin-bottom:6px">
                    Вітаємо у Dyz-Art MAS!
                </div>
                <div style="font-size:0.82rem;color:#6B7280">{hint}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for msg in messages:
        if msg.get("role") == "user":
            with st.chat_message("user"):
                st.markdown(msg.get("content", ""))
        else:
            icon, label = AGENT_LABELS.get(
                msg.get("agent_name", ""), ("🤖", msg.get("agent_name", "Агент"))
            )
            with st.chat_message("assistant", avatar=icon):
                st.caption(label)
                st.markdown(msg.get("content", ""))


def chat_input_form(
    *,
    form_key: str,
    on_send: Callable[[str], None],
    reset_callback: Callable[[], None] | None = None,
    placeholder: str = "Опишіть замовлення або відповідайте на уточнення агента…",
) -> None:
    """Textarea + Send (+ optional Reset) inside a ``st.form``."""
    with st.form(form_key, clear_on_submit=True):
        user_input = st.text_area(
            "Повідомлення", placeholder=placeholder,
            height=80, label_visibility="collapsed",
        )
        if reset_callback is not None:
            col_send, col_reset = st.columns([3, 1])
            with col_send:
                send = st.form_submit_button("📨 Надіслати", use_container_width=True)
            with col_reset:
                reset = st.form_submit_button("🔄 Скинути", use_container_width=True)
        else:
            send = st.form_submit_button("📨 Надіслати", use_container_width=True)
            reset = False

        if send and user_input.strip():
            on_send(user_input.strip())
        if reset:
            reset_callback()  # type: ignore[misc]


def hitl_form(
    *,
    form_key: str,
    ambiguities: list[str],
    on_submit: Callable[[str], None],
) -> None:
    """The Human-in-the-Loop expert answer form (shown when graph is paused)."""
    st.markdown(
        """
        <div style="
            background:#FFFBF0; border:1.5px solid #FF9500;
            border-radius:12px; padding:14px 18px; margin-top:8px
        ">
        <strong>⏸️ Очікується відповідь технолога-експерта</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if ambiguities:
        st.markdown("**Питання від валідатора:**")
        for i, q in enumerate(ambiguities, 1):
            st.markdown(f"{i}. {q}")

    with st.form(form_key, clear_on_submit=True):
        expert_input = st.text_area(
            "Ваша відповідь як технолог-експерт:",
            placeholder="Введіть технічне уточнення...",
            height=90,
        )
        submitted = st.form_submit_button(
            "📤 Надіслати відповідь", use_container_width=True
        )
        if submitted and expert_input.strip():
            on_submit(expert_input.strip())


def done_banner(on_restart: Callable[[], None]) -> None:
    st.markdown(
        """
        <div class="done-banner">
            <h3>✅ Замовлення опрацьовано!</h3>
            <p>Технічне завдання сформовано. Завантажте документ у правій панелі.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Нове замовлення", use_container_width=True):
        on_restart()
