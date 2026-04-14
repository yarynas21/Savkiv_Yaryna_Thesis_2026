"""
ConversationalAgent
======================
Responsible for "intellectual discovery of requirements":
- Engages in dynamic dialogue with the client
- Extracts and structures product specifications from natural language
- Returns a filled `client_requirements` dict and a list of `product_components`

Hybrid approach:
- LLM drives the conversation and extracts values naturally
- Python deterministically validates completeness before allowing "complete"
- If LLM says "complete" but fields are missing, Python overrides and asks the missing ones
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm_for_agent
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)
AGENT_NAME = "ConversationalAgent"


# ---------------------------------------------------------------------------
# Deterministic checklist
# ---------------------------------------------------------------------------

# Required fields per component — Python checks these, not LLM
REQUIRED_BOX_FIELDS = [
    "size_mm",
    "construction",
    "print_sides",
    "material",
    "board_thickness_mm",
    "lamination",
    "uv_varnish",
    "shrink_wrap",
]

REQUIRED_CARD_FIELDS = [
    "card_size_mm",
    "gsm",
    "print_colors",
    "front_finish",
    "back_finish",
    "shrink_wrap",
]

REQUIRED_RULEBOOK_FIELDS = [
    "size_mm",
    "pages",
    "binding",
]

REQUIRED_GENERAL_FIELDS = [
    "has_game_components",
    "has_additional_elements",
]

# Human-readable labels for missing fields (used when Python overrides LLM)
FIELD_LABELS = {
    # general
    "has_game_components": "Чи є комплектуючі (кубики, фішки, пісочний годинник тощо)?",
    "has_additional_elements": "Чи є додаткові елементи (ігрове поле, листівка тощо)?",
    # box
    "box.size_mm": "Розмір коробки — довжина × ширина × висота (мм)?",
    "box.construction": "Конструктив коробки: кришка і дно / дно і рукав / самозбірна?",
    "box.print_sides": "Друк лише зовні коробки чи також і всередині?",
    "box.material": "Основа коробки — гофра чи палітурний картон?",
    "box.board_thickness_mm": "Товщина палітурного картону (1.5 мм / 2.0 мм / порекомендуй)?",
    "box.lamination": "Ламінація коробки — глянцева чи матова?",
    "box.uv_varnish": "Чи потрібне УФ-лакування на коробці? Якщо так — які елементи?",
    "box.shrink_wrap": "Чи потрібне термопакування коробки?",
    # cards
    "cards.card_size_mm": "Розмір карти — довжина × ширина (мм)?",
    "cards.gsm": "Граматура/товщина матеріалу карт (наприклад 300 gsm)?",
    "cards.print_colors": "Колірність друку карт з двох сторін (наприклад 4+4)?",
    "cards.front_finish": "Покриття лицьової сторони карт (глянцева/матова ламінація, УФ-лак, без покриття)?",
    "cards.back_finish": "Покриття зворотньої сторони карт (глянцева/матова ламінація, УФ-лак, без покриття)?",
    "cards.shrink_wrap": "Чи потрібне термопакування карт?",
    # rulebook
    "rulebook.size_mm": "Розмір інструкції — довжина × ширина (мм)?",
    "rulebook.pages": "Кількість сторінок інструкції?",
    "rulebook.binding": "Кріплення інструкції: на скорбу чи фальцювання (згин)?",
}

class ClientExtractionOutput(BaseModel):
    """Structured output contract for conversational requirements extraction."""

    status: str = Field(description="Either 'complete' or 'incomplete'")
    client_requirements: dict[str, Any] = Field(default_factory=dict)
    product_components: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_question: str | None = Field(default=None)


def _find_missing_fields(result: dict) -> list[str]:
    """
    Deterministically checks which required fields are missing in the LLM result.
    Returns list of field keys like "box.size_mm", "cards.gsm", etc.
    """
    missing = []

    req = result.get("client_requirements", {})
    for field in REQUIRED_GENERAL_FIELDS:
        if req.get(field) is None:
            missing.append(field)

    components = {c["id"]: c for c in result.get("product_components", [])}

    box = components.get("rigid_box", {})
    for field in REQUIRED_BOX_FIELDS:
        if box.get(field) is None:
            missing.append(f"box.{field}")

    cards = components.get("card_deck", {})
    for field in REQUIRED_CARD_FIELDS:
        if cards.get(field) is None:
            missing.append(f"cards.{field}")

    rulebook = components.get("rulebook", {})
    for field in REQUIRED_RULEBOOK_FIELDS:
        if rulebook.get(field) is None:
            missing.append(f"rulebook.{field}")

    return missing


def _format_missing_as_question(missing_fields: list[str]) -> str:
    """Format missing fields as a question block for the client."""
    lines = ["Ще кілька уточнень:\n"]
    for i, key in enumerate(missing_fields, 1):
        label = FIELD_LABELS.get(key, key)
        lines.append(f"{i}. {label}")
    return "\n".join(lines)


def _repair_extraction_result(result: Any) -> dict[str, Any]:
    """
    Lightweight JSON repair/sanitization in case model output shape drifts.
    Ensures required keys exist and have expected container types.
    """
    if not isinstance(result, dict):
        result = {}

    repaired: dict[str, Any] = {
        "status": result.get("status", "incomplete"),
        "client_requirements": result.get("client_requirements") or {},
        "product_components": result.get("product_components") or [],
        "follow_up_question": result.get("follow_up_question"),
    }

    if repaired["status"] not in ("complete", "incomplete"):
        repaired["status"] = "incomplete"

    if not isinstance(repaired["client_requirements"], dict):
        repaired["client_requirements"] = {}
    if not isinstance(repaired["product_components"], list):
        repaired["product_components"] = []
    if repaired["follow_up_question"] is not None and not isinstance(
        repaired["follow_up_question"], str
    ):
        repaired["follow_up_question"] = str(repaired["follow_up_question"])

    return repaired


# ---------------------------------------------------------------------------
# System prompt — LLM drives conversation, Python validates completeness
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ти — менеджер з роботи з клієнтами у поліграфічній компанії Dyz-Art.
Твоя задача — зрозуміти, що саме потрібно замовнику, та структурувати вимоги для виробництва.

Продукція компанії: преміум-упаковка, коробки для настільних ігор, колоди карт, правила гри, вставки.

════════════════════════════════════════
ІНФОРМАЦІЯ ЯКУ ТРЕБА ЗІБРАТИ
════════════════════════════════════════

ЗАГАЛЬНЕ:
□ Наявність комплектуючих (пісочний годинник, кубики, фішки тощо)
□ Наявність додаткових елементів (ігрове поле, інформаційна листівка тощо)

КОРОБКА:
□ Розмір (довжина × ширина × висота, мм)
□ Конструктив: кришка і дно / дно і рукав / самозбірна
□ Друк: лише зовні або зовні та всередині
□ Основа: гофра або палітурний картон
□ Товщина палітурного картону (1.5 мм / 2.0 мм; якщо не знає — запропонуй 1.75 мм)
□ Ламінація: глянцева або матова (ціни різняться)
□ УФ-лакування: так/ні; якщо так — які елементи або яка площа
□ Термопакування коробки: так/ні

КАРТИ (110 карт):
□ Розмір карти (довжина × ширина, мм)
□ Граматура матеріалу (наприклад 300 gsm, 350 gsm)
□ Колірність друку з двох сторін (наприклад 4+4)
□ Покриття лицьової сторони (глянцева/матова ламінація / УФ-лак / без)
□ Покриття зворотньої сторони (глянцева/матова ламінація / УФ-лак / без)
□ Термопакування карт: так/ні

ІНСТРУКЦІЯ/ПРАВИЛА:
□ Розмір (довжина × ширина, мм)
□ Кількість сторінок
□ Кріплення: на скорбу або фальцювання (згин)

════════════════════════════════════════
ПРАВИЛА:
- Задавай питання БЛОКАМИ (всі питання одного компонента одразу).
- НЕ перепитуй те що вже відомо.
- Якщо клієнт не знає — запропонуй стандарт та запитай підтвердження.
════════════════════════════════════════

Якщо вся інформація зібрана — поверни JSON (без markdown):
{{
  "status": "complete",
  "client_requirements": {{
    "client_name": "...",
    "product_name": "...",
    "quantity": 1000,
    "language": "uk",
    "deadline_days": 30,
    "premium_finish": true,
    "has_game_components": true,
    "game_components_notes": "...",
    "has_additional_elements": false,
    "notes": "..."
  }},
  "product_components": [
    {{
      "id": "rigid_box",
      "name": "Коробка",
      "type": "rigid_box",
      "size_mm": [300, 200, 60],
      "quantity": 1000,
      "construction": "lid_and_base",
      "print_sides": "outside_only",
      "material": "bookbinding_board",
      "board_thickness_mm": 1.75,
      "lamination": "matte",
      "uv_varnish": true,
      "uv_varnish_elements": "логотип на кришці",
      "shrink_wrap": false
    }},
    {{
      "id": "card_deck",
      "name": "Колода карт",
      "type": "card_deck",
      "card_count": 110,
      "card_size_mm": [63, 88],
      "quantity": 1000,
      "gsm": 300,
      "print_colors": "4+4",
      "front_finish": "matte_lamination",
      "back_finish": "matte_lamination",
      "shrink_wrap": true
    }},
    {{
      "id": "rulebook",
      "name": "Правила гри",
      "type": "rulebook_thin",
      "size_mm": [210, 148],
      "quantity": 1000,
      "pages": 8,
      "binding": "saddle_stitch"
    }}
  ],
  "follow_up_question": null
}}

Якщо ще не вистачає інформації — поверни:
{{
  "status": "incomplete",
  "client_requirements": {{}},
  "product_components": [],
  "follow_up_question": "Питання до клієнта"
}}

Виводь ТІЛЬКИ валідний JSON, без пояснень та markdown.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def conversational_agent_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: ConversationalAgent.

    Flow:
    1. LLM extracts values and decides if ready (status complete/incomplete).
    2. Python validates: if LLM says "complete" but fields are missing → override.
    3. Only when Python confirms all fields present → signal readiness.
    """
    logger.info(f"{AGENT_NAME}: Starting requirements extraction")
    logger.debug(f"Messages count: {len(state.get('messages', []))}")

    llm = get_llm_for_agent("client_interface")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    logger.debug("Invoking LLM chain with structured output...")

    try:
        # Primary path: native structured output, fallback to robust JSON parser.
        try:
            structured_llm = llm.with_structured_output(ClientExtractionOutput)
            chain = prompt | structured_llm
            raw = chain.invoke({"messages": state["messages"]})
            if isinstance(raw, ClientExtractionOutput):
                result = raw.model_dump()
            else:
                result = raw
        except Exception:
            chain = prompt | llm | RobustJsonOutputParser()
            result = chain.invoke({"messages": state["messages"]})
        result = _repair_extraction_result(result)
        logger.info(f"LLM response received: status={result.get('status')}")
        logger.debug(f"Result keys: {list(result.keys())}")
    except Exception as e:
        logger.error(f"Error in {AGENT_NAME} LLM call: {e}", exc_info=True)
        raise

    updates: dict[str, Any] = {"current_agent": AGENT_NAME}

    if result.get("status") == "complete":
        # Python deterministically validates completeness
        missing_fields = _find_missing_fields(result)

        if missing_fields:
            # LLM thought it was done, but fields are missing — override
            logger.warning(
                f"LLM returned 'complete' but {len(missing_fields)} fields missing: {missing_fields}"
            )
            question = _format_missing_as_question(missing_fields)
            updates["messages"] = [
                AIMessage(content=question, name=AGENT_NAME)
            ]
            updates["client_requirements"] = {}
            updates["product_components"] = []
        else:
            # All fields confirmed present — truly complete
            logger.info("Requirements extraction complete (Python validation passed)")
            components = result.get("product_components", [])
            logger.info(f"Extracted {len(components)} product components")
            updates["client_requirements"] = result.get("client_requirements", {})
            updates["product_components"] = components
            updates["messages"] = [
                AIMessage(
                    content=(
                        "Вимоги зафіксовані. Передаю технологу для формування маршруту.\n"
                        f"Компоненти: {', '.join(c['name'] for c in components)}"
                    ),
                    name=AGENT_NAME,
                )
            ]
    else:
        # LLM says incomplete — ask its follow-up question
        question = result.get("follow_up_question", "Будь ласка, уточніть деталі замовлення.")
        logger.info("Requirements incomplete (LLM), asking follow-up question")
        updates["messages"] = [
            AIMessage(content=question, name=AGENT_NAME)
        ]
        updates["client_requirements"] = {}
        updates["product_components"] = []

    logger.debug(f"{AGENT_NAME} updates: {list(updates.keys())}")
    return updates
