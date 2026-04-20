"""
ProductionState — shared state for the LangGraph multi-agent workflow.
"""

from __future__ import annotations

from typing import Annotated, List, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ProductionState(TypedDict):
    """
    Shared state that flows through all agents in the workflow.

    Fields:
        messages            – full conversation history (auto-merged by add_messages)
        client_requirements – structured parameters extracted from the client's request
        product_components  – list of product parts (box, cards, rulebook, inserts…)
        production_routes   – technological route for each component
        validation_status   – "pending" | "validated" | "needs_human" | "approved"
        ambiguities         – list of unresolved technical questions
        human_feedback      – expert's answer injected via Human-in-the-Loop interrupt
        work_order          – final Technical Work Order dict (→ Excel)
        cost_estimates      – price breakdown per quantity tier
        llm_eval            – per-session LLM runtime metrics rows for eval/cost
        current_agent       – name of the agent currently executing (for Streamlit status)
        iteration           – validation loop counter (safety cap)
    """

    messages: Annotated[List[BaseMessage], add_messages]
    client_requirements: dict
    product_components: List[dict]
    requirements_complete: bool
    production_routes: List[dict]
    validation_status: str
    ambiguities: List[str]
    human_feedback: Optional[str]
    work_order: Optional[dict]
    cost_estimates: Optional[dict]
    llm_eval: Optional[dict]
    current_agent: str
    iteration: int
