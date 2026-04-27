"""
Top banner + user card + logout button.
Used by every authenticated view.
"""

from __future__ import annotations

import streamlit as st

from api_client import logout

_ROLE_LABEL_UK = {
    "admin": "Адміністратор",
    "expert": "Технолог",
    "client": "Клієнт",
}


def render(subtitle: str | None = None) -> None:
    """Render the top header + user card on a one-row two-column layout."""
    user = st.session_state.get("current_user") or {}
    uname = user.get("username", "?")
    initial = uname[0].upper() if uname else "?"
    role = user.get("role", "")
    role_uk = _ROLE_LABEL_UK.get(role, role)

    header_col, user_col = st.columns([6, 1])
    with header_col:
        caption = subtitle or (
            "Multi-Agent System · автоматична генерація технологічних маршрутів у поліграфії"
        )
        st.markdown(
            f"""
            <div class="mas-header">
              <div class="mas-header-icon">🖨️</div>
              <div>
                <h1>Dyz-Art | MAS Виробничий Планувальник</h1>
                <p>{caption}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with user_col:
        st.markdown(
            f"""
            <div class="user-card">
              <div class="user-avatar">{initial}</div>
              <div class="user-name">{uname}</div>
              <div class="user-role">{role_uk}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Вийти", use_container_width=True, key="logout_btn"):
            logout()

    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
