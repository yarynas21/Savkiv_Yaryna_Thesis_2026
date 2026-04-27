"""
Right-column information panels: progress bar, components list, routes
table, cost card and Excel download button.

Everything is read-only: panels never mutate state, the view is responsible
for passing in the latest payload.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st



def progress_bar(percent: int, *, label: str = "📊 Прогрес замовлення") -> None:
    percent = max(0, min(100, int(percent)))
    st.markdown(
        f"""
        <div class="progress-wrap">
            <div class="progress-label">{label}</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width:{percent}%"></div>
            </div>
            <div class="progress-pct">{percent}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_components(components: Iterable[dict]) -> None:
    components = list(components)
    if not components:
        return
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



def render_routes(routes: Iterable[dict]) -> None:
    routes = list(routes)
    if not routes:
        return
    st.markdown('<div class="section-title">🔧 Технологічні маршрути</div>', unsafe_allow_html=True)
    for route in routes:
        comp_label = route.get("component_name", route.get("component_id", "Компонент"))
        ops = route.get("operations", [])
        if not ops:
            continue
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



def render_cost_estimates(cost_est: dict | None) -> None:
    if not cost_est:
        return
    st.markdown('<div class="section-title">💰 Калькуляція вартості</div>', unsafe_allow_html=True)

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



def excel_download(
    excel_bytes: bytes | None,
    *,
    file_name: str = "work_order",
    button_key: str | None = None,
) -> None:
    if not excel_bytes:
        return
    st.markdown('<div class="section-title">📥 Документи</div>', unsafe_allow_html=True)
    st.download_button(
        label="⬇️ Завантажити Технічне Завдання (Excel)",
        data=excel_bytes,
        file_name=f"{file_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
        key=button_key,
    )
