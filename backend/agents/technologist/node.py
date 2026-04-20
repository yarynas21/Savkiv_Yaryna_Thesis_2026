from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm_for_agent
from agents.technologist.prompt import _SYSTEM_PROMPT
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Load knowledge base from PostgreSQL
# ---------------------------------------------------------------------------
from db.repository import get_kb_machines, get_kb_materials, get_kb_operations


def _load_kb() -> dict:
    return {
        "materials": get_kb_materials(),
        "operations": get_kb_operations(),
        "machines": get_kb_machines(),
    }


_KB = _load_kb()


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

    llm = get_llm_for_agent("technologist")

    # Trim KB to avoid huge prompts — send only relevant sections
    kb_summary = {
        "operations_by_type": _KB["operations"].get("product_type_routes", {}),
        "materials_list": [
            {"id": m["id"], "name": m["name"], "compatible_with": m["compatible_with"]}
            for m in _KB["materials"].get("papers", [])
        ],
        "stock_items": [
            {
                "stock_no": s["stock_no"],
                "name": s["name"],
                "for_use": s.get("for_use"),
                "supply_form": s.get("supply_form"),
                "notes": s.get("notes"),
                "paper_id": s.get("paper_id"),
            }
            for s in _KB["materials"].get("stock_items", [])
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
        HumanMessage(content=(
            "Згенеруй технологічні маршрути у форматі JSON згідно інструкції. "
            "Виведи лише валідний JSON без markdown."
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
                    f"Технологічні маршрути сформовано для {len(routes)} компонент(ів).\n"
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
