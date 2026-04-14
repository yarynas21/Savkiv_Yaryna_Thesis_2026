"""
Підграфи MAS: кожен агент — окремий скомпільований StateGraph (START → run → END).
Батьківський workflow підключає їх як вузли для явної композиції мультиагентної системи.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.conversational_agent import conversational_agent_node
from agents.generation import generation_node
from agents.technologist import technologist_node
from agents.validation import validation_node
from graph.human_review import human_review_node
from graph.state import ProductionState


def _single_agent_subgraph(node_fn):
    g = StateGraph(ProductionState)
    g.add_node("run", node_fn)
    g.add_edge(START, "run")
    g.add_edge("run", END)
    return g.compile()


def build_conversational_agent_subgraph():
    return _single_agent_subgraph(conversational_agent_node)


def build_technologist_subgraph():
    return _single_agent_subgraph(technologist_node)


def build_validation_subgraph():
    return _single_agent_subgraph(validation_node)


def build_human_review_subgraph():
    return _single_agent_subgraph(human_review_node)


def build_generation_subgraph():
    return _single_agent_subgraph(generation_node)
