"""PNG графа LangGraph через get_graph().draw_mermaid_png(). Запуск: python visualize_graph.py [-o шлях]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from graph.workflow import compile_workflow


def visualize_graph(pipeline, output_path: str = "ai/pipeline_graph.png") -> None:
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
    p.add_argument("-o", "--output", default="pipeline_graph.png")
    args = p.parse_args()
    try:
        visualize_graph(compile_workflow(), output_path=args.output)
    except Exception as e:
        print(e)
        sys.exit(1)
