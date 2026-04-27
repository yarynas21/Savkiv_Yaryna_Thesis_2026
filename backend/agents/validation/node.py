from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.json_parser import RobustJsonOutputParser
from agents.llm_factory import get_llm_for_agent
from agents.validation.prompt import _SYSTEM_PROMPT
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)

from db.repository import get_kb_machines


def _load_constraints() -> dict:
    return get_kb_machines().get("constraints", {})


_CONSTRAINTS = _load_constraints()


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

    if human_feedback and human_feedback not in ("Відсутній", "None", ""):
        logger.info("Human expert feedback received — marking routes as validated without LLM re-check")
        return {
            "validation_status": "validated",
            "ambiguities": [],
            "current_agent": "ValidationAgent",
            "iteration": iteration + 1,
            "human_feedback": None,
            "messages": [
                AIMessage(
                    content=(
                        "Технологічні маршрути перевірено з урахуванням відповіді експерта.\n"
                        f"Рішення експерта: {human_feedback[:200]}\n"
                        "Передаю на генерацію документів."
                    ),
                    name="ValidationAgent",
                )
            ],
        }

    llm = get_llm_for_agent("validation")

    # Safety cap — after 3 validation loops, force approval
    if iteration >= 3:
        logger.warning(f"Validation iteration limit reached ({iteration}), forcing approval")
        return {
            "validation_status": "validated",
            "ambiguities": [],
            "current_agent": "ValidationAgent",
            "iteration": iteration + 1,
            "human_feedback": None,
            "messages": [
                AIMessage(
                    content="Валідацію завершено (досягнуто ліміт ітерацій). Передаю на генерацію.",
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
        HumanMessage(content=(
            "Перевір маршрути та поверни результат суворо у JSON згідно інструкції. "
            "Без markdown, лише JSON."
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
        "human_feedback": None,
    }

    if corrected:
        if (
            isinstance(corrected, list)
            and corrected
            and all(isinstance(r, dict) and "component_id" in r and "operations" in r for r in corrected)
        ):
            updates["production_routes"] = corrected
        else:
            logger.warning("ValidationAgent: corrected_routes from LLM has invalid schema — ignoring")

    if status == "validated":
        updates["messages"] = [
            AIMessage(
                content="Технологічні маршрути перевірено. Передаю на генерацію документів.",
                name="ValidationAgent",
            )
        ]
    else:
        questions = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(ambiguities))
        updates["messages"] = [
            AIMessage(
                content=(
                    "Знайдено неоднозначності. Потрібна консультація експерта:\n"
                    + questions
                ),
                name="ValidationAgent",
            )
        ]

    return updates
