"""
LangGraph Workflow
==================
Assembles all agents into a StateGraph with:
- Sequential flow: ClientInterface → Technologist → Validation → Generation
- Conditional edge at Validation: "needs_human" → interrupt → back to Validation
- Human-in-the-Loop via langgraph interrupt mechanism

Graph topology:
  START
    └─► client_interface ──► technologist ──► validation
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

from agents.client_interface import client_interface_node
from agents.generation import generation_node
from agents.technologist import technologist_node
from agents.validation import validation_node
from graph.state import ProductionState
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Human-in-the-Loop node
# ---------------------------------------------------------------------------
def human_review_node(state: ProductionState) -> dict:
    """
    Reads expert feedback that was injected into state by the Streamlit app.
    The graph is paused BEFORE this node via interrupt_before=["human_review"].
    The Streamlit app updates state with human_feedback, then resumes.
    No interrupt() call needed here — interrupt_before already handled the pause.
    """
    expert_answer = state.get("human_feedback") or ""
    ambiguities = state.get("ambiguities", [])
    logger.info("HumanReviewNode: Incorporating expert feedback into workflow")
    logger.info(f"Expert feedback ({len(ambiguities)} ambiguities resolved): {expert_answer[:120]}...")

    return {
        "current_agent": "HumanExpert",
        # human_feedback is already in state; we don't need to re-set it
    }


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------
def _route_after_validation(
    state: ProductionState,
) -> Literal["human_review", "generation"]:
    """
    Decides next node after validation:
    - needs_human → pause for expert
    - validated   → proceed to generation
    """
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
    """
    If client requirements are complete → proceed to technologist.
    If incomplete → stop graph (END) and wait for next user message.
    The Streamlit app will re-invoke the graph with the next user message,
    which gets appended to the conversation history via add_messages reducer.
    """
    components = state.get("product_components", [])
    requirements = state.get("client_requirements", {})
    if components and requirements:
        logger.info("Client requirements complete, routing to technologist")
        return "technologist"
    logger.info("Client requirements incomplete, pausing workflow (→ END)")
    return "__end__"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
def compile_workflow(checkpointer=None):
    """
    Build and compile the LangGraph StateGraph.

    Parameters
    ----------
    checkpointer : optional LangGraph checkpointer (default: MemorySaver)

    Returns
    -------
    Compiled graph ready for invocation.
    """
    logger.info("Compiling LangGraph workflow...")
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.debug("Using MemorySaver checkpointer")

    graph = StateGraph(ProductionState)
    logger.debug("StateGraph created")

    # ── Nodes ──────────────────────────────────────────────────────────────
    graph.add_node("client_interface", client_interface_node)
    graph.add_node("technologist", technologist_node)
    graph.add_node("validation", validation_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("generation", generation_node)

    # ── Edges ──────────────────────────────────────────────────────────────

    # Entry point
    graph.add_edge(START, "client_interface")

    # After client_interface: go to technologist if complete, else END and wait for user
    graph.add_conditional_edges(
        "client_interface",
        _route_after_client,
        {
            "technologist": "technologist",
            "__end__": END,
        },
    )

    # Technologist always proceeds to validation
    graph.add_edge("technologist", "validation")

    # Validation: conditional routing
    graph.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "human_review": "human_review",
            "generation": "generation",
        },
    )

    # After human review → re-validate
    graph.add_edge("human_review", "validation")

    # Generation → end
    graph.add_edge("generation", END)

    # ── Compile ────────────────────────────────────────────────────────────
    logger.info("Compiling graph with checkpointer and interrupts...")
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
    logger.info("Workflow compiled successfully")
    return compiled