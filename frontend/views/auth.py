"""
Auth gate — login + open registration (new users default to role=client).
"""

from __future__ import annotations

import streamlit as st

from api_client import login, register


def render() -> None:
    # full-screen gradient background
    st.markdown('<div class="auth-page-bg"></div>', unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown(
            """
            <div class="auth-card">
              <div class="auth-logo">
                <span class="auth-logo-icon">🖨️</span>
                <div class="auth-title">Dyz-Art MAS</div>
                <div class="auth-sub">Виробничий планувальник · Multi-Agent System</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["Увійти", "Реєстрація"])

        with tab_login:
            _render_login()

        with tab_reg:
            _render_register()


def _render_login() -> None:
    with st.form("login_form"):
        username = st.text_input("Логін", placeholder="введіть логін")
        password = st.text_input("Пароль", type="password", placeholder="введіть пароль")
        submitted = st.form_submit_button(
            "Увійти →", use_container_width=True, type="primary"
        )

    if submitted:
        if not username or not password:
            st.error("Заповніть логін і пароль.")
            return
        with st.spinner("Входимо..."):
            ok = login(username, password)
        if ok:
            st.toast("Ласкаво просимо!", icon="✅")
            st.rerun()
        else:
            st.error("Невірний логін або пароль.")


def _render_register() -> None:
    with st.form("register_form"):
        reg_email    = st.text_input("Email", placeholder="you@example.com")
        reg_username = st.text_input("Логін", placeholder="мінімум 3 символи")
        reg_password = st.text_input(
            "Пароль", type="password", placeholder="мінімум 8 символів"
        )
        reg_confirm  = st.text_input(
            "Підтвердити пароль", type="password", placeholder="повторіть пароль"
        )
        reg_submitted = st.form_submit_button(
            "Створити акаунт →", use_container_width=True, type="primary"
        )

    if reg_submitted:
        errors = _validate_register(reg_email, reg_username, reg_password, reg_confirm)
        if errors:
            for e in errors:
                st.error(e)
            return
        with st.spinner("Створюємо акаунт..."):
            ok, err = register(reg_email, reg_username, reg_password)
        if ok:
            st.toast("Акаунт створено! Тепер увійдіть.", icon="✅")
        else:
            st.error(err or "Помилка реєстрації.")


def _validate_register(
    email: str, username: str, password: str, confirm: str
) -> list[str]:
    errors: list[str] = []
    if not email or "@" not in email:
        errors.append("Введіть коректний email.")
    if len(username) < 3:
        errors.append("Логін має містити мінімум 3 символи.")
    if len(password) < 8:
        errors.append("Пароль має містити мінімум 8 символів.")
    if password and confirm and password != confirm:
        errors.append("Паролі не збігаються.")
    return errors
