"""
Dyz-Art MAS — Streamlit Frontend
==================================
Multi-Agent System for Production Workflow Generation in the Printing Industry.

Communicates with the FastAPI backend via HTTP (httpx).
Set API_BASE_URL in .env to point to the backend (default: http://localhost:8000).

Layout:
  Left column  → chat interface (client ↔ agents dialogue)
  Right column → agent status tracker | product components | route table | Excel download
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dyz-Art MAS | Виробничий планувальник",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ---- Global ---- */
    [data-testid="stAppViewContainer"] {
        background: #F0F4F8;
    }
    /* ---- Top header ---- */
    .mas-header {
        background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
        color: white;
        padding: 18px 28px;
        border-radius: 12px;
        margin-bottom: 18px;
    }
    .mas-header h1 { margin: 0; font-size: 1.7rem; }
    .mas-header p  { margin: 4px 0 0; opacity: 0.85; font-size: 0.9rem; }

    /* ---- Agent status badge ---- */
    .agent-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 2px 0;
    }
    .badge-active   { background: #D4EDDA; color: #155724; }
    .badge-done     { background: #CCE5FF; color: #004085; }
    .badge-waiting  { background: #FFF3CD; color: #856404; }
    .badge-pending  { background: #E2E3E5; color: #495057; }

    /* ---- Chat bubbles ---- */
    .chat-user {
        background: #2E75B6;
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 10px 16px;
        margin: 6px 0 6px 20%;
        font-size: 0.92rem;
    }
    .chat-agent {
        background: white;
        color: #212529;
        border-radius: 18px 18px 18px 4px;
        padding: 10px 16px;
        margin: 6px 20% 6px 0;
        border: 1px solid #DEE2E6;
        font-size: 0.92rem;
    }
    .chat-agent-name {
        font-size: 0.72rem;
        color: #6C757D;
        margin-bottom: 4px;
    }

    /* ---- Section titles ---- */
    .section-title {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6C757D;
        margin: 14px 0 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state initialisation ──────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict[str, Any] = {
        # Auth
        "access_token": None,
        "current_user": None,
        # Session
        "thread_id": str(uuid.uuid4()),
        "messages": [],
        "awaiting_human": False,
        "finished": False,
        "excel_ready": False,
        "agent_steps": {
            "ClientInterfaceAgent": "pending",
            "TechnologistAgent":    "pending",
            "ValidationAgent":      "pending",
            "HumanExpert":          "pending",
            "GenerationAgent":      "pending",
        },
        "excel_bytes": None,
        "work_order": None,
        "cost_estimates": None,
        "product_components": [],
        "production_routes": [],
        "ambiguities": [],
        "current_agent": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _auth_headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _do_login(username: str, password: str) -> bool:
    try:
        resp = httpx.post(
            f"{API_BASE}/auth/token",
            json={"username": username, "password": password},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["access_token"] = data["access_token"]
            # Fetch profile
            me = httpx.get(
                f"{API_BASE}/auth/me",
                headers=_auth_headers(),
                timeout=10.0,
            )
            if me.status_code == 200:
                st.session_state["current_user"] = me.json()
            return True
        return False
    except Exception:
        return False


def _do_register(email: str, username: str, password: str) -> tuple[bool, str]:
    try:
        resp = httpx.post(
            f"{API_BASE}/auth/register",
            json={"email": email, "username": username, "password": password},
            timeout=15.0,
        )
        if resp.status_code == 201:
            return True, ""
        detail = resp.json().get("detail", "Помилка реєстрації")
        return False, detail
    except Exception as exc:
        return False, str(exc)


def _logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ── Auth gate — show login/register if not authenticated ──────────────────────
def _show_auth_page() -> None:
    st.markdown(
        """
        <style>
        .auth-box {
            max-width: 420px;
            margin: 60px auto 0;
            background: white;
            border-radius: 16px;
            padding: 36px 40px;
            box-shadow: 0 4px 24px rgba(31,78,121,0.12);
        }
        .auth-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1F4E79;
            margin-bottom: 4px;
        }
        .auth-sub { color: #6C757D; font-size: 0.9rem; margin-bottom: 24px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown('<div class="auth-title">🖨️ Dyz-Art MAS</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-sub">Виробничий планувальник</div>', unsafe_allow_html=True)

        tab_login, tab_reg = st.tabs(["Увійти", "Реєстрація"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Логін", placeholder="admin")
                password = st.text_input("Пароль", type="password")
                submitted = st.form_submit_button("Увійти", use_container_width=True)
                if submitted:
                    if _do_login(username, password):
                        st.rerun()
                    else:
                        st.error("Невірний логін або пароль")

        with tab_reg:
            with st.form("register_form"):
                reg_email    = st.text_input("Email", placeholder="you@example.com")
                reg_username = st.text_input("Логін", placeholder="мінімум 3 символи")
                reg_password = st.text_input("Пароль", type="password",
                                             placeholder="мінімум 8 символів")
                reg_submitted = st.form_submit_button("Створити акаунт", use_container_width=True)
                if reg_submitted:
                    ok, err = _do_register(reg_email, reg_username, reg_password)
                    if ok:
                        st.success("Акаунт створено! Тепер увійдіть.")
                    else:
                        st.error(err)


if not st.session_state.get("access_token"):
    _show_auth_page()
    st.stop()

# ── Header (shown only when authenticated) ────────────────────────────────────
_header_col, _user_col = st.columns([5, 1])
with _header_col:
    st.markdown(
        """
        <div class="mas-header">
          <h1>🖨️ Dyz-Art | MAS Виробничий Планувальник</h1>
          <p>Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфії</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with _user_col:
    _u = st.session_state.get("current_user") or {}
    st.markdown(f"**{_u.get('username', '')}**")
    st.caption(_u.get("role", ""))
    if st.button("Вийти", use_container_width=True):
        _logout()

# ── Agent label / badge helpers ───────────────────────────────────────────────
_AGENT_LABELS = {
    "ClientInterfaceAgent": "1️⃣  Агент-інтерв'юер",
    "TechnologistAgent":    "2️⃣  Технолог",
    "ValidationAgent":      "3️⃣  Валідатор",
    "HumanExpert":          "👤  Експерт (Human-in-the-Loop)",
    "GenerationAgent":      "4️⃣  Генератор документів",
}


def _badge(status: str) -> str:
    cls = {
        "active":  "badge-active",
        "done":    "badge-done",
        "waiting": "badge-waiting",
        "pending": "badge-pending",
    }.get(status, "badge-pending")
    labels = {
        "active":  "▶ Активний",
        "done":    "✓ Виконано",
        "waiting": "⏸ Очікує",
        "pending": "· Очікує черги",
    }
    return f'<span class="agent-badge {cls}">{labels.get(status, status)}</span>'


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, **kwargs) -> dict | None:
    """Make a synchronous HTTP call to the FastAPI backend."""
    url = f"{API_BASE}{path}"
    headers = {**_auth_headers(), **kwargs.pop("headers", {})}
    try:
        resp = httpx.request(method, url, timeout=120.0, headers=headers, **kwargs)
        if resp.status_code == 401:
            st.warning("Сесія закінчилася. Будь ласка, увійдіть знову.")
            _logout()
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        st.error(
            f"❌ Не вдалося підключитися до бекенду ({API_BASE}). "
            "Переконайтеся, що FastAPI-сервер запущено."
        )
        return None
    except httpx.HTTPStatusError as exc:
        st.error(f"❌ Помилка API [{exc.response.status_code}]: {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"❌ Несподівана помилка: {exc}")
        return None


def _apply_state(data: dict) -> None:
    """Apply the SessionState JSON returned by the API to Streamlit session_state."""
    # Sync new messages (API returns all messages; find ones we haven't shown yet)
    existing_count = len(st.session_state["messages"])
    for msg in data.get("messages", [])[existing_count:]:
        st.session_state["messages"].append(msg)
        if msg["role"] == "agent":
            _update_agent_status(msg.get("agent_name", ""))

    st.session_state["awaiting_human"]    = data.get("awaiting_human", False)
    st.session_state["finished"]          = data.get("finished", False)
    st.session_state["excel_ready"]       = data.get("excel_ready", False)
    st.session_state["product_components"] = data.get("product_components", [])
    st.session_state["production_routes"]  = data.get("production_routes", [])
    st.session_state["ambiguities"]        = data.get("ambiguities", [])
    st.session_state["current_agent"]      = data.get("current_agent", "")

    if data.get("work_order"):
        st.session_state["work_order"] = data["work_order"]
    if data.get("cost_estimates"):
        st.session_state["cost_estimates"] = data["cost_estimates"]

    # Eagerly fetch Excel bytes once the document is ready
    if data.get("excel_ready") and not st.session_state["excel_bytes"]:
        _fetch_excel()


def _fetch_excel() -> None:
    """Download Excel bytes from the backend and cache them in session state."""
    thread_id = st.session_state["thread_id"]
    url = f"{API_BASE}/api/sessions/{thread_id}/excel"
    try:
        resp = httpx.get(url, headers=_auth_headers(), timeout=30.0)
        resp.raise_for_status()
        st.session_state["excel_bytes"] = resp.content
    except Exception as exc:
        st.warning(f"⚠️ Не вдалося завантажити Excel: {exc}")


def _update_agent_status(agent_name: str) -> None:
    steps = st.session_state["agent_steps"]
    for key in steps:
        if steps[key] == "active":
            steps[key] = "done"
    if agent_name in steps:
        steps[agent_name] = "active" if not st.session_state["finished"] else "done"


# ── Run: send user message ─────────────────────────────────────────────────
def _send_message(user_input: str) -> None:
    thread_id = st.session_state["thread_id"]
    data = _api(
        "POST",
        f"/api/sessions/{thread_id}/messages",
        json={"message": user_input},
    )
    if data:
        _apply_state(data)


# ── Run: submit expert review ──────────────────────────────────────────────
def _send_review(feedback: str) -> None:
    thread_id = st.session_state["thread_id"]
    data = _api(
        "POST",
        f"/api/sessions/{thread_id}/review",
        json={"feedback": feedback},
    )
    if data:
        st.session_state["agent_steps"]["HumanExpert"] = "done"
        _apply_state(data)


# ── Render chat messages ───────────────────────────────────────────────────
def _render_chat() -> None:
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            label = _AGENT_LABELS.get(msg.get("agent_name", ""), msg.get("agent_name", ""))
            st.markdown(
                f'<div class="chat-agent">'
                f'<div class="chat-agent-name">{label}</div>'
                f'{msg["content"].replace(chr(10), "<br>")}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Two-column layout ─────────────────────────────────────────────────────────
col_chat, col_info = st.columns([3, 2], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — Chat
# ─────────────────────────────────────────────────────────────────────────────
with col_chat:
    st.markdown('<div class="section-title">💬 Чат із системою</div>', unsafe_allow_html=True)

    if not st.session_state["messages"]:
        st.info(
            "**Вітаємо у Dyz-Art MAS!**\n\n"
            "Опишіть ваше замовлення — наприклад:\n\n"
            "> *«Мені потрібна преміальна коробка для колекційної настільної гри "
            "тираж 1000 шт., з колодою 110 карт і правилами. "
            "Дедлайн — 30 днів»*",
        )

    chat_container = st.container(height=450)
    with chat_container:
        _render_chat()

    # ── Human-in-the-loop expert panel ────────────────────────────────────
    if st.session_state["awaiting_human"]:
        st.warning("⏸️ **Система очікує відповіді технолога-експерта**")
        ambiguities = st.session_state.get("ambiguities", [])
        if ambiguities:
            st.markdown("**Питання від валідатора:**")
            for i, q in enumerate(ambiguities, 1):
                st.markdown(f"{i}. {q}")

        with st.form("human_form", clear_on_submit=True):
            expert_input = st.text_area(
                "Ваша відповідь як технолог-експерт:",
                placeholder="Введіть технічне уточнення...",
                height=100,
            )
            submitted = st.form_submit_button("📤 Надіслати відповідь")
            if submitted and expert_input.strip():
                st.session_state["messages"].append(
                    {"role": "user", "content": f"[Експерт]: {expert_input}", "agent_name": "HumanExpert"}
                )
                st.session_state["awaiting_human"] = False
                with st.spinner("Обробка відповіді експерта…"):
                    _send_review(expert_input)
                st.rerun()

    # ── Regular chat input ─────────────────────────────────────────────────
    elif not st.session_state["finished"]:
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Ваше повідомлення:",
                placeholder="Опишіть замовлення або відповідайте на уточнення агента…",
                height=80,
            )
            col_send, col_reset = st.columns([3, 1])
            with col_send:
                send = st.form_submit_button("📨 Надіслати", use_container_width=True)
            with col_reset:
                reset = st.form_submit_button("🔄 Скинути", use_container_width=True)

            if send and user_input.strip():
                st.session_state["messages"].append(
                    {"role": "user", "content": user_input, "agent_name": ""}
                )
                with st.spinner("Агенти обробляють запит…"):
                    _send_message(user_input)
                st.rerun()

            if reset:
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    else:
        st.success("✅ Замовлення опрацьовано. Документи готові до завантаження.")
        if st.button("🔄 Нове замовлення"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — Info panel
# ─────────────────────────────────────────────────────────────────────────────
with col_info:

    # ── Agent status tracker ──────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 Статус агентів</div>', unsafe_allow_html=True)

    for agent_id, label in _AGENT_LABELS.items():
        status = st.session_state["agent_steps"].get(agent_id, "pending")
        badge_html = _badge(status)
        st.markdown(
            f"<div style='margin:3px 0'>{label}&nbsp;&nbsp;{badge_html}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Product components ────────────────────────────────────────────────
    components = st.session_state["product_components"]
    if components:
        st.markdown(
            '<div class="section-title">📦 Компоненти продукту</div>',
            unsafe_allow_html=True,
        )
        for comp in components:
            with st.expander(f"📌 {comp.get('name', comp.get('id', '—'))}", expanded=False):
                st.json(comp, expanded=False)

    # ── Production routes table ───────────────────────────────────────────
    routes = st.session_state["production_routes"]
    if routes:
        st.markdown(
            '<div class="section-title">🔧 Технологічні маршрути</div>',
            unsafe_allow_html=True,
        )
        import pandas as pd

        for route in routes:
            comp_label = route.get("component_name", route.get("component_id", "Компонент"))
            ops = route.get("operations", [])
            if ops:
                rows = [
                    {
                        "№": op.get("step", ""),
                        "Операція": op.get("operation_name", op.get("operation_id", "")),
                        "Обладнання": op.get("machine") or "—",
                        "Примітки": op.get("notes") or "—",
                    }
                    for op in ops
                ]
                st.markdown(f"**{comp_label}**")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Cost estimates ────────────────────────────────────────────────────
    cost_est = st.session_state["cost_estimates"]
    if cost_est:
        st.markdown(
            '<div class="section-title">💰 Калькуляція вартості</div>',
            unsafe_allow_html=True,
        )
        import pandas as pd

        tiers = cost_est.get("tiers", {})
        if tiers:
            df_cost = pd.DataFrame(
                [{"Тираж": k, "Вартість (грн)": f"{v:,.0f}"} for k, v in tiers.items()]
            )
            st.dataframe(df_cost, use_container_width=True, hide_index=True)
        setup = cost_est.get("setup_costs", 0)
        if setup:
            st.caption(f"Разові витрати (кліше/штампи): {setup:,.0f} грн")
        st.caption(cost_est.get("note", ""))

    # ── Excel download ────────────────────────────────────────────────────
    excel_bytes = st.session_state["excel_bytes"]
    if excel_bytes:
        st.divider()
        st.markdown(
            '<div class="section-title">📥 Документи</div>',
            unsafe_allow_html=True,
        )
        wo = st.session_state.get("work_order") or {}
        order_no = wo.get("order_number", "work_order")
        st.download_button(
            label="⬇️ Завантажити Технічне Завдання (Excel)",
            data=excel_bytes,
            file_name=f"{order_no}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── LLM provider indicator ────────────────────────────────────────────
    st.divider()
    provider = os.getenv("LLM_PROVIDER", "openai").upper()
    model_map = {
        "OPENAI":    os.getenv("OPENAI_MODEL", "gpt-4o"),
        "ANTHROPIC": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        "GOOGLE":    os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
    }
    model = model_map.get(provider, "—")
    st.caption(f"🔌 LLM: **{provider}** / {model}")
    st.caption(f"🔗 API: {API_BASE}")
