"""PNG графа LangGraph через get_graph().draw_mermaid_png().

Запуск:
  python visualize_graph.py                                # весь workflow → pipeline_graph.png
  python visualize_graph.py --target conversational        # реальний conversational subgraph
  python visualize_graph.py --target conversational_detailed
  python visualize_graph.py --target conversational -o out.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Literal

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from langgraph.graph import END, START, StateGraph
from graph.state import ProductionState

_DEFAULT_OUTPUTS: dict[str, str] = {
    "workflow": "pipeline_graph.png",
    "conversational": "conversational_graph.png",
    "conversational_detailed": "conversational_graph_detailed.png",
}


def _build_workflow():
    from graph.workflow import compile_workflow

    return compile_workflow()


def _build_conversational():
    """Real conversational subgraph with actual runtime nodes."""
    from langgraph.prebuilt import ToolNode

    from agents.conversational import (
        conversational_agent_node,
        conversational_tool_response_node,
        game_components_catalog_tool,
        greeting_tool,
        route_after_conversational_manager,
    )

    g = StateGraph(ProductionState)
    g.add_node("conversational_agent_manager", conversational_agent_node)
    g.add_node(
        "tool_node_greeting_and_game_components",
        ToolNode([greeting_tool, game_components_catalog_tool]),
    )
    g.add_node("tool_response_to_client_message", conversational_tool_response_node)

    g.add_edge(START, "conversational_agent_manager")
    g.add_conditional_edges(
        "conversational_agent_manager",
        route_after_conversational_manager,
        {
            "tools": "tool_node_greeting_and_game_components",
            "__end__": END,
        },
    )
    g.add_edge(
        "tool_node_greeting_and_game_components",
        "tool_response_to_client_message",
    )
    g.add_edge("tool_response_to_client_message", END)
    return g.compile()


def _noop_node(_: ProductionState) -> dict:
    return {}


def _route_after_manager_detailed(
    _: ProductionState,
) -> Literal["greeting_tool_call", "game_components_catalog_tool_call", "__end__"]:
    # Diagram-only router: we return __end__, but graph renders all branches.
    return "__end__"


def _build_conversational_detailed():
    """Diagram-only version with separate tool nodes for readability."""
    g = StateGraph(ProductionState)
    g.add_node("conversational_agent_manager", _noop_node)
    g.add_node("greeting_tool_call", _noop_node)
    g.add_node("game_components_catalog_tool_call", _noop_node)
    g.add_node("tool_response_to_client_message", _noop_node)

    g.add_edge(START, "conversational_agent_manager")
    g.add_conditional_edges(
        "conversational_agent_manager",
        _route_after_manager_detailed,
        {
            "greeting_tool_call": "greeting_tool_call",
            "game_components_catalog_tool_call": "game_components_catalog_tool_call",
            "__end__": END,
        },
    )
    g.add_edge("greeting_tool_call", "tool_response_to_client_message")
    g.add_edge("game_components_catalog_tool_call", "tool_response_to_client_message")
    g.add_edge("tool_response_to_client_message", END)
    return g.compile()


_BUILDERS = {
    "workflow": _build_workflow,
    "conversational": _build_conversational,
    "conversational_detailed": _build_conversational_detailed,
}


def visualize_graph(pipeline, output_path: str) -> None:
    """Visualize the pipeline graph and save it as a PNG."""
    graph = pipeline.get_graph()
    try:
        graph_image = graph.draw_mermaid_png()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(graph_image)
        print(f"Graph visualization saved to: {out.resolve()}")
    except Exception as e:
        print(f"Could not generate graph image: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--target",
        choices=sorted(_BUILDERS),
        default="workflow",
        help=(
            "Який граф малювати: "
            "'workflow' (весь pipeline), "
            "'conversational' (реальний підграф), "
            "'conversational_detailed' (деталізована схема з окремими tool-вузлами)."
        ),
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Шлях до PNG. За замовчуванням залежить від --target.",
    )
    args = p.parse_args()
    output = args.output or _DEFAULT_OUTPUTS[args.target]
    try:
        visualize_graph(_BUILDERS[args.target](), output_path=output)
    except Exception as e:
        print(e)
        sys.exit(1)
