from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from agents.conversational.llm_invoke import _invoke_llm
from agents.conversational.prompt import PROMPT
from agents.conversational.schema import (
    FieldSpec,
    _find_missing_fields,
    _format_missing_as_question,
    _repair_extraction_result,
)
from agents.conversational.tools import _extract_text_content, greeting_tool
from agents.llm_factory import get_llm_for_agent
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)
AGENT_NAME = "ConversationalAgent"
_GREETING_MESSAGES = {
    "привіт",
    "привіт!",
    "вітаю",
    "доброго дня",
    "добрий день",
    "добрий вечір",
    "hello",
    "hi",
}


def _next_llm_eval(state: ProductionState) -> dict[str, Any]:
    base = state.get("llm_eval") or {}
    return {
        "rows": list(base.get("rows", [])),
        "session_call_count": int(base.get("session_call_count", 0)),
    }


def _append_eval_row(
    llm_eval: dict[str, Any],
    result: dict[str, Any],
    invoke_meta: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "latency_ms": float(invoke_meta.get("latency_ms", 0.0)),
        "input_tokens": int(invoke_meta.get("input_tokens", 0)),
        "output_tokens": int(invoke_meta.get("output_tokens", 0)),
        "model": invoke_meta.get("model", "unknown"),
        "tier": invoke_meta.get("tier", "unknown"),
        "estimated": not bool(invoke_meta.get("usage_available", False)),
    }
    llm_eval["rows"].append(row)
    llm_eval["session_call_count"] += 1
    return llm_eval


def _build_tool_call(tool_name: str, prefix: str, args: dict[str, Any] | None = None) -> AIMessage:
    """Create an AIMessage that carries a single tool call with a unique id.

    Args:
        tool_name: The name of the tool to invoke.
        prefix: A human-readable prefix prepended to the UUID-based call id.
    """
    return AIMessage(
        content="",
        name=AGENT_NAME,
        tool_calls=[
            {
                "name": tool_name,
                "args": args or {},
                "id": f"{prefix}-{uuid4().hex}",
                "type": "tool_call",
            }
        ],
    )


def _should_use_greeting_tool(messages: list[Any]) -> bool:
    """Return True for short greeting-only openings in the latest user message."""
    if not messages:
        return False
    text = _extract_text_content(messages[-1]).strip().lower()
    return text in _GREETING_MESSAGES


def _render_game_components_catalog() -> str:
    """Render the game-components catalog as a Markdown block for follow-up questions.

    Pulled from the ``game_components`` table so the list stays in sync with
    seeding/migrations. Groups items by category and shows name, unit, price.
    Returns an empty string if the catalog is empty or the table is missing.
    """
    try:
        from db.repository import get_game_components
        rows = get_game_components()
    except Exception as error:
        logger.warning("Could not load game_components catalog: %s", error)
        return ""
    if not rows:
        return ""

    _CATEGORY_LABELS = {
        "dice": "Кубики",
        "meeple": "Міпли",
        "pawn": "Фішки",
        "token": "Жетони",
        "coin": "Монети",
        "tile": "Тайли",
        "timer": "Пісочний годинник",
        "dry_erase": "Dry-erase",
        "organizer": "Органайзер",
        "wrap": "Термоусадка",
    }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("category", "інше")), []).append(row)

    lines: list[str] = ["**Доступні комплектуючі з нашого каталогу:**", ""]
    for category, items in grouped.items():
        heading = _CATEGORY_LABELS.get(category, category.capitalize())
        lines.append(f"_{heading}:_")
        for item in items:
            price = item.get("price_uah")
            unit = item.get("unit", "")
            lines.append(f"- **{item.get('name', '')}** — {price} грн / {unit}")
        lines.append("")
    lines.append(
        "Напишіть, будь ласка, які позиції з цього переліку і в якій кількості вам потрібні "
        "(наприклад: *«кубики D6 — 1000 шт, міпли — 500 шт»*)."
    )
    return "\n".join(lines)


def _format_missing_with_catalog(missing: list[FieldSpec]) -> str:
    """Wrap ``_format_missing_as_question`` and embed the catalog when relevant.

    If ``game_components_notes`` is among the missing fields and will be shown
    in the current question block, the DB-backed catalog is rendered inline
    so the client can pick items directly without an extra turn.
    """
    base_question = _format_missing_as_question(missing)
    needs_catalog = any(spec.key == "game_components_notes" for spec in missing)
    if not needs_catalog:
        return base_question
    if "комплектуючі" not in base_question:
        return base_question
    catalog_block = _render_game_components_catalog()
    if not catalog_block:
        return base_question
    closing = "Дякую! Як тільки уточнимо — одразу рухаємось далі."
    enriched = base_question.replace(
        closing, f"{catalog_block}\n\n{closing}"
    )
    return enriched


def _merge_components(
    existing_components: list[dict[str, Any]], new_components: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge component lists by component id, preserving previously collected values."""
    merged: dict[str, dict[str, Any]] = {}

    for component in existing_components:
        if isinstance(component, dict) and component.get("id"):
            merged[component["id"]] = dict(component)

    for component in new_components:
        if not isinstance(component, dict):
            continue
        component_id = component.get("id")
        if not component_id:
            continue

        base = merged.get(component_id, {})
        merged[component_id] = {
            **base,
            **{k: v for k, v in component.items() if v is not None},
        }

    return list(merged.values())


def _merge_partial_data(
    existing_requirements: dict[str, Any],
    existing_components: list[dict[str, Any]],
    new_requirements: dict[str, Any],
    new_components: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge newly extracted data into previously collected requirements/components."""
    logger.debug(
        "Partial merge input: existing_requirements_keys=%s, existing_components=%d, "
        "new_requirements_keys=%s, new_components=%d",
        list(existing_requirements.keys()),
        len(existing_components),
        list(new_requirements.keys()),
        len(new_components),
    )
    merged_requirements = {
        **existing_requirements,
        **{k: v for k, v in new_requirements.items() if v is not None},
    }
    merged_components = _merge_components(existing_components, new_components)
    logger.debug(
        "Partial merge result: merged_requirements_keys=%s, merged_components=%d",
        list(merged_requirements.keys()),
        len(merged_components),
    )
    return merged_requirements, merged_components


def _known_data_system_message(
    known_requirements: dict[str, Any], known_components: list[dict[str, Any]]
) -> SystemMessage | None:
    """Build a system message with already known data to avoid repeated questions."""
    if not known_requirements and not known_components:
        return None

    lines: list[str] = [
        "═══════════════════════════════════════════",
        "ВЖЕ ЗІБРАНІ ДАНІ — НЕ ПЕРЕПИТУЙ ЦІ ПОЛЯ",
        "═══════════════════════════════════════════",
    ]

    if known_requirements:
        lines.append("\n📋 Загальні вимоги:")
        for key, value in known_requirements.items():
            lines.append(f"  • {key}: {value}")

    for component in known_components:
        comp_name = component.get("name", component.get("id", "компонент"))
        lines.append(f"\n📦 {comp_name}:")
        for key, value in component.items():
            if key not in ("id", "name", "type"):
                lines.append(f"  • {key}: {value}")

    lines += [
        "",
        "Використовуй ці дані як вже підтверджені.",
        "Повертай їх у відповіді (partial merge) і став лише нові уточнення.",
        "═══════════════════════════════════════════",
        "",
        f"JSON для merge:\n{json.dumps({'client_requirements': known_requirements, 'product_components': known_components}, ensure_ascii=False)}",
    ]

    return SystemMessage(content="\n".join(lines))



def conversational_agent_node(state: ProductionState) -> dict[str, Any]:
    """Main conversational node that collects client requirements.

    Dispatches to ``greeting_tool`` for bare greetings, otherwise invokes the
    LLM chain to extract or follow up on order requirements.  If the LLM
    claims the extraction is complete but Python-side validation finds missing
    fields, the node overrides the status and asks targeted follow-up questions.
    """
    logger.info(f"{AGENT_NAME}: Starting requirements extraction")
    logger.debug(f"Messages count: {len(state.get('messages', []))}")

    messages = state.get("messages", [])
    known_requirements = state.get("client_requirements", {}) or {}

    if _should_use_greeting_tool(messages):
        logger.info("Greeting branch selected. Triggering greeting_tool.")
        latest_user_text = _extract_text_content(messages[-1]) if messages else ""
        return {
            "current_agent": AGENT_NAME,
            "messages": [
                _build_tool_call(
                    greeting_tool.name,
                    "greeting",
                    args={"user_query": latest_user_text},
                )
            ],
            "client_requirements": {},
            "product_components": [],
            "llm_eval": _next_llm_eval(state),
        }

    llm = get_llm_for_agent("client_interface")

    logger.debug("Invoking LLM chain with structured output...")
    known_components = state.get("product_components", []) or []
    logger.info(
        "Known state before LLM: requirements_keys=%s, components=%d",
        list(known_requirements.keys()),
        len(known_components),
    )
    llm_messages = list(state["messages"])
    known_data_message = _known_data_system_message(known_requirements, known_components)
    if known_data_message:
        logger.debug("Injecting known-data system message for partial merge context.")
        llm_messages = [known_data_message, *llm_messages]

    try:
        llm_raw_result, invoke_meta = _invoke_llm(PROMPT, llm_messages, llm)
        result = _repair_extraction_result(llm_raw_result)
        logger.info(f"LLM response received: status={result.get('status')}")
        logger.info(f"Result: {result}")
        logger.debug(f"Result keys: {list(result.keys())}")
    except Exception as error:
        logger.error(f"Error in {AGENT_NAME} LLM call: {error}", exc_info=True)
        raise

    merged_requirements, merged_components = _merge_partial_data(
        known_requirements,
        known_components,
        result.get("client_requirements", {}),
        result.get("product_components", []),
    )
    result["client_requirements"] = merged_requirements
    result["product_components"] = merged_components

    updates: dict[str, Any] = {"current_agent": AGENT_NAME}
    llm_eval = _next_llm_eval(state)

    if result.get("status") == "complete":
        missing_fields = _find_missing_fields(result)
        llm_eval = _append_eval_row(llm_eval, result, invoke_meta)
        logger.info("Status=complete, missing_fields_count=%d", len(missing_fields))

        if missing_fields:
            logger.warning(
                f"LLM returned 'complete' but {len(missing_fields)} fields missing: {missing_fields}"
            )
            llm_question = result.get("follow_up_question", "")
            question = llm_question.strip() if llm_question and llm_question.strip() else _format_missing_with_catalog(missing_fields)
            if not (llm_question and llm_question.strip()):
                logger.warning("LLM marked complete prematurely and gave no follow_up_question — Python fallback")
            updates["messages"] = [AIMessage(content=question, name=AGENT_NAME)]
            updates["client_requirements"] = merged_requirements
            updates["product_components"] = merged_components
            updates["requirements_complete"] = False
        else:
            logger.info("Requirements extraction complete (Python validation passed)")
            components = merged_components
            logger.info(f"Extracted {len(components)} product components")
            updates["client_requirements"] = merged_requirements
            updates["product_components"] = components
            updates["requirements_complete"] = True
            updates["messages"] = [
                AIMessage(
                    content=(
                        "Вимоги зафіксовані. Передаю технологу для формування маршруту.\n"
                        f"Компоненти: {', '.join(component['name'] for component in components)}"
                    ),
                    name=AGENT_NAME,
                )
            ]
    else:
        missing_fields = _find_missing_fields(result)
        llm_eval = _append_eval_row(llm_eval, result, invoke_meta)
        logger.info("Status=incomplete, missing_fields_count=%d", len(missing_fields))
        llm_question = result.get("follow_up_question", "")
        if missing_fields:
            question = _format_missing_with_catalog(missing_fields)
            logger.info("Using Python follow-up from missing fields")
            if llm_question and llm_question.strip():
                logger.debug("Ignoring LLM follow_up_question because missing_fields are present")
        elif llm_question and llm_question.strip():
            question = llm_question.strip()
            logger.info("Using LLM follow_up_question")
        else:
            question = "Будь ласка, уточніть деталі замовлення."
            logger.warning("No follow_up_question and no missing_fields — generic fallback")
        logger.debug("Follow-up question preview: %s", question[:500])
        updates["messages"] = [AIMessage(content=question, name=AGENT_NAME)]
        updates["client_requirements"] = merged_requirements
        updates["product_components"] = merged_components
        updates["requirements_complete"] = False

    updates["llm_eval"] = llm_eval
    logger.debug(f"{AGENT_NAME} updates: {list(updates.keys())}")
    return updates


def route_after_conversational_manager(state: ProductionState) -> Literal["tools", "__end__"]:
    """Route to the tools node if the last message carries tool calls, otherwise end."""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and getattr(messages[-1], "tool_calls", None):
        return "tools"
    return "__end__"


def conversational_tool_response_node(state: ProductionState) -> dict[str, Any]:
    """Unwrap the last ToolMessage and re-emit its content as a plain AIMessage.

    This bridges the LangGraph tools node back into the conversation flow so
    that the tool response is visible to the client interface.
    """
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[-1], ToolMessage):
        return {"current_agent": AGENT_NAME}

    return {
        "current_agent": AGENT_NAME,
        "messages": [AIMessage(content=messages[-1].content, name=AGENT_NAME)],
        "client_requirements": {},
        "product_components": [],
    }
