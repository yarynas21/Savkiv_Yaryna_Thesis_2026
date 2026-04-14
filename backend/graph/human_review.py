"""
Вузол Human-in-the-Loop: пауза графа перед урахуванням відповіді експерта.
"""

from __future__ import annotations

from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)


def human_review_node(state: ProductionState) -> dict:
    """
    Читає зворотний зв'язок експерта зі стану (інжектований через API після interrupt).
    Граф призупиняється ПЕРЕД цим вузлом через interrupt_before=['human_review'].
    """
    expert_answer = state.get("human_feedback") or ""
    ambiguities = state.get("ambiguities", [])
    logger.info("HumanReviewNode: Incorporating expert feedback into workflow")
    logger.info(
        f"Expert feedback ({len(ambiguities)} ambiguities resolved): {expert_answer[:120]}..."
    )

    return {
        "current_agent": "HumanExpert",
    }
