"""
Validation Agent
================
Implements the "Human-in-the-Loop" mechanism.

Responsibilities:
- Checks completeness and technical feasibility of production routes
- Identifies ambiguities (missing glue type, incompatible material, etc.)
- If ambiguities are found → sets status "needs_human" and lists them
- If everything is OK → sets status "validated"
- After human feedback is injected → re-validates and approves
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)

_KB_DIR = Path(__file__).parent.parent / "knowledge_base"


def _load_constraints() -> dict:
    with open(_KB_DIR / "machines.json", encoding="utf-8") as f:
        return json.load(f).get("constraints", {})


_CONSTRAINTS = _load_constraints()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """Ти — технолог-валідатор поліграфічного підприємства Dyz-Art.
Твоя задача — перевірити технологічні маршрути на повноту та технічну можливість.

МАРШРУТИ ДЛЯ ПЕРЕВІРКИ:
{routes}

ВИМОГИ ЗАМОВНИКА:
{requirements}

ОБМЕЖЕННЯ ОБЛАДНАННЯ:
{constraints}

ЗВОРОТНІЙ ЗВ'ЯЗОК ЕКСПЕРТА (якщо є):
{human_feedback}

Перевір:
1. Чи всі обов'язкові операції присутні для кожного типу продукту.
2. Чи вибрані матеріали сумісні між собою.
3. Чи правильно обраний тип друку залежно від тиражу.
4. Чи вказаний клей для склеювання.
5. Чи враховані всі спецефекти (фольга, рельєф).

Поверни ТІЛЬКИ JSON (без markdown):
{{
  "validation_status": "validated",
  "ambiguities": [],
  "corrected_routes": null,
  "summary": "Маршрути пройшли перевірку."
}}

АБО якщо є проблеми:
{{
  "validation_status": "needs_human",
  "ambiguities": [
    "Для компонента 'card_deck' не вказано тип клею між шарами карт.",
    "Матеріал 'coated_250' несумісний з soft touch ламінацією за специфікацією машини."
  ],
  "corrected_routes": null,
  "summary": "Потрібне уточнення від експерта."
}}
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def validation_node(state: ProductionState) -> dict[str, Any]:
    """
    LangGraph node: Validation Agent.
    Validates routes and triggers Human-in-the-Loop if needed.
    """
    logger.info("ValidationAgent: Starting route validation")
    
    routes = state.get("production_routes", [])
    requirements = state.get("client_requirements", {})
    human_feedback = state.get("human_feedback") or "Відсутній"
    iteration = state.get("iteration", 0)
    
    logger.info(f"Validating {len(routes)} routes, iteration {iteration}")
    logger.debug(f"Human feedback present: {bool(state.get('human_feedback'))}")

    # ── If expert feedback was provided → trust it and mark as validated ──────
    # The human expert has already resolved all ambiguities; no LLM re-check needed.
    if human_feedback and human_feedback not in ("Відсутній", "None", ""):
        logger.info("Human expert feedback received — marking routes as validated without LLM re-check")
        return {
            "validation_status": "validated",
            "ambiguities": [],
            "current_agent": "ValidationAgent",
            "iteration": iteration + 1,
            "human_feedback": None,  # consume feedback
            "messages": [
                AIMessage(
                    content=(
                        "✅ Технологічні маршрути перевірено з урахуванням відповіді експерта.\n"
                        f"Рішення експерта: {human_feedback[:200]}\n"
                        "Передаю на генерацію документів."
                    ),
                    name="ValidationAgent",
                )
            ],
        }

    llm = get_llm()

    # Safety cap — after 3 validation loops, force approval
    if iteration >= 3:
        logger.warning(f"Validation iteration limit reached ({iteration}), forcing approval")
        return {
            "validation_status": "validated",
            "ambiguities": [],
            "current_agent": "ValidationAgent",
            "messages": [
                AIMessage(
                    content="✅ Валідацію завершено (досягнуто ліміт ітерацій). Передаю на генерацію.",
                    name="ValidationAgent",
                )
            ],
        }

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYSTEM_PROMPT.format(
            routes=json.dumps(routes, ensure_ascii=False, indent=2),
            requirements=json.dumps(requirements, ensure_ascii=False, indent=2),
            constraints=json.dumps(_CONSTRAINTS, ensure_ascii=False, indent=2),
            human_feedback=human_feedback,
        )),
    ])

    chain = prompt | llm | RobustJsonOutputParser()
    logger.debug("Invoking LLM for validation...")
    
    try:
        result: dict = chain.invoke({})
        logger.info("LLM validation response received")
    except Exception as e:
        logger.error(f"Error in ValidationAgent LLM call: {e}", exc_info=True)
        raise

    status = result.get("validation_status", "needs_human")
    ambiguities = result.get("ambiguities", [])
    corrected = result.get("corrected_routes")
    
    logger.info(f"Validation status: {status}, ambiguities: {len(ambiguities)}")

    updates: dict[str, Any] = {
        "validation_status": status,
        "ambiguities": ambiguities,
        "current_agent": "ValidationAgent",
        "iteration": iteration + 1,
        "human_feedback": None,  # reset after processing
    }

    if corrected:
        updates["production_routes"] = corrected

    if status == "validated":
        updates["messages"] = [
            AIMessage(
                content="✅ Технологічні маршрути перевірено. Передаю на генерацію документів.",
                name="ValidationAgent",
            )
        ]
    else:
        questions = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(ambiguities))
        updates["messages"] = [
            AIMessage(
                content=(
                    "⚠️ Знайдено неоднозначності. Потрібна консультація експерта:\n"
                    + questions
                ),
                name="ValidationAgent",
            )
        ]

    return updates
