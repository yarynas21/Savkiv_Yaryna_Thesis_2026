"""
Client Interface Agent
======================
Responsible for "intellectual discovery of requirements":
- Engages in dynamic dialogue with the client
- Extracts and structures product specifications from natural language
- Returns a filled `client_requirements` dict and a list of `product_components`

If the conversation does not yet contain enough information, the agent asks
follow-up questions (returned as an AI message). The workflow loop continues
until requirements are sufficiently complete.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ти — менеджер з роботи з клієнтами у поліграфічній компанії Dyz-Art.
Твоя задача — зрозуміти, що саме потрібно замовнику, та структурувати вимоги для виробництва.

Продукція компанії: преміум-упаковка, коробки для настільних ігор, колоди карт, правила гри, вставки.

Якщо запит зрозумілий — поверни JSON з такою структурою (без markdown-обгортки):
{{
  "status": "complete",
  "client_requirements": {{
    "client_name": "...",
    "product_name": "...",
    "quantity": 1000,
    "language": "uk",
    "deadline_days": 30,
    "premium_finish": true,
    "notes": "..."
  }},
  "product_components": [
    {{
      "id": "rigid_box",
      "name": "Жорстка коробка",
      "type": "rigid_box",
      "size_mm": [300, 200, 60],
      "quantity": 1000,
      "finish": "soft_touch_lamination",
      "special_effects": ["hot_foil_stamping"]
    }},
    {{
      "id": "card_deck",
      "name": "Колода карт",
      "type": "card_deck",
      "card_count": 110,
      "card_size_mm": [63, 88],
      "quantity": 1000,
      "finish": "uv_varnish",
      "special_effects": []
    }}
  ],
  "follow_up_question": null
}}

Якщо не вистачає деталей — поверни:
{{
  "status": "incomplete",
  "client_requirements": {{}},
  "product_components": [],
  "follow_up_question": "Яке питання задати замовнику?"
}}

ВАЖЛИВО:
- Виводь ТІЛЬКИ валідний JSON, без пояснень та markdown.
- Якщо замовник хоче преміум продукт (board game, collectible) — автоматично рекоменд: soft touch ламінацію, фольгування.
- Типи компонентів: rigid_box, folding_box, card_deck, rulebook_thin, rulebook_thick, insert.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def client_interface_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: Client Interface Agent.
    Processes conversation messages and extracts structured requirements.
    """
    logger.info("ClientInterfaceAgent: Starting requirements extraction")
    logger.debug(f"Messages count: {len(state.get('messages', []))}")
    
    llm = get_llm()
    logger.debug("LLM initialized")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm | RobustJsonOutputParser()
    logger.debug("Invoking LLM chain...")

    try:
        result: dict = chain.invoke({"messages": state["messages"]})
        logger.info(f"LLM response received: status={result.get('status')}")
        logger.debug(f"Result keys: {list(result.keys())}")
    except Exception as e:
        logger.error(f"Error in ClientInterfaceAgent LLM call: {e}", exc_info=True)
        raise

    updates: dict[str, Any] = {"current_agent": "ClientInterfaceAgent"}

    if result.get("status") == "complete":
        logger.info("Requirements extraction complete")
        components = result.get("product_components", [])
        logger.info(f"Extracted {len(components)} product components")
        updates["client_requirements"] = result.get("client_requirements", {})
        updates["product_components"] = components
        # No follow-up — signal readiness
        updates["messages"] = [
            AIMessage(
                content=(
                    "✅ Вимоги зафіксовані. Передаю технологу для формування маршруту.\n"
                    f"Компоненти: {', '.join(c['name'] for c in components)}"
                ),
                name="ClientInterfaceAgent",
            )
        ]
    else:
        # Ask follow-up question
        question = result.get("follow_up_question", "Будь ласка, уточніть деталі замовлення.")
        logger.info("Requirements incomplete, asking follow-up question")
        updates["messages"] = [
            AIMessage(content=question, name="ClientInterfaceAgent")
        ]
        updates["client_requirements"] = {}
        updates["product_components"] = []
    
    logger.debug(f"ClientInterfaceAgent updates: {list(updates.keys())}")
    return updates
