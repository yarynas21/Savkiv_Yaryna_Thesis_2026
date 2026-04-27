"""
LangGraph Workflow
==================
Assembles all agents into a StateGraph with:
- Sequential flow: ConversationalAgent → Technologist → Validation → Generation
- Conditional edge at Validation: "needs_human" → interrupt → back to Validation
- Human-in-the-Loop via langgraph interrupt mechanism

Кожен агент підключений як підграф (див. graph/agent_subgraphs.py); ідентифікатори
вузлів узгоджені з agents.registry.

Graph topology:
  START
    └─► conversational_agent ──► technologist ──► validation
                                                  │
                               ┌──── needs_human ─┘
                               │         ▲
                               ▼         │
                           human_review ─┘
                               │
                    validated  └─► generation ──► END
"""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.registry import (
    NODE_CONVERSATIONAL_AGENT,
    NODE_GENERATION,
    NODE_HUMAN_REVIEW,
    NODE_TECHNOLOGIST,
    NODE_VALIDATION,
)
from graph.agent_subgraphs import (
    build_conversational_agent_subgraph,
    build_generation_subgraph,
    build_human_review_subgraph,
    build_technologist_subgraph,
    build_validation_subgraph,
)
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)


def _route_after_validation(
    state: ProductionState,
) -> Literal["human_review", "generation"]:
    status = state.get("validation_status", "needs_human")
    logger.debug(f"Routing after validation: status={status}")
    if status == "validated":
        logger.info("Routes validated, proceeding to generation")
        return "generation"
    logger.info("Routes need human review")
    return "human_review"


def _route_after_client(
    state: ProductionState,
) -> Literal["technologist", "__end__"]:
    if state.get("requirements_complete") is True:
        logger.info("Client requirements complete, routing to technologist")
        return "technologist"
    logger.info("Client requirements incomplete, pausing workflow (→ END)")
    return "__end__"


def compile_workflow(checkpointer=None):
    """Build and compile the LangGraph StateGraph."""
    logger.info("Compiling LangGraph workflow...")
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.debug("Using MemorySaver checkpointer")

    graph = StateGraph(ProductionState)
    logger.debug("StateGraph created")

    graph.add_node(NODE_CONVERSATIONAL_AGENT, build_conversational_agent_subgraph())
    graph.add_node(NODE_TECHNOLOGIST, build_technologist_subgraph())
    graph.add_node(NODE_VALIDATION, build_validation_subgraph())
    graph.add_node(NODE_HUMAN_REVIEW, build_human_review_subgraph())
    graph.add_node(NODE_GENERATION, build_generation_subgraph())

    graph.add_edge(START, NODE_CONVERSATIONAL_AGENT)

    graph.add_conditional_edges(
        NODE_CONVERSATIONAL_AGENT,
        _route_after_client,
        {
            "technologist": NODE_TECHNOLOGIST,
            "__end__": END,
        },
    )

    graph.add_edge(NODE_TECHNOLOGIST, NODE_VALIDATION)

    graph.add_conditional_edges(
        NODE_VALIDATION,
        _route_after_validation,
        {
            "human_review": NODE_HUMAN_REVIEW,
            "generation": NODE_GENERATION,
        },
    )

    graph.add_edge(NODE_HUMAN_REVIEW, NODE_VALIDATION)
    graph.add_edge(NODE_GENERATION, END)

    logger.info("Compiling graph with checkpointer and interrupts...")
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=[NODE_HUMAN_REVIEW],
    )
    logger.info("Workflow compiled successfully")
    return compiled
