"""
Generation Agent
================
Final stage of the workflow.

Responsibilities:
- Receives validated production routes
- Calls the Excel generator to produce the Technical Work Order
- Calls the cost calculator to produce price estimates
- Returns `work_order` and `cost_estimates` in state
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm
from graph.state import ProductionState
from tools.excel_generator import generate_work_order_excel
from tools.cost_calculator import calculate_costs
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# System prompt — used to enrich the work order with human-readable summaries
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ти — агент-генератор документів поліграфічного підприємства Dyz-Art.

На основі затверджених маршрутів сформуй структуру Технічного Завдання:

МАРШРУТИ:
{routes}

ВИМОГИ ЗАМОВНИКА:
{requirements}

Поверни ТІЛЬКИ JSON (без markdown):
{{
  "order_number": "DYZ-2025-001",
  "client": "...",
  "product": "...",
  "quantity": 1000,
  "components": [
    {{
      "component_id": "rigid_box",
      "component_name": "Жорстка коробка",
      "material_summary": "Покривний аркуш: крейд. 350 г/м² + soft touch; Основа: сірий картон 2000 г/м²",
      "operations_summary": [
        "1. Допечатна підготовка",
        "2. Офсетний друк (Heidelberg SM74, 4+0)",
        "3. Soft Touch ламінація",
        "4. Гаряче тиснення фольгою",
        "5. Висічка (BOBST SP 76)",
        "6. Обклейка чіпборда",
        "7. Складання коробки",
        "8. Контроль якості",
        "9. Пакування"
      ],
      "estimated_duration_hours": 6.5
    }}
  ],
  "total_estimated_hours": 12.0,
  "special_notes": "Замовити кліше для фольги за 5 днів до виробництва."
}}
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def generation_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: Generation Agent.
    Compiles the Technical Work Order (Excel) and cost estimates.
    """
    logger.info("GenerationAgent: Starting document generation")
    
    routes = state.get("production_routes", [])
    requirements = state.get("client_requirements", {})
    logger.info(f"Generating work order for {len(routes)} routes")
    
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT.format(
            routes=json.dumps(routes, ensure_ascii=False, indent=2),
            requirements=json.dumps(requirements, ensure_ascii=False, indent=2),
        )),
    ])

    chain = prompt | llm | RobustJsonOutputParser()
    logger.debug("Invoking LLM for work order structure...")
    
    try:
        work_order: dict = chain.invoke({})
        logger.info("Work order structure generated")
    except Exception as e:
        logger.error(f"Error in GenerationAgent LLM call: {e}", exc_info=True)
        raise

    # Generate Excel bytes
    logger.info("Generating Excel file...")
    excel_bytes = generate_work_order_excel(work_order, routes, requirements)
    logger.info(f"Excel file generated: {len(excel_bytes)} bytes")

    # Calculate cost estimates
    quantity = requirements.get("quantity", 1000)
    logger.info(f"Calculating costs for quantity: {quantity}")
    cost_estimates = calculate_costs(routes, quantity)
    logger.info("Cost estimates calculated")

    work_order["excel_bytes"] = excel_bytes

    summary_lines = [
        f"📄 **Технічне завдання сформовано** — замовлення {work_order.get('order_number', 'N/A')}",
        f"Клієнт: {work_order.get('client', '—')}",
        f"Продукт: {work_order.get('product', '—')}",
        f"Тираж: {quantity} шт.",
        "",
        "💰 **Орієнтовна вартість:**",
    ]
    for tier, price in cost_estimates.get("tiers", {}).items():
        summary_lines.append(f"  • {tier}: {price:,.0f} грн")

    return {
        "work_order": work_order,
        "cost_estimates": cost_estimates,
        "current_agent": "GenerationAgent",
        "messages": [
            AIMessage(
                content="\n".join(summary_lines),
                name="GenerationAgent",
            )
        ],
    }
