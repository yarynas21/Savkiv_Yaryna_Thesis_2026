"""
Admin view — data-editor tabs + LLM controls + metrics dashboard.

Save / Add / Delete all go through the admin-scoped ``/api/admin/*``
endpoints. A single "Зберегти зміни" button diffs the edited DataFrame
against the loaded snapshot, so editors don't need to click per-row.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from api_client import api
from common import header

_MODEL_OPTIONS = {
    "GPT-4o (OpenAI)": {"provider": "openai", "model": "gpt-4o"},
    "Sonnet 4.6 (Anthropic)": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
}

_MODEL_DISPLAY_NAMES = {
    ("openai", "gpt-4o"): "GPT-4o (OpenAI)",
    ("anthropic", "claude-sonnet-4-6"): "Sonnet 4.6 (Anthropic)",
}


def _human_model_name(model_raw: str) -> str:
    model = str(model_raw or "").strip()
    if model == "gpt-4o":
        return "GPT-4o (OpenAI)"
    if model in {"claude-sonnet-4-6", "claude-sonnet-4"}:
        return "Sonnet 4.6 (Anthropic)"
    return model



def _to_df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def _diff_rows(
    original: pd.DataFrame,
    edited: pd.DataFrame,
    key_columns: list[str],
) -> tuple[list[dict], list[dict], list[tuple]]:
    """Return ``(to_upsert_new, to_upsert_changed, to_delete_keys)``."""
    if original.empty:
        original_keys: set[tuple] = set()
    else:
        original_keys = {tuple(row) for row in original[key_columns].itertuples(index=False)}
    edited_keys = set()
    new_rows: list[dict] = []
    changed_rows: list[dict] = []
    for _, row in edited.iterrows():
        key = tuple(row[col] for col in key_columns)
        if any(pd.isna(v) or v == "" for v in key):
            continue
        edited_keys.add(key)
        payload = row.to_dict()
        if key not in original_keys:
            new_rows.append(payload)
        else:
            orig_row = original.loc[
                (original[key_columns] == pd.Series(dict(zip(key_columns, key)))).all(axis=1)
            ]
            if not orig_row.empty and orig_row.iloc[0].to_dict() != payload:
                changed_rows.append(payload)

    to_delete = list(original_keys - edited_keys)
    return new_rows, changed_rows, to_delete


# Tab: game_components

_COMPONENT_COLUMNS = ["id", "name", "category", "unit", "price_uah", "notes"]


def _tab_components() -> None:
    rows = api("GET", "/api/admin/game_components") or []
    original = _to_df(rows, _COMPONENT_COLUMNS)

    st.caption("Каталог компонентів настільних ігор та їхні ціни (UAH).")
    edited = st.data_editor(
        original,
        num_rows="dynamic",
        use_container_width=True,
        key="admin_components_editor",
        column_config={
            "id":        st.column_config.TextColumn("ID", width="small", required=True),
            "name":      st.column_config.TextColumn("Назва", required=True),
            "category":  st.column_config.TextColumn("Категорія", width="small", required=True),
            "unit":      st.column_config.TextColumn("Одиниця", width="small", required=True),
            "price_uah": st.column_config.NumberColumn("Ціна, ₴", format="%.2f", required=True),
            "notes":     st.column_config.TextColumn("Примітки"),
        },
    )

    if st.button("💾 Зберегти зміни", key="save_components", type="primary"):
        new_rows, changed_rows, to_delete = _diff_rows(original, edited, ["id"])
        with st.spinner("Зберігаємо..."):
            _persist(
                new_rows, changed_rows, to_delete,
                create_path="/api/admin/game_components",
                update_path=lambda r: f"/api/admin/game_components/{r['id']}",
                delete_path=lambda key: f"/api/admin/game_components/{key[0]}",
            )


# Tab: cost_rates

_COST_COLUMNS = ["category", "rate_key", "value_numeric", "unit", "notes"]


def _tab_cost_rates() -> None:
    rows = api("GET", "/api/admin/cost_rates") or []
    original = _to_df(rows, _COST_COLUMNS)

    st.caption(
        "Тарифи калькулятора вартості. Ключ рядка — пара (category, rate_key). "
        "Зміни застосовуються до наступного запуску графа."
    )
    edited = st.data_editor(
        original,
        num_rows="dynamic",
        use_container_width=True,
        key="admin_cost_rates_editor",
        column_config={
            "category":      st.column_config.TextColumn("Категорія", required=True),
            "rate_key":      st.column_config.TextColumn("Ключ", required=True),
            "value_numeric": st.column_config.NumberColumn("Значення", required=True, format="%.6f"),
            "unit":          st.column_config.TextColumn("Одиниця", width="small"),
            "notes":         st.column_config.TextColumn("Примітки"),
        },
    )

    if st.button("💾 Зберегти зміни", key="save_cost_rates", type="primary"):
        new_rows, changed_rows, to_delete = _diff_rows(
            original, edited, ["category", "rate_key"]
        )
        with st.spinner("Зберігаємо..."):
            _persist(
                new_rows, changed_rows, to_delete,
                create_path="/api/admin/cost_rates",
                update_path=lambda r: f"/api/admin/cost_rates/{r['category']}/{r['rate_key']}",
                delete_path=lambda key: f"/api/admin/cost_rates/{key[0]}/{key[1]}",
            )


# Tab: materials (papers table)

_PAPER_COLUMNS = [
    "id", "name", "type", "weight_gsm", "thickness_mm",
    "compatible_with", "typical_use",
]


def _tab_papers() -> None:
    rows = api("GET", "/api/admin/papers") or []
    original = _to_df(rows, _PAPER_COLUMNS)
    editor_df = original.copy()
    # Streamlit data_editor can't edit list-typed cells as TextColumn directly.
    # Show these fields as comma-separated strings in the UI, then parse back.
    for col in ("compatible_with", "typical_use"):
        editor_df[col] = editor_df[col].apply(
            lambda v: ", ".join(_ensure_list(v))
        )

    st.caption(
        "Каталог матеріалів. Поля `compatible_with` та `typical_use` приймають "
        "списки рядків — розділяйте комами при редагуванні."
    )

    edited = st.data_editor(
        editor_df,
        num_rows="dynamic",
        use_container_width=True,
        key="admin_papers_editor",
        column_config={
            "id":               st.column_config.TextColumn("ID", required=True),
            "name":             st.column_config.TextColumn("Назва", required=True),
            "type":             st.column_config.TextColumn("Тип", required=True),
            "weight_gsm":       st.column_config.NumberColumn("г/м²", required=True),
            "thickness_mm":     st.column_config.NumberColumn("Товщина, мм", format="%.3f"),
            "compatible_with":  st.column_config.TextColumn("Сумісність"),
            "typical_use":      st.column_config.TextColumn("Застосування"),
        },
    )

    if st.button("💾 Зберегти зміни", key="save_papers", type="primary"):
        original = original.copy()
        edited = edited.copy()
        for col in ("compatible_with", "typical_use"):
            original[col] = original[col].apply(_ensure_list)
            edited[col] = edited[col].apply(_ensure_list)
        new_rows, changed_rows, to_delete = _diff_rows(original, edited, ["id"])
        with st.spinner("Зберігаємо..."):
            _persist(
                new_rows, changed_rows, to_delete,
                create_path="/api/admin/papers",
                update_path=lambda r: f"/api/admin/papers/{r['id']}",
                delete_path=lambda key: f"/api/admin/papers/{key[0]}",
            )


def _ensure_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value)]


# Tab: users

_USER_EDIT_COLUMNS = ["id", "username", "email", "role", "is_active"]


def _tab_users() -> None:
    rows = api("GET", "/api/admin/users") or []
    df = pd.DataFrame(rows, columns=_USER_EDIT_COLUMNS + ["created_at"])
    st.caption("Редагуйте тільки `role` та `is_active`. Для нових користувачів використовуйте форму нижче.")

    edited = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        key="admin_users_editor",
        column_config={
            "id":         st.column_config.TextColumn("ID", disabled=True),
            "username":   st.column_config.TextColumn("Логін", disabled=True),
            "email":      st.column_config.TextColumn("Email", disabled=True),
            "role":       st.column_config.SelectboxColumn(
                "Роль", options=["admin", "client", "expert"], required=True
            ),
            "is_active":  st.column_config.CheckboxColumn("Активний"),
            "created_at": st.column_config.DatetimeColumn("Створено", disabled=True),
        },
    )

    if st.button("💾 Зберегти зміни", key="save_users", type="primary"):
        with st.spinner("Зберігаємо..."):
            for _, new in edited.iterrows():
                old_series = df.loc[df["id"] == new["id"]]
                if old_series.empty:
                    continue
                old = old_series.iloc[0]
                payload: dict = {}
                if new["role"] != old["role"]:
                    payload["role"] = new["role"]
                if bool(new["is_active"]) != bool(old["is_active"]):
                    payload["is_active"] = bool(new["is_active"])
                if payload:
                    api("PATCH", f"/api/admin/users/{new['id']}", json=payload)
        st.toast("Користувачів оновлено.", icon="✅")
        st.rerun()

    st.divider()
    st.markdown("**Додати користувача**")
    with st.form("admin_new_user"):
        email = st.text_input("Email")
        username = st.text_input("Логін")
        password = st.text_input("Пароль", type="password")
        role = st.selectbox("Роль", ["client", "expert", "admin"], index=0)
        is_active = st.checkbox("Активний", value=True)
        submitted = st.form_submit_button("Створити", use_container_width=True, type="primary")
        if submitted:
            if not email or not username or not password:
                st.error("Заповніть email, логін і пароль.")
            else:
                api(
                    "POST", "/api/admin/users",
                    json={
                        "email": email, "username": username, "password": password,
                        "role": role, "is_active": is_active,
                    },
                )
                st.rerun()



def _tab_llm_runtime() -> None:
    st.caption(
        "Глобальний вибір LLM для всіх агентів (conversation/technologist/validation/generation). "
        "Зміни зберігаються в БД і діють, поки адміністратор не змінить налаштування знову."
    )
    current = api("GET", "/api/admin/llm/runtime") or {}
    current_provider = str(current.get("provider", "openai"))
    current_model = str(current.get("model", "gpt-4o"))

    selected_label = "GPT-4o (OpenAI)"
    for label, payload in _MODEL_OPTIONS.items():
        if payload["provider"] == current_provider and payload["model"] == current_model:
            selected_label = label
            break

    chosen = st.radio(
        "Активна модель",
        list(_MODEL_OPTIONS.keys()),
        index=list(_MODEL_OPTIONS.keys()).index(selected_label),
        horizontal=False,
        key="admin_llm_runtime_selector",
    )

    current_human = _MODEL_DISPLAY_NAMES.get(
        (current_provider, current_model),
        f"{current_provider} / {current_model}",
    )
    st.text(f"Поточна модель: {current_human}")
    if current.get("updated_at"):
        st.caption(f"Оновлено: {current.get('updated_at')}")

    if st.button("💾 Зберегти модель", key="save_llm_runtime", type="primary"):
        payload = _MODEL_OPTIONS[chosen]
        with st.spinner("Оновлюємо модель..."):
            result = api("PUT", "/api/admin/llm/runtime", json=payload)
        if result is not None:
            st.toast(f"Активна модель: {chosen}", icon="🤖")
            st.rerun()



def _tab_metrics_dashboard() -> None:
    st.caption("Операційні метрики LLM-сесій: вартість, latency, виклики та розподіл по моделях.")
    overview = api("GET", "/api/metrics/overview")
    if not overview:
        st.info("Ще немає даних для дашборду. Запустіть хоча б одну сесію.")
        return

    core = overview.get("core") or {}
    latency = overview.get("latency") or {}
    cost = overview.get("cost") or {}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Сесій", int(overview.get("sessions_total", 0)))
    c2.metric("LLM викликів", int(overview.get("calls_total", 0)))
    c3.metric("Вартість LLM (USD)", f"{float(cost.get('total_cost_usd', 0.0)):.4f}")
    c4.metric("Час агентів (хв)", f"{float(core.get('agent_processing_total_min', 0.0)):.3f}")

    st.divider()
    l1, l2 = st.columns(2)
    l1.metric("Latency p50 (хв)", f"{float(latency.get('latency_p50_min', 0.0)):.4f}")
    l2.metric("Latency p95 (хв)", f"{float(latency.get('latency_p95_min', 0.0)):.4f}")

    by_model = overview.get("by_model") or []
    if by_model:
        st.subheader("По моделях")
        by_model_df = pd.DataFrame(by_model)
        if "model" in by_model_df.columns:
            by_model_df["model"] = by_model_df["model"].apply(_human_model_name)

        table_cols = [
            "model",
            "calls_total",
            "input_tokens_total",
            "output_tokens_total",
            "latency_total_ms",
            "total_cost_usd",
        ]
        present_cols = [c for c in table_cols if c in by_model_df.columns]
        rename_map = {
            "model": "Модель",
            "calls_total": "К-сть викликів",
            "input_tokens_total": "Вхідні токени",
            "output_tokens_total": "Вихідні токени",
            "latency_total_ms": "Загальний latency, мс",
            "total_cost_usd": "Вартість, USD",
        }
        st.dataframe(
            by_model_df[present_cols].rename(columns=rename_map),
            use_container_width=True,
        )

        g1, g2 = st.columns(2)
        if {"model", "total_cost_usd"}.issubset(by_model_df.columns):
            g1.bar_chart(by_model_df.set_index("model")[["total_cost_usd"]], use_container_width=True)
        if {"model", "calls_total"}.issubset(by_model_df.columns):
            g2.bar_chart(by_model_df.set_index("model")[["calls_total"]], use_container_width=True)
    else:
        st.info("Немає агрегованих даних `by_model`.")

    per_session_cost = overview.get("per_session_cost") or []
    if per_session_cost:
        st.subheader("Вартість по сесіях")
        ps_df = pd.DataFrame(per_session_cost)
        if {"thread_id", "total_cost_usd"}.issubset(ps_df.columns):
            st.dataframe(
                ps_df.rename(columns={"thread_id": "Сесія", "total_cost_usd": "Вартість, USD"}),
                use_container_width=True,
            )
            st.bar_chart(ps_df.set_index("thread_id")[["total_cost_usd"]], use_container_width=True)



def _persist(
    new_rows: list[dict],
    changed_rows: list[dict],
    to_delete: list[tuple],
    *,
    create_path: str,
    update_path: Callable[[dict], str],
    delete_path: Callable[[tuple], str],
) -> None:
    errors = 0
    for row in new_rows:
        if api("POST", create_path, json=row) is None:
            errors += 1
    for row in changed_rows:
        if api("PUT", update_path(row), json=row) is None:
            errors += 1
    for key in to_delete:
        if api("DELETE", delete_path(key)) is None:
            errors += 1
    if errors:
        st.warning(f"{errors} операцій завершилися з помилкою.")
    else:
        st.toast(
            f"Застосовано: {len(new_rows)} додано, {len(changed_rows)} оновлено, "
            f"{len(to_delete)} видалено.",
            icon="✅",
        )
    st.rerun()



def render() -> None:
    header.render(subtitle="Адміністрування бази знань та користувачів")

    tab_comp, tab_rates, tab_papers, tab_users, tab_llm, tab_metrics = st.tabs(
        ["🎲 Компоненти", "💰 Cost rates", "📄 Матеріали", "👥 Користувачі", "🤖 LLM", "📊 Метрики"]
    )
    with tab_comp:
        _tab_components()
    with tab_rates:
        _tab_cost_rates()
    with tab_papers:
        _tab_papers()
    with tab_users:
        _tab_users()
    with tab_llm:
        _tab_llm_runtime()
    with tab_metrics:
        _tab_metrics_dashboard()
