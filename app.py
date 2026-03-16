"""
Dyz-Art MAS — Streamlit UI
===========================
Multi-Agent System for Production Workflow Generation in the Printing Industry.

Layout:
  Left column  → chat interface (client ↔ agents dialogue)
  Right column → agent status tracker | product components | route table | Excel download
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any

# Make sure project root is on the path when running from IDE
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dyz-Art MAS | Виробничий планувальник",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
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

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="mas-header">
      <h1>🖨️ Dyz-Art | MAS Виробничий Планувальник</h1>
      <p>Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфії</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Session state initialisation ─────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "thread_id": str(uuid.uuid4()),
        "messages": [],           # list of {role, content, agent_name}
        "graph_state": None,      # last snapshot from LangGraph
        "workflow": None,         # compiled graph
        "awaiting_human": False,  # is graph paused at human_review?
        "finished": False,
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
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ── Lazy-load the compiled workflow ──────────────────────────────────────────
@st.cache_resource(show_spinner="Ініціалізація агентів…")
def _get_workflow():
    logger.info("Compiling LangGraph workflow...")
    from graph.workflow import compile_workflow
    workflow = compile_workflow()
    logger.info("Workflow compiled successfully")
    return workflow


def get_workflow():
    if st.session_state["workflow"] is None:
        logger.debug("Initializing workflow in session state")
        st.session_state["workflow"] = _get_workflow()
    return st.session_state["workflow"]


# ── Helper: map agent name → display label ───────────────────────────────────
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
    return (
        f'<span class="agent-badge {cls}">{labels.get(status, status)}</span>'
    )


# ── Run one LangGraph step ────────────────────────────────────────────────────
def _run_graph(user_input: str | None = None, human_feedback: str | None = None):
    """
    Drives the LangGraph workflow forward.

    - `user_input`     → initial / follow-up user message
    - `human_feedback` → expert answer when graph is paused at human_review
    """
    logger.info(f"Running workflow: user_input={bool(user_input)}, human_feedback={bool(human_feedback)}")
    wf = get_workflow()
    config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
    logger.debug(f"Thread ID: {st.session_state['thread_id']}")

    try:
        if human_feedback is not None:
            # Resume graph paused at interrupt_before=["human_review"].
            # CORRECT pattern for interrupt_before:
            #   1. update_state() — injects feedback into the CURRENT checkpoint
            #      (does NOT restart from START, preserves graph position)
            #   2. invoke(None)   — resumes from where it paused (human_review node)
            # NOTE: invoke({"human_feedback": ...}) would start a NEW run from START,
            # which is why we must NOT pass a state dict when resuming.
            logger.info("Resuming workflow with human feedback (update_state + invoke(None))")
            wf.update_state(config, {"human_feedback": human_feedback})
            result = wf.invoke(None, config=config)
            logger.debug(f"Workflow result type after resume: {type(result)}")
        elif user_input is not None:
            logger.info(f"Processing user input: {user_input[:100]}...")
            graph_state = st.session_state.get("graph_state") or {}
            logger.debug(f"Current graph state keys: {list(graph_state.keys())}")

            # Check if this is the first invocation (no prior state saved)
            is_first_invocation = not bool(graph_state)

            if is_first_invocation:
                # First message: start graph from scratch with full initial state
                logger.info("First invocation: starting graph from scratch")
                invoke_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "client_requirements": {},
                    "product_components": [],
                    "production_routes": [],
                    "validation_status": "pending",
                    "ambiguities": [],
                    "human_feedback": None,
                    "work_order": None,
                    "cost_estimates": None,
                    "current_agent": "",
                    "iteration": 0,
                }
            else:
                # Subsequent messages: only send the new human message.
                # LangGraph will APPEND it to the existing conversation history
                # in the checkpoint via the add_messages reducer.
                logger.info("Subsequent invocation: appending message to existing state")
                invoke_state = {
                    "messages": [HumanMessage(content=user_input)],
                }

            logger.debug("Invoking workflow")
            result = wf.invoke(invoke_state, config=config)
            logger.info(f"Workflow invocation completed. Result type: {type(result)}")
        else:
            logger.warning("_run_graph called without user_input or human_feedback")
            return

        _process_result(result)

        # Check if graph is paused at human_review (interrupt_before)
        try:
            snapshot = wf.get_state(config)
            logger.debug(f"Graph next nodes: {snapshot.next}")
            if "human_review" in (snapshot.next or []):
                logger.info("Graph paused at human_review — awaiting expert input")
                st.session_state["awaiting_human"] = True
                # Store ambiguities from the latest snapshot values
                snap_vals = snapshot.values if isinstance(snapshot.values, dict) else {}
                if snap_vals.get("ambiguities"):
                    st.session_state["graph_state"] = snap_vals
            else:
                st.session_state["awaiting_human"] = False
        except Exception as snap_err:
            logger.warning(f"Could not read graph snapshot: {snap_err}")

    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}", exc_info=True)
        st.error(f"❌ Помилка при виконанні workflow: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def _process_result(result: dict | Any):
    """Extract relevant info from graph output and update session state."""
    logger.info(f"Processing workflow result: type={type(result)}")
    logger.debug(f"Result attributes: {dir(result) if hasattr(result, '__dict__') else 'N/A'}")
    
    if result is None:
        logger.warning("Workflow returned None")
        st.warning("⚠️ Workflow повернув None. Можливо, потрібна додаткова конфігурація.")
        return

    # LangGraph may return a snapshot object or a plain dict
    # Try multiple ways to extract the state dict
    state_dict = {}
    
    if isinstance(result, dict):
        logger.debug("Result is a plain dict")
        state_dict = result
    elif hasattr(result, "values"):
        logger.debug("Result has 'values' attribute (LangGraph snapshot)")
        values = result.values
        logger.debug(f"values type: {type(values)}")
        # Check if values is callable (method) or a dict
        if callable(values):
            logger.debug("result.values is callable (method), calling it...")
            try:
                state_dict = values()
                logger.debug(f"Called values(), got type: {type(state_dict)}")
            except Exception as e:
                logger.error(f"Error calling values(): {e}", exc_info=True)
                # Try to use result as dict directly
                try:
                    if hasattr(result, "__getitem__"):
                        state_dict = dict(result)
                        logger.debug("Converted result to dict using dict()")
                except Exception as e2:
                    logger.error(f"Error converting result to dict: {e2}", exc_info=True)
        else:
            state_dict = values if isinstance(values, dict) else {}
            logger.debug(f"values is not callable, using as-is: {type(state_dict)}")
    elif hasattr(result, "__getitem__"):
        # Try to convert to dict if it supports indexing
        try:
            logger.debug("Result supports indexing, trying to convert to dict")
            state_dict = dict(result)
        except Exception as e:
            logger.warning(f"Could not convert result to dict: {e}")
            state_dict = {}
    else:
        logger.warning(f"Unexpected result type: {type(result)}")
        logger.debug(f"Result repr: {repr(result)[:200]}")
        st.warning(f"⚠️ Неочікуваний тип результату: {type(result)}")
        state_dict = {}

    # Ensure state_dict is a dict
    if not isinstance(state_dict, dict):
        logger.error(f"state_dict is not a dict, it's {type(state_dict)}")
        state_dict = {}

    # Debug: log what we received
    if not state_dict:
        logger.warning("State dict is empty")
        st.warning("⚠️ State dict порожній. Перевірте, чи правильно працює workflow.")
    else:
        logger.debug(f"State dict keys: {list(state_dict.keys())}")

    st.session_state["graph_state"] = state_dict

    # NOTE: awaiting_human is now set in _run_graph via wf.get_state(config).next

    # Update component data
    if state_dict.get("product_components"):
        st.session_state["product_components"] = state_dict["product_components"]
    if state_dict.get("production_routes"):
        st.session_state["production_routes"] = state_dict["production_routes"]

    # Extract agent messages
    messages = state_dict.get("messages", [])
    logger.debug(f"Found {len(messages)} messages in state")
    for msg in messages:
        if isinstance(msg, AIMessage):
            agent_name = getattr(msg, "name", None) or state_dict.get("current_agent", "Agent")
            logger.info(f"Adding message from agent: {agent_name}")
            _add_message("agent", msg.content, agent_name)
            _update_agent_status(agent_name)

    # Work order & costs
    if state_dict.get("work_order"):
        wo = state_dict["work_order"]
        st.session_state["work_order"] = wo
        if "excel_bytes" in wo:
            st.session_state["excel_bytes"] = wo["excel_bytes"]
        st.session_state["finished"] = True
        st.session_state["awaiting_human"] = False

    if state_dict.get("cost_estimates"):
        st.session_state["cost_estimates"] = state_dict["cost_estimates"]

    # Mark generation done
    current = state_dict.get("current_agent", "")
    if current == "GenerationAgent":
        st.session_state["agent_steps"]["GenerationAgent"] = "done"
        st.session_state["finished"] = True


def _add_message(role: str, content: str, agent_name: str = "") -> None:
    logger.debug(f"Adding message: role={role}, agent={agent_name}, content_length={len(content)}")
    st.session_state["messages"].append(
        {"role": role, "content": content, "agent_name": agent_name}
    )


def _update_agent_status(agent_name: str) -> None:
    steps = st.session_state["agent_steps"]
    # Mark previous active agents as done
    for key in steps:
        if steps[key] == "active":
            steps[key] = "done"
    if agent_name in steps:
        steps[agent_name] = "active" if not st.session_state["finished"] else "done"


# ── Render chat messages ──────────────────────────────────────────────────────
def _render_chat():
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            label = _AGENT_LABELS.get(msg["agent_name"], msg["agent_name"])
            st.markdown(
                f'<div class="chat-agent">'
                f'<div class="chat-agent-name">{label}</div>'
                f'{msg["content"].replace(chr(10), "<br>")}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Two-column layout ─────────────────────────────────────────────────────────
col_chat, col_info = st.columns([3, 2], gap="large")

# ────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — Chat
# ────────────────────────────────────────────────────────────────────────────
with col_chat:
    st.markdown('<div class="section-title">💬 Чат із системою</div>', unsafe_allow_html=True)

    # Welcome message on first load
    if not st.session_state["messages"]:
        st.info(
            "**Вітаємо у Dyz-Art MAS!**\n\n"
            "Опишіть ваше замовлення — наприклад:\n\n"
            "> *«Мені потрібна преміальна коробка для колекційної настільної гри "
            "тираж 1000 шт., з колодою 110 карт і правилами. "
            "Дедлайн — 30 днів»*",
        )

    # Chat history
    chat_container = st.container(height=450)
    with chat_container:
        _render_chat()

    # ── Human-in-the-loop expert panel ────────────────────────────────────
    if st.session_state["awaiting_human"]:
        st.warning("⏸️ **Система очікує відповіді технолога-експерта**")
        graph_state = st.session_state.get("graph_state") or {}
        ambiguities = graph_state.get("ambiguities", [])
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
                _add_message("user", f"[Експерт]: {expert_input}", "HumanExpert")
                st.session_state["agent_steps"]["HumanExpert"] = "done"
                st.session_state["awaiting_human"] = False
                _run_graph(human_feedback=expert_input)
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
                _add_message("user", user_input)
                with st.spinner("Агенти обробляють запит…"):
                    _run_graph(user_input=user_input)
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


# ────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — Info panel
# ────────────────────────────────────────────────────────────────────────────
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
        st.markdown('<div class="section-title">📦 Компоненти продукту</div>',
                    unsafe_allow_html=True)
        for comp in components:
            with st.expander(f"📌 {comp.get('name', comp.get('id', '—'))}", expanded=False):
                st.json(comp, expanded=False)

    # ── Production routes table ───────────────────────────────────────────
    routes = st.session_state["production_routes"]
    if routes:
        st.markdown('<div class="section-title">🔧 Технологічні маршрути</div>',
                    unsafe_allow_html=True)
        import pandas as pd

        for route in routes:
            comp_label = route.get("component_name", route.get("component_id", "Компонент"))
            ops = route.get("operations", [])
            if ops:
                rows = []
                for op in ops:
                    rows.append({
                        "№": op.get("step", ""),
                        "Операція": op.get("operation_name", op.get("operation_id", "")),
                        "Обладнання": op.get("machine") or "—",
                        "Примітки": op.get("notes") or "—",
                    })
                df = pd.DataFrame(rows)
                st.markdown(f"**{comp_label}**")
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Cost estimates ────────────────────────────────────────────────────
    cost_est = st.session_state["cost_estimates"]
    if cost_est:
        st.markdown('<div class="section-title">💰 Калькуляція вартості</div>',
                    unsafe_allow_html=True)
        tiers = cost_est.get("tiers", {})
        if tiers:
            import pandas as pd
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
        st.markdown('<div class="section-title">📥 Документи</div>', unsafe_allow_html=True)
        wo = st.session_state.get("work_order", {})
        order_no = wo.get("order_number", "work_order") if wo else "work_order"
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
