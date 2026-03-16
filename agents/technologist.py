"""
Technologist Agent
==================
Core reasoning engine of the MAS.

Responsibilities:
- Reads the structured product components from state
- Loads the knowledge base (materials, operations, machines)
- For each component selects compatible materials and builds a
  technological route (sequence of operations)
- Returns `production_routes` — one route per component
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Load knowledge base once at module level
# ---------------------------------------------------------------------------
_KB_DIR = Path(__file__).parent.parent / "knowledge_base"


def _load_kb() -> dict:
    with open(_KB_DIR / "materials.json", encoding="utf-8") as f:
        materials = json.load(f)
    with open(_KB_DIR / "operations.json", encoding="utf-8") as f:
        operations = json.load(f)
    with open(_KB_DIR / "machines.json", encoding="utf-8") as f:
        machines = json.load(f)
    return {"materials": materials, "operations": operations, "machines": machines}


_KB = _load_kb()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ти — досвідчений технолог поліграфічного підприємства Dyz-Art.
Маєш доступ до бази знань матеріалів, операцій та обмежень обладнання.

БАЗА ЗНАНЬ:
{knowledge_base}

КОМПОНЕНТИ ЗАМОВЛЕННЯ:
{components}

ВИМОГИ ЗАМОВНИКА:
{requirements}

Для КОЖНОГО компонента сформуй технологічний маршрут у вигляді JSON (без markdown):
{{
  "production_routes": [
    {{
      "component_id": "rigid_box",
      "component_name": "Жорстка коробка",
      "material": {{
        "cover": "coated_350",
        "base": "grey_chipboard_2000",
        "adhesive": "hot_melt_EVA"
      }},
      "operations": [
        {{
          "step": 1,
          "operation_id": "prepress",
          "operation_name": "Допечатна підготовка",
          "machine": null,
          "parameters": {{}},
          "notes": ""
        }},
        {{
          "step": 2,
          "operation_id": "offset_printing",
          "operation_name": "Офсетний друк",
          "machine": "heidelberg_sm74",
          "parameters": {{"colors": "4+0 CMYK"}},
          "notes": "Тираж > 500 — офсет"
        }}
      ],
      "estimated_duration_hours": 6.5
    }}
  ]
}}

ПРАВИЛА ВИБОРУ:
1. Якщо тираж < 500 — цифровий друк (digital_printing), інакше офсет.
2. Для rigid_box — завжди потрібна основа з сірого картону (chipboard) + обклейка.
3. Premium finish (soft touch) — потребує термічного преса.
4. Якщо є hot_foil_stamping — додати операцію після ламінації.
5. Виводь ТІЛЬКИ валідний JSON.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def technologist_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: Technologist Agent.
    Synthesises production routes for each product component.
    """
    logger.info("TechnologistAgent: Starting route synthesis")
    
    components = state.get("product_components", [])
    requirements = state.get("client_requirements", {})
    logger.info(f"Processing {len(components)} components")
    logger.debug(f"Components: {[c.get('name', c.get('id')) for c in components]}")
    
    llm = get_llm()

    # Trim KB to avoid huge prompts — send only relevant sections
    kb_summary = {
        "operations_by_type": _KB["operations"].get("product_type_routes", {}),
        "materials_list": [
            {"id": m["id"], "name": m["name"], "compatible_with": m["compatible_with"]}
            for m in _KB["materials"].get("papers", [])
        ],
        "machines_summary": [
            {"id": m["id"], "name": m["name"], "operation": m["operation"]}
            for m in _KB["machines"].get("machines", [])
        ],
        "constraints": _KB["machines"].get("constraints", {}),
    }

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT.format(
            knowledge_base=json.dumps(kb_summary, ensure_ascii=False, indent=2),
            components=json.dumps(components, ensure_ascii=False, indent=2),
            requirements=json.dumps(requirements, ensure_ascii=False, indent=2),
        )),
    ])

    chain = prompt | llm | RobustJsonOutputParser()
    logger.debug("Invoking LLM for route synthesis...")
    
    try:
        result: dict = chain.invoke({})
        logger.info("LLM response received for route synthesis")
        logger.debug(f"Result keys: {list(result.keys())}")
    except Exception as e:
        logger.error(f"Error in TechnologistAgent LLM call: {e}", exc_info=True)
        raise

    routes = result.get("production_routes", [])
    logger.info(f"Generated {len(routes)} production routes")

    return {
        "production_routes": routes,
        "current_agent": "TechnologistAgent",
        "validation_status": "pending",
        "messages": [
            AIMessage(
                content=(
                    f"🔧 Технологічні маршрути сформовано для {len(routes)} компонент(ів).\n"
                    + "\n".join(
                        f"  • {r.get('component_name', r.get('component_id'))}: "
                        f"{len(r.get('operations', []))} операцій"
                        for r in routes
                    )
                ),
                name="TechnologistAgent",
            )
        ],
    }
