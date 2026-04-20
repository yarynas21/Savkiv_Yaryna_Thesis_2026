from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from agents.conversational.prompt import _GREETING_SYSTEM_PROMPT
from agents.llm_factory import get_llm_for_agent

_GREETING_FALLBACK = "Вітаю! Яка інформація вам потрібна для замовлення?"

_COMPONENTS_SUGGESTER_PROMPT = """Ти — консультант поліграфічної компанії Dyz-Art, який допомагає обрати
комплектуючі для настільної гри з наявного каталогу.

Нижче — повний каталог закупних комплектуючих у форматі pipe-CSV:
  id | name | category | unit | price_uah

Відповідай ЛИШЕ на основі цих даних — нічого не вигадуй, не додавай позицій поза каталогом,
не вигадуй знижок і не рахуй сумарну вартість (це зробимо пізніше).

Правила відповіді:
- Якщо клієнт згадав конкретну категорію (кубики/фішки/жетони/пісочний годинник тощо) —
  покажи ЛИШЕ позиції цієї категорії та 1-2 суміжні, які логічно поєднуються.
- Якщо клієнт не конкретизував — покажи весь каталог, згрупований за категоріями.
- Формат — Markdown:
  ### Комплектуючі
  **Категорія**
  - **Назва** — X грн / одиниця
- Заверши запрошенням: *«Які позиції і в якій кількості додати у замовлення?»*
- Українською, коротко, без JSON, без markdown-таблиць.
"""


def _format_catalog_fallback(rows: list[dict[str, Any]]) -> str:
    """Deterministic Markdown fallback used when the LLM call fails."""
    lines = ["### Комплектуючі"]
    for row in rows:
        lines.append(f"- **{row['name']}** — {row['price_uah']} грн / {row['unit']}")
    lines.append("")
    lines.append("*Які позиції і в якій кількості додати у замовлення?*")
    return "\n".join(lines)


def _extract_text_content(message: Any) -> str:
    """Extract plain text from a LangChain message regardless of content shape.

    Handles three content formats:
    - str: returned as-is after stripping whitespace.
    - list: each dict item with ``type == "text"`` is joined into a single string.
    - other: coerced to str.
    """
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            part.get("text", "").strip()
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return " ".join(part for part in text_parts if part)
    return str(content).strip()


@tool("greeting_tool")
def greeting_tool(user_query: str = "") -> str:
    """Return an onboarding greeting for a user greeting query."""
    try:
        llm = get_llm_for_agent("client_interface")
        result = llm.invoke([
            SystemMessage(content=_GREETING_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Клієнт написав привітання. Сформуй відповідь на основі його повідомлення:\n"
                    f"{user_query}"
                )
            ),
        ])
        return result.content if hasattr(result, "content") else str(result)
    except Exception:
        return _GREETING_FALLBACK


@tool("game_components_catalog_tool")
def game_components_catalog_tool(user_query: str = "") -> str:
    """Suggest purchasable board-game components from the catalog.

    Call whenever the client says they need game components — even if they
    only named a category like "кубики" or "фішки" without specific items.
    The tool loads the catalog from the DB and uses an LLM to return a
    Markdown suggestion filtered to the client's intent. Pass the client's
    original phrase about components as ``user_query``.
    """
    from db.repository import get_game_components

    rows = get_game_components()
    if not rows:
        return (
            "Каталог комплектуючих поки що порожній — уточніть, будь ласка, "
            "які саме позиції потрібні, і я зафіксую їх у замовленні."
        )

    catalog_csv = "\n".join(
        f"{r['id']} | {r['name']} | {r['category']} | {r['unit']} | {r['price_uah']}"
        for r in rows
    )

    try:
        llm = get_llm_for_agent("client_interface")
        result = llm.invoke([
            SystemMessage(
                content=(
                    f"{_COMPONENTS_SUGGESTER_PROMPT}\n\nКаталог:\n{catalog_csv}"
                )
            ),
            HumanMessage(
                content=(
                    "Клієнт написав про комплектуючі:\n"
                    f"{user_query or '(без уточнення — покажи весь каталог)'}"
                )
            ),
        ])
        content = result.content if hasattr(result, "content") else str(result)
        if isinstance(content, str) and content.strip():
            return content
        return _format_catalog_fallback(rows)
    except Exception:
        return _format_catalog_fallback(rows)
