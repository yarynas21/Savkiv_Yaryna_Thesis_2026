"""
Graph Visualization Tool
========================
Visualizes the LangGraph workflow structure using graphviz.

Requirements:
    pip install graphviz langgraph

Usage:
    python visualize_graph.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graph.workflow import compile_workflow

try:
    from graphviz import Digraph
except ImportError:
    print("❌ graphviz не встановлено. Встановіть:")
    print("   pip install graphviz")
    print("   # Також потрібен системний graphviz:")
    print("   # macOS: brew install graphviz")
    print("   # Ubuntu: sudo apt-get install graphviz")
    sys.exit(1)


def visualize_workflow(output_format: str = "png", output_file: str = "workflow_graph"):
    """
    Creates a visual representation of the LangGraph workflow.

    Parameters
    ----------
    output_format : str
        Output format: 'png', 'svg', 'pdf', 'dot'
    output_file : str
        Output filename (without extension)
    """
    print("🔄 Compiling workflow...")
    workflow = compile_workflow()
    
    print("📊 Creating graph visualization...")
    
    # Create directed graph
    dot = Digraph(comment="Dyz-Art MAS Workflow", format=output_format)
    dot.attr(rankdir="LR", size="12,8")
    dot.attr("node", shape="box", style="rounded,filled", fontname="Arial")
    dot.attr("edge", fontname="Arial", fontsize="10")
    
    # Color scheme
    colors = {
        "start": "#90EE90",      # light green
        "end": "#FFB6C1",        # light pink
        "agent": "#87CEEB",      # sky blue
        "human": "#FFD700",      # gold
        "decision": "#DDA0DD",   # plum
    }
    
    # ── Nodes ────────────────────────────────────────────────────────────────
    
    # START
    dot.node("START", "START", fillcolor=colors["start"], fontcolor="black")
    
    # Agents
    dot.node("client_interface", 
             "1️⃣ Client Interface\nAgent\n(Витягує вимоги)", 
             fillcolor=colors["agent"], fontcolor="black")
    
    dot.node("technologist", 
             "2️⃣ Technologist\nAgent\n(Будує маршрути)", 
             fillcolor=colors["agent"], fontcolor="black")
    
    dot.node("validation", 
             "3️⃣ Validation\nAgent\n(Перевіряє маршрути)", 
             fillcolor=colors["agent"], fontcolor="black")
    
    dot.node("human_review", 
             "👤 Human-in-the-Loop\n(Очікує відповіді експерта)", 
             fillcolor=colors["human"], fontcolor="black", shape="diamond")
    
    dot.node("generation", 
             "4️⃣ Generation\nAgent\n(Excel + калькуляція)", 
             fillcolor=colors["agent"], fontcolor="black")
    
    # END
    dot.node("END", "END", fillcolor=colors["end"], fontcolor="black")
    
    # Decision nodes (for conditional edges)
    dot.node("check_client", 
             "Вимоги\nповні?", 
             fillcolor=colors["decision"], fontcolor="black", shape="diamond", style="filled")
    
    dot.node("check_validation", 
             "Маршрути\nвалідні?", 
             fillcolor=colors["decision"], fontcolor="black", shape="diamond", style="filled")
    
    # ── Edges ────────────────────────────────────────────────────────────────
    
    # START → client_interface
    dot.edge("START", "client_interface", label="", color="black")
    
    # client_interface → decision
    dot.edge("client_interface", "check_client", label="", color="black")
    
    # Decision: complete → technologist, incomplete → END
    dot.edge("check_client", "technologist", 
             label="✅ Так\n(компоненти\n+ вимоги)", 
             color="green", fontcolor="green")
    dot.edge("check_client", "END", 
             label="❌ Ні\n(очікує\nвідповіді)", 
             color="orange", fontcolor="orange", style="dashed")
    
    # technologist → validation
    dot.edge("technologist", "validation", label="", color="black")
    
    # validation → decision
    dot.edge("validation", "check_validation", label="", color="black")
    
    # Decision: validated → generation, needs_human → human_review
    dot.edge("check_validation", "generation", 
             label="✅ Валідовано", 
             color="green", fontcolor="green")
    dot.edge("check_validation", "human_review", 
             label="⚠️ Потрібен\nексперт", 
             color="red", fontcolor="red")
    
    # human_review → validation (loop back)
    dot.edge("human_review", "validation", 
             label="Відповідь\nексперта", 
             color="blue", fontcolor="blue", style="dashed")
    
    # generation → END
    dot.edge("generation", "END", label="", color="black")
    
    # ── Render ───────────────────────────────────────────────────────────────
    
    output_path = dot.render(output_file, cleanup=True, view=False)
    print(f"✅ Граф збережено: {output_path}")
    print(f"   Формат: {output_format.upper()}")
    
    # Also save as DOT source for manual editing
    dot_file = f"{output_file}.dot"
    dot.save(dot_file)
    print(f"📝 DOT source збережено: {dot_file}")
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualize Dyz-Art MAS LangGraph workflow")
    parser.add_argument(
        "--format",
        choices=["png", "svg", "pdf", "dot"],
        default="png",
        help="Output format (default: png)"
    )
    parser.add_argument(
        "--output",
        default="workflow_graph",
        help="Output filename without extension (default: workflow_graph)"
    )
    
    args = parser.parse_args()
    
    try:
        visualize_workflow(output_format=args.format, output_file=args.output)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
