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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ---- Global ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background: #F5F7FA;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="block-container"] { padding-top: 1.5rem; }

    /* ---- Top header ---- */
    .mas-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #1F6FEB 100%);
        color: white;
        padding: 20px 28px;
        border-radius: 16px;
        margin-bottom: 0px;
        box-shadow: 0 4px 20px rgba(31,111,235,0.25);
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .mas-header-icon { font-size: 2.2rem; line-height: 1; }
    .mas-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
    .mas-header p  { margin: 3px 0 0; opacity: 0.75; font-size: 0.82rem; }

    /* ---- User card ---- */
    .user-card {
        background: white;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        text-align: center;
        border: 1px solid #E8EDF5;
    }
    .user-avatar {
        width: 40px; height: 40px;
        background: linear-gradient(135deg, #1F6FEB, #7B2FBE);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem; font-weight: 700; color: white;
        margin: 0 auto 8px;
    }
    .user-name { font-weight: 600; font-size: 0.88rem; color: #1a1a2e; }
    .user-role { font-size: 0.75rem; color: #8896A8; margin-top: 2px; }

    /* ---- Agent status cards ---- */
    .agent-card {
        background: white;
        border: 1px solid #E8EDF5;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 5px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        transition: box-shadow 0.2s;
    }
    .agent-card-active {
        border-color: #34C759;
        background: #F0FFF4;
        box-shadow: 0 0 0 2px rgba(52,199,89,0.15);
    }
    .agent-card-done {
        border-color: #1F6FEB;
        background: #EFF6FF;
    }
    .agent-card-waiting {
        border-color: #FF9500;
        background: #FFFBF0;
    }
    .agent-card-pending {
        background: #FFFFFF;
        border-color: #D6DEE8;
        opacity: 1;
    }
    .agent-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .dot-active  { background: #34C759; box-shadow: 0 0 6px rgba(52,199,89,0.6); }
    .dot-done    { background: #1F6FEB; }
    .dot-waiting { background: #FF9500; }
    .dot-pending { background: #94A3B8; }
    .agent-label { font-size: 0.82rem; font-weight: 500; color: #374151; flex: 1; }
    .agent-status-text { font-size: 0.72rem; font-weight: 600; }
    .status-active  { color: #15803D; }
    .status-done    { color: #1D4ED8; }
    .status-waiting { color: #B45309; }
    .status-pending { color: #64748B; }

    /* ---- Progress bar ---- */
    .progress-wrap {
        background: white;
        border-radius: 12px;
        padding: 14px 16px;
        border: 1px solid #E8EDF5;
        margin-bottom: 6px;
    }
    .progress-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .progress-bar-bg {
        background: #E8EDF5;
        border-radius: 99px;
        height: 6px;
        overflow: hidden;
    }
    .progress-bar-fill {
        height: 100%;
        border-radius: 99px;
        background: linear-gradient(90deg, #1F6FEB, #34C759);
        transition: width 0.4s ease;
    }
    .progress-pct {
        font-size: 0.75rem;
        color: #1F6FEB;
        font-weight: 700;
        text-align: right;
        margin-top: 4px;
    }

    /* ── Section titles ── */
    .section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #94A3B8;
        margin: 16px 0 8px;
    }

    /* ── Product components ── */
    .component-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 10px;
    }
    .component-card {
        background: #FFFFFF;
        border: 1px solid #E8EDF5;
        border-radius: 10px;
        padding: 10px 12px;
    }
    .component-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #1F2937;
        margin-bottom: 4px;
    }
    .component-meta {
        font-size: 0.78rem;
        color: #64748B;
        line-height: 1.4;
    }

    /* ── Cost card ── */
    .cost-card {
        background: linear-gradient(135deg, #F0FFF4, #EFF6FF);
        border: 1px solid #BBF7D0;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 4px 0;
    }

    /* ── Auth page ── */
    .auth-logo {
        text-align: center;
        margin-bottom: 24px;
    }
    .auth-logo-icon { font-size: 3rem; display: block; margin-bottom: 8px; }
    .auth-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1a3a5c;
        letter-spacing: -0.03em;
    }
    .auth-sub { color: #8896A8; font-size: 0.88rem; margin-top: 4px; }

    /* ── Chat container scrollbar ── */
    [data-testid="stVerticalBlockBorderWrapper"] div::-webkit-scrollbar { width: 4px; }
    [data-testid="stVerticalBlockBorderWrapper"] div::-webkit-scrollbar-thumb {
        background: #E8EDF5; border-radius: 99px;
    }

    /* ── Chat message overrides ── */
    [data-testid="stChatMessage"] {
        background: white;
        border-radius: 12px;
        border: 1px solid #F0F4F8;
        margin-bottom: 4px;
    }

    /* ── Success / done state ── */
    .done-banner {
        background: linear-gradient(135deg, #F0FFF4, #EFF6FF);
        border: 1.5px solid #34C759;
        border-radius: 14px;
        padding: 18px 20px;
        text-align: center;
    }
    .done-banner h3 { color: #15803D; margin: 0 0 6px; font-size: 1.1rem; }
    .done-banner p  { color: #374151; margin: 0; font-size: 0.85rem; }

    /* ── Input area ── */
    [data-testid="stTextArea"] textarea {
        border-radius: 10px !important;
        border-color: #E8EDF5 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stTextArea"] textarea:focus {
        border-color: #1F6FEB !important;
        box-shadow: 0 0 0 2px rgba(31,111,235,0.15) !important;
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
        "llm_metrics_session": None,
        "llm_metrics_overview": None,
        "product_components": [],
        "production_routes": [],
        "ambiguities": [],
        "current_agent": "",
        "order_progress": 0,
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


# ── Auth gate ─────────────────────────────────────────────────────────────────
def _show_auth_page() -> None:
    st.markdown(
        """
        <style>
        .auth-box {
            max-width: 400px;
            margin: 40px auto 0;
            background: white;
            border-radius: 20px;
            padding: 40px 44px;
            box-shadow: 0 8px 40px rgba(31,58,92,0.10);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col = st.columns([1, 1.8, 1])[1]
    with col:
        st.markdown(
            """
            <div class="auth-logo">
              <span class="auth-logo-icon">🖨️</span>
              <div class="auth-title">Dyz-Art MAS</div>
              <div class="auth-sub">Виробничий планувальник</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["🔑 Увійти", "✏️ Реєстрація"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Логін", placeholder="admin")
                password = st.text_input("Пароль", type="password")
                submitted = st.form_submit_button("Увійти →", use_container_width=True)
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
                reg_submitted = st.form_submit_button("Створити акаунт →", use_container_width=True)
                if reg_submitted:
                    ok, err = _do_register(reg_email, reg_username, reg_password)
                    if ok:
                        st.success("✅ Акаунт створено! Тепер увійдіть.")
                    else:
                        st.error(err)


if not st.session_state.get("access_token"):
    _show_auth_page()
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
_header_col, _user_col = st.columns([6, 1])
with _header_col:
    st.markdown(
        """
        <div class="mas-header">
          <div class="mas-header-icon">🖨️</div>
          <div>
            <h1>Dyz-Art | MAS Виробничий Планувальник</h1>
            <p>Multi-Agent System · автоматична генерація технологічних маршрутів у поліграфії</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with _user_col:
    _u = st.session_state.get("current_user") or {}
    _uname = _u.get("username", "?")
    _initial = _uname[0].upper() if _uname else "?"
    st.markdown(
        f"""
        <div class="user-card">
          <div class="user-avatar">{_initial}</div>
          <div class="user-name">{_uname}</div>
          <div class="user-role">{_u.get("role", "користувач")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Вийти", use_container_width=True, key="logout_btn"):
        _logout()

st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

# ── Agent labels ──────────────────────────────────────────────────────────────
_AGENT_LABELS = {
    "ClientInterfaceAgent": ("💬", "Агент-інтерв'юер"),
    "TechnologistAgent":    ("⚙️", "Технолог"),
    "ValidationAgent":      ("🔍", "Валідатор"),
    "HumanExpert":          ("👤", "Експерт (Human-in-the-Loop)"),
    "GenerationAgent":      ("📄", "Генератор документів"),
}
_AGENT_EXECUTION_ORDER = [
    "ClientInterfaceAgent",
    "TechnologistAgent",
    "ValidationAgent",
    "HumanExpert",
    "GenerationAgent",
]


def _agent_card(agent_id: str, status: str) -> str:
    icon, label = _AGENT_LABELS.get(agent_id, ("🤖", agent_id))
    card_cls = {
        "active": "agent-card agent-card-active",
        "done":   "agent-card agent-card-done",
        "waiting":"agent-card agent-card-waiting",
        "pending":"agent-card agent-card-pending",
    }.get(status, "agent-card agent-card-pending")
    dot_cls = {
        "active": "agent-dot dot-active",
        "done":   "agent-dot dot-done",
        "waiting":"agent-dot dot-waiting",
        "pending":"agent-dot dot-pending",
    }.get(status, "agent-dot dot-pending")
    status_text = {
        "active":  ("▶ Активний", "status-active"),
        "done":    ("✓ Виконано", "status-done"),
        "waiting": ("⏸ Очікує", "status-waiting"),
        "pending": ("· У черзі",  "status-pending"),
    }.get(status, ("·", "status-pending"))
    return (
        f'<div class="{card_cls}">'
        f'<span class="{dot_cls}"></span>'
        f'<span class="agent-label">{icon} {label}</span>'
        f'<span class="agent-status-text {status_text[1]}">{status_text[0]}</span>'
        f'</div>'
    )


def _refresh_agent_queue_status() -> None:
    """Refresh waiting/queue marker so the next agent in pipeline is visible."""
    steps = st.session_state["agent_steps"]

    for key in list(steps.keys()):
        if steps[key] == "waiting":
            steps[key] = "pending"

    if st.session_state.get("awaiting_human") and steps.get("HumanExpert") not in ("done", "active"):
        steps["HumanExpert"] = "waiting"
        return

    for idx, agent in enumerate(_AGENT_EXECUTION_ORDER):
        if steps.get(agent) == "active":
            for next_agent in _AGENT_EXECUTION_ORDER[idx + 1:]:
                if steps.get(next_agent) == "pending":
                    steps[next_agent] = "waiting"
                    break
            return

    for agent in _AGENT_EXECUTION_ORDER:
        if steps.get(agent) == "pending":
            steps[agent] = "waiting"
            break


# ── Order progress ─────────────────────────────────────────────────────────────
def _compute_progress() -> int:
    """Estimate order collection progress 0-100 based on session state."""
    steps_done = sum(
        1 for s in st.session_state["agent_steps"].values() if s in ("done", "active")
    )
    total = len(st.session_state["agent_steps"])
    if st.session_state.get("finished"):
        return 100
    components = st.session_state.get("product_components", [])
    if components:
        base = 40 + int((steps_done / total) * 50)
        return min(base, 95)
    msg_count = len(st.session_state.get("messages", []))
    return min(msg_count * 8, 35)


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, **kwargs) -> dict | None:
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
    existing_count = len(st.session_state["messages"])
    for msg in data.get("messages", [])[existing_count:]:
        st.session_state["messages"].append(msg)
        if msg["role"] == "agent":
            _update_agent_status(msg.get("agent_name", ""))

    st.session_state["awaiting_human"]     = data.get("awaiting_human", False)
    st.session_state["finished"]           = data.get("finished", False)
    st.session_state["excel_ready"]        = data.get("excel_ready", False)
    st.session_state["product_components"] = data.get("product_components", [])
    st.session_state["production_routes"]  = data.get("production_routes", [])
    st.session_state["ambiguities"]        = data.get("ambiguities", [])
    st.session_state["current_agent"]      = data.get("current_agent", "")
    _refresh_agent_queue_status()

    if data.get("work_order"):
        st.session_state["work_order"] = data["work_order"]
    if data.get("cost_estimates"):
        st.session_state["cost_estimates"] = data["cost_estimates"]

    if data.get("excel_ready") and not st.session_state["excel_bytes"]:
        _fetch_excel()
    _refresh_metrics()


def _fetch_excel() -> None:
    thread_id = st.session_state["thread_id"]
    url = f"{API_BASE}/api/sessions/{thread_id}/excel"
    try:
        resp = httpx.get(url, headers=_auth_headers(), timeout=30.0)
        resp.raise_for_status()
        st.session_state["excel_bytes"] = resp.content
    except Exception as exc:
        st.warning(f"⚠️ Не вдалося завантажити Excel: {exc}")


def _refresh_metrics() -> None:
    thread_id = st.session_state["thread_id"]
    session_metrics = _api("GET", f"/api/sessions/{thread_id}/metrics")
    overview_metrics = _api("GET", "/api/metrics/overview")
    if session_metrics is not None:
        st.session_state["llm_metrics_session"] = session_metrics
    if overview_metrics is not None:
        st.session_state["llm_metrics_overview"] = overview_metrics


def _update_agent_status(agent_name: str) -> None:
    steps = st.session_state["agent_steps"]
    for key in steps:
        if steps[key] == "active":
            steps[key] = "done"
    if agent_name in steps:
        steps[agent_name] = "active" if not st.session_state["finished"] else "done"
    _refresh_agent_queue_status()


def _send_message(user_input: str) -> None:
    thread_id = st.session_state["thread_id"]
    data = _api(
        "POST",
        f"/api/sessions/{thread_id}/messages",
        json={"message": user_input},
    )
    if data:
        _apply_state(data)


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


_refresh_agent_queue_status()
_refresh_metrics()


# ── Render chat messages ───────────────────────────────────────────────────────
def _render_chat() -> None:
    if not st.session_state["messages"]:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #EFF6FF, #F5F3FF);
                border: 1px solid #DBEAFE;
                border-radius: 14px;
                padding: 20px 24px;
                text-align: center;
                color: #374151;
            ">
                <div style="font-size:2rem;margin-bottom:8px">👋</div>
                <div style="font-weight:600;font-size:0.95rem;margin-bottom:6px">
                    Вітаємо у Dyz-Art MAS!
                </div>
                <div style="font-size:0.82rem;color:#6B7280">
                    Опишіть ваше замовлення, наприклад:<br>
                    <em>«Потрібна преміальна коробка для настільної гри, тираж 1000 шт.,
                    з колодою 110 карт і правилами. Дедлайн — 30 днів»</em>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            icon, label = _AGENT_LABELS.get(
                msg.get("agent_name", ""), ("🤖", msg.get("agent_name", "Агент"))
            )
            with st.chat_message("assistant", avatar=icon):
                st.caption(label)
                st.markdown(msg["content"])


# ── Two-column layout ─────────────────────────────────────────────────────────
col_chat, col_info = st.columns([3, 2], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — Chat
# ─────────────────────────────────────────────────────────────────────────────
with col_chat:
    st.markdown('<div class="section-title">💬 Чат із системою</div>', unsafe_allow_html=True)

    chat_height = 370 if not st.session_state["messages"] else 490
    chat_container = st.container(height=chat_height, border=False)
    with chat_container:
        _render_chat()

    # ── Human-in-the-loop ────────────────────────────────────────────────────
    if st.session_state["awaiting_human"]:
        st.markdown(
            """
            <div style="
                background:#FFFBF0;border:1.5px solid #FF9500;
                border-radius:12px;padding:14px 18px;margin-top:8px
            ">
            <strong>⏸️ Очікується відповідь технолога-експерта</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ambiguities = st.session_state.get("ambiguities", [])
        if ambiguities:
            st.markdown("**Питання від валідатора:**")
            for i, q in enumerate(ambiguities, 1):
                st.markdown(f"{i}. {q}")

        with st.form("human_form", clear_on_submit=True):
            expert_input = st.text_area(
                "Ваша відповідь як технолог-експерт:",
                placeholder="Введіть технічне уточнення...",
                height=90,
            )
            submitted = st.form_submit_button("📤 Надіслати відповідь", use_container_width=True)
            if submitted and expert_input.strip():
                st.session_state["messages"].append(
                    {"role": "user", "content": f"**[Експерт]:** {expert_input}", "agent_name": "HumanExpert"}
                )
                st.session_state["awaiting_human"] = False
                with st.spinner("⚙️ Обробка відповіді експерта…"):
                    _send_review(expert_input)
                st.rerun()

    # ── Regular chat input ────────────────────────────────────────────────────
    elif not st.session_state["finished"]:
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Повідомлення",
                placeholder="Опишіть замовлення або відповідайте на уточнення агента…",
                height=80,
                label_visibility="collapsed",
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
                with st.spinner("🤖 Агенти обробляють запит…"):
                    _send_message(user_input)
                st.rerun()

            if reset:
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    else:
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
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — Info panel
# ─────────────────────────────────────────────────────────────────────────────
with col_info:

    # ── Progress indicator ────────────────────────────────────────────────────
    progress = _compute_progress()
    st.markdown(
        f"""
        <div class="progress-wrap">
            <div class="progress-label">📊 Прогрес замовлення</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width:{progress}%"></div>
            </div>
            <div class="progress-pct">{progress}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Agent status cards ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 Статус агентів</div>', unsafe_allow_html=True)
    for agent_id in _AGENT_LABELS:
        status = st.session_state["agent_steps"].get(agent_id, "pending")
        st.markdown(_agent_card(agent_id, status), unsafe_allow_html=True)

    # ── Product components ────────────────────────────────────────────────────
    components = st.session_state["product_components"]
    if components:
        st.markdown('<div class="section-title">📦 Склад замовлення</div>', unsafe_allow_html=True)
        cards_html = '<div class="component-list">'
        for comp in components:
            raw_name = str(comp.get("name", comp.get("id", "—")))
            comp_name = raw_name[:1].upper() + raw_name[1:] if raw_name else "—"
            comp_type = comp.get("type") or comp.get("component_id") or "не вказано"
            qty = comp.get("quantity")
            qty_text = f" • Кількість: {qty}" if qty is not None else ""
            cards_html += (
                f'<div class="component-card">'
                f'<div class="component-title">📌 {comp_name}</div>'
                f'<div class="component-meta">Компонент: {comp_type}{qty_text}</div>'
                f'</div>'
            )
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        with st.expander("Деталі компонентів", expanded=False):
            for comp in components:
                raw_name = str(comp.get("name", comp.get("id", "—")))
                comp_name = raw_name[:1].upper() + raw_name[1:] if raw_name else "—"
                st.markdown(f"**{comp_name}**")
                st.json(comp, expanded=False)

    # ── Production routes ─────────────────────────────────────────────────────
    routes = st.session_state["production_routes"]
    if routes:
        st.markdown('<div class="section-title">🔧 Технологічні маршрути</div>', unsafe_allow_html=True)
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
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "№": st.column_config.NumberColumn(width="small"),
                        "Операція": st.column_config.TextColumn(width="medium"),
                    },
                )

    # ── Cost estimates ────────────────────────────────────────────────────────
    cost_est = st.session_state["cost_estimates"]
    if cost_est:
        st.markdown('<div class="section-title">💰 Калькуляція вартості</div>', unsafe_allow_html=True)
        import pandas as pd

        tiers = cost_est.get("tiers", {})
        if tiers:
            df_cost = pd.DataFrame(
                [{"Тираж": k, "Вартість (грн)": f"{v:,.0f} ₴"} for k, v in tiers.items()]
            )
            st.dataframe(df_cost, use_container_width=True, hide_index=True)
        setup = cost_est.get("setup_costs", 0)
        if setup:
            st.markdown(
                f'<div class="cost-card">💡 <strong>Разові витрати</strong> (кліше/штампи): '
                f'<strong>{setup:,.0f} ₴</strong></div>',
                unsafe_allow_html=True,
            )
        note = cost_est.get("note", "")
        if note:
            st.caption(note)

    # ── Excel download ────────────────────────────────────────────────────────
    excel_bytes = st.session_state["excel_bytes"]
    if excel_bytes:
        st.markdown('<div class="section-title">📥 Документи</div>', unsafe_allow_html=True)
        wo = st.session_state.get("work_order") or {}
        order_no = wo.get("order_number", "work_order")
        st.download_button(
            label="⬇️ Завантажити Технічне Завдання (Excel)",
            data=excel_bytes,
            file_name=f"{order_no}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

    # ── LLM Eval metrics ──────────────────────────────────────────────────────
    llm_session = st.session_state.get("llm_metrics_session")
    if llm_session:
        st.markdown('<div class="section-title">📈 LLM Eval</div>', unsafe_allow_html=True)

        session = llm_session or {}

        cost = session.get("cost", {})
        if cost:
            st.caption("Cost (current full conversation)")
            st.metric("total_cost_usd", f"{float(cost.get('total_cost_usd', 0.0)):.4f}")

        latency = session.get("latency", {})
        if latency:
            st.caption("Latency")
            c_lat1, c_lat2 = st.columns(2)
            with c_lat1:
                st.metric("p50", f"{float(latency.get('latency_p50_min', 0.0)):.2f} хв")
            with c_lat2:
                st.metric("p95", f"{float(latency.get('latency_p95_min', 0.0)):.2f} хв")

    # ── Footer info ───────────────────────────────────────────────────────────
    st.divider()
    provider = os.getenv("LLM_PROVIDER", "openai").upper()
    model_map = {
        "OPENAI":    os.getenv("OPENAI_MODEL", "gpt-4o"),
        "ANTHROPIC": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        "GOOGLE":    os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
    }
    model = model_map.get(provider, "—")
    _msg_count = len(st.session_state.get("messages", []))
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption(f"🔌 **{provider}** / {model}")
    with col_b:
        st.caption(f"💬 Повідомлень: {_msg_count}")
