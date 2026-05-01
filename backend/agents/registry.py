"""
Реєстр агентів MAS — ідентифікатори вузлів графа та метадані для документації / UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

NODE_CONVERSATIONAL_AGENT = "conversational_agent"
NODE_CLIENT_INTERFACE = NODE_CONVERSATIONAL_AGENT
NODE_TECHNOLOGIST = "technologist"
NODE_VALIDATION = "validation"
NODE_GENERATION = "generation"
NODE_HUMAN_REVIEW = "human_review"

AgentGraphNodeId = Literal[
    "conversational_agent",
    "technologist",
    "validation",
    "generation",
    "human_review",
]

# Roles for which a separate LLM instance is created
AgentLLMRole = Literal[
    "client_interface",
    "conversational_agent",
    "technologist",
    "validation",
    "generation",
]


@dataclass(frozen=True, slots=True)
class AgentInfo:
    """Метадані агента в багатоагентній системі."""

    graph_node_id: str
    display_name_uk: str
    role_description_uk: str
    uses_llm: bool


AGENTS: Mapping[str, AgentInfo] = {
    NODE_CONVERSATIONAL_AGENT: AgentInfo(
        graph_node_id=NODE_CONVERSATIONAL_AGENT,
        display_name_uk="Conversational Agent",
        role_description_uk=(
            "Веде діалог, збирає та структурує вимоги до замовлення "
            "і перелік компонентів продукту."
        ),
        uses_llm=True,
    ),
    NODE_TECHNOLOGIST: AgentInfo(
        graph_node_id=NODE_TECHNOLOGIST,
        display_name_uk="Технологічний агент",
        role_description_uk=(
            "На основі бази знань будує технологічні маршрути виробництва "
            "для кожного компонента."
        ),
        uses_llm=True,
    ),
    NODE_VALIDATION: AgentInfo(
        graph_node_id=NODE_VALIDATION,
        display_name_uk="Агент валідації",
        role_description_uk=(
            "Перевіряє повноту та технічну узгодженість маршрутів; "
            "за потреби ініціює залучення людини-експерта."
        ),
        uses_llm=True,
    ),
    NODE_GENERATION: AgentInfo(
        graph_node_id=NODE_GENERATION,
        display_name_uk="Агент генерації документів",
        role_description_uk=(
            "Формує структуру технічного завдання, розрахунок вартості "
            "та файл Excel."
        ),
        uses_llm=True,
    ),
    NODE_HUMAN_REVIEW: AgentInfo(
        graph_node_id=NODE_HUMAN_REVIEW,
        display_name_uk="Людина-експерт (Human-in-the-Loop)",
        role_description_uk=(
            "Фіксує вузол паузи графа: відповіді експерта з API потрапляють у стан "
            "і далі враховуються при валідації."
        ),
        uses_llm=False,
    ),
}

# Convenient tuple of identifiers for iterations / lookups
AGENT_GRAPH_NODE_IDS: tuple[str, ...] = tuple(AGENTS.keys())
