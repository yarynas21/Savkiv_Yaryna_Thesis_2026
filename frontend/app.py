"""
Dyz-Art MAS — Streamlit Frontend entry point.

Delegates all rendering to role-specific views after auth.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

st.set_page_config(
    page_title="Dyz-Art MAS | Виробничий планувальник",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from styles import inject  # noqa: E402 — must come after set_page_config
inject()

from views import auth, admin, client, expert  # noqa: E402

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("access_token"):
    auth.render()
    st.stop()

# ── Role-based dispatch ───────────────────────────────────────────────────────
_role = (st.session_state.get("current_user") or {}).get("role", "client")

if _role == "admin":
    admin.render()
elif _role == "expert":
    expert.render()
else:
    client.render()
