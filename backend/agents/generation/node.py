from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.generation.prompt import _SYSTEM_PROMPT
from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm_for_agent
from graph.state import ProductionState
from tools.excel_generator import generate_work_order_excel
from tools.cost_calculator import calculate_costs
from utils.logger import get_logger

logger = get_logger(__name__)


def generation_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: Generation Agent.
    Compiles the Technical Work Order (Excel) and cost estimates.
    """
    logger.info("GenerationAgent: Starting document generation")

    routes = state.get("production_routes", [])
    requirements = state.get("client_requirements", {})
    logger.info(f"Generating work order for {len(routes)} routes")

    llm = get_llm_for_agent("generation")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT.format(
            routes=json.dumps(routes, ensure_ascii=False, indent=2),
            requirements=json.dumps(requirements, ensure_ascii=False, indent=2),
        )),
        HumanMessage(content=(
            "Сформуй структуру технічного завдання у JSON згідно інструкції. "
            "Без markdown, лише JSON."
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

    # Calculate cost estimates first — passed into Excel
    quantity   = requirements.get("quantity", 1000)
    components = state.get("product_components", [])
    logger.info(f"Calculating costs for quantity: {quantity}")
    cost_estimates = calculate_costs(
        routes,
        quantity,
        components=components,
        client_requirements=requirements,
    )
    logger.info("Cost estimates calculated")

    # Generate Excel bytes (includes Наряди + Калькуляція)
    logger.info("Generating Excel file...")
    excel_bytes = generate_work_order_excel(work_order, routes, requirements, cost_estimates)
    logger.info(f"Excel file generated: {len(excel_bytes)} bytes")

    work_order["excel_bytes"] = excel_bytes

    summary_lines = [
        f"**Технічне завдання сформовано** — замовлення {work_order.get('order_number', 'N/A')}",
        f"Клієнт: {work_order.get('client', '—')}",
        f"Продукт: {work_order.get('product', '—')}",
        f"Тираж: {quantity} шт.",
        "",
        f"**Собівартість усього:** {cost_estimates.get('total_cost', 0):,.0f} грн",
        f"**Собівартість за одиницю:** {cost_estimates.get('cost_per_unit', 0):.2f} грн",
        f"**До оплати за одиницю (+{int((cost_estimates.get('margin',1.1)-1)*100)}%):** "
        f"{cost_estimates.get('price_per_unit', 0):.2f} грн",
        f"**Сума до оплати:** {cost_estimates.get('total_payment', 0):,.0f} грн",
        "",
        "**Орієнтовна вартість для інших тиражів:**",
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
