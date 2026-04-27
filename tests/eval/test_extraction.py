"""Pytest evaluation suite for the conversational extraction agent.

Run:
    cd Savkiv_Yaryna_Thesis_2025
    pytest tests/eval/test_extraction.py -v --tb=short -s

After the run, charts and a JSON report are written to:
    tests/eval/reports/
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(ROOT / ".env")

# Prevent unrelated auth bootstrap errors during test import collection.
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_for_eval_only")

from agents.conversational.llm_invoke import _invoke_llm
from agents.conversational.node import _known_data_system_message, _merge_partial_data
from agents.conversational.prompt import PROMPT, get_ui_role_context
from agents.conversational.schema import _repair_extraction_result
from agents.llm_factory import get_llm_for_agent
from tests.eval.dataset import ALL_SCENARIOS, Scenario

REPORTS_DIR = Path(__file__).parent / "reports"
_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

# Category display config: prefix → (label, color)
_CATEGORIES: dict[str, tuple[str, str]] = {
    "ext":    ("Базова екстракція",    "#4C72B0"),
    "ext2":   ("Екстракція (дод.)",   "#4C72B0"),
    "ext3":   ("Екстракція (розш.)",  "#4C72B0"),
    "ext4":   ("Екстракція (4)",      "#4C72B0"),
    "conf":   ("Тест на плутанину",   "#DD8452"),
    "conf2":  ("Плутанина (дод.)",    "#DD8452"),
    "conf3":  ("Плутанина (розш.)",   "#DD8452"),
    "multi":  ("Multi-turn",          "#55A868"),
    "multi2": ("Multi-turn (дод.)",   "#55A868"),
    "multi3": ("Multi-turn (розш.)",  "#55A868"),
    "multi4": ("Multi-turn (4)",      "#55A868"),
    "guard":  ("Guardrails",          "#C44E52"),
    "guard2": ("Guardrails (дод.)",   "#C44E52"),
    "guard3": ("Guardrails (розш.)",  "#C44E52"),
    "guard4": ("Guardrails (4)",      "#C44E52"),
    "edge":   ("Edge cases",          "#8172B2"),
    "edge2":  ("Edge cases (дод.)",   "#8172B2"),
    "edge3":  ("Edge cases (розш.)",  "#8172B2"),
    "edge4":  ("Edge cases (4)",      "#8172B2"),
    "stress": ("Stress tests",        "#937860"),
}

# ---------------------------------------------------------------------------
# Shared results accumulator (thread-safe enough for sequential pytest)
# ---------------------------------------------------------------------------

_results: list[dict[str, Any]] = []


def _persist_progress() -> None:
    """Persist partial results during long runs (even if tests fail/interrupt)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = REPORTS_DIR / f"results_{_PROVIDER}.partial.json"
    safe = [{k: v for k, v in row.items() if k != "llm_meta"} for row in _results]
    progress_path.write_text(json.dumps(safe, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------

def _build_messages(scenario: Scenario) -> list:
    messages: list = []
    if scenario.accumulated:
        known_req = scenario.accumulated.get("requirements", {})
        known_comp = scenario.accumulated.get("components", [])
        sys_msg = _known_data_system_message(known_req, known_comp)
        if sys_msg:
            messages.append(sys_msg)
    for human_text, assistant_text in scenario.history:
        messages.append(HumanMessage(content=human_text))
        messages.append(AIMessage(content=assistant_text))
    messages.append(HumanMessage(content=scenario.input))
    return messages


def _get_component(result: dict, component_id: str) -> dict:
    for comp in result.get("product_components", []):
        if isinstance(comp, dict) and comp.get("id") == component_id:
            return comp
    return {}


def _apply_merge(result: dict, accumulated: dict) -> dict:
    existing_req = accumulated.get("requirements", {})
    existing_comp = accumulated.get("components", [])
    merged_req, merged_comp = _merge_partial_data(
        existing_req, existing_comp,
        result.get("client_requirements", {}),
        result.get("product_components", []),
    )
    return {**result, "client_requirements": merged_req, "product_components": merged_comp}


# ---------------------------------------------------------------------------
# Field-level comparison
# ---------------------------------------------------------------------------

def _field_ok(actual: Any, expected: Any) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, list):
        return actual == expected
    if isinstance(expected, float):
        try:
            return abs(float(actual or 0) - expected) < 0.01
        except (TypeError, ValueError):
            return False
    return actual == expected


# ---------------------------------------------------------------------------
# Pytest fixture + parametrised test
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def llm():
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY (or configure LLM_PROVIDER for another provider) before running eval tests.")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("Set ANTHROPIC_API_KEY before running eval tests.")
    if provider in {"google", "gemini"} and not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("Set GOOGLE_API_KEY before running eval tests.")
    return get_llm_for_agent("client_interface")


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=[s.id for s in ALL_SCENARIOS])
def test_extraction(scenario: Scenario, llm) -> None:
    ui_role_context = get_ui_role_context("client")
    messages = _build_messages(scenario)

    raw_result, meta = _invoke_llm(PROMPT, messages, llm, ui_role_context=ui_role_context)
    result = _repair_extraction_result(raw_result)

    if scenario.accumulated:
        result = _apply_merge(result, scenario.accumulated)

    failures: list[str] = []
    field_results: list[dict[str, Any]] = []  # per-field records for heatmap
    expected = scenario.expected

    def _check(actual: Any, exp: Any, path: str) -> None:
        ok = _field_ok(actual, exp)
        field_results.append({"field": path, "ok": ok, "expected": exp, "actual": actual})
        if not ok:
            failures.append(f"  {path}: expected={exp!r}  got={actual!r}")

    # 1. status
    if "status" in expected:
        _check(result.get("status"), expected["status"], "status")

    # 2. requirements
    actual_req = result.get("client_requirements", {})
    for k, v in expected.get("requirements", {}).items():
        _check(actual_req.get(k), v, f"req.{k}")

    # 3. components
    for comp_id, exp_fields in expected.get("components", {}).items():
        actual_comp = _get_component(result, comp_id)
        _check(bool(actual_comp), True, f"comp.{comp_id}.present")
        for k, v in exp_fields.items():
            _check(actual_comp.get(k) if actual_comp else None, v, f"comp.{comp_id}.{k}")

    # 4. no_hallucination
    for k in expected.get("no_hallucination", []):
        _check(actual_req.get(k), None, f"req.{k}(no_halluc)")

    # 5. follow_up_contains
    if "follow_up_contains" in expected:
        fup = (result.get("follow_up_question") or "").lower()
        substr = expected["follow_up_contains"].lower()
        ok = substr in fup
        field_results.append({"field": "follow_up_contains", "ok": ok,
                               "expected": substr, "actual": fup[:120]})
        if not ok:
            failures.append(f"  follow_up missing {substr!r}. got: {fup[:150]!r}")

    asserted = len(field_results)
    correct = sum(1 for f in field_results if f["ok"])

    # determine category prefix
    prefix = next((p for p in _CATEGORIES if scenario.id.startswith(p + "_")
                   or scenario.id.startswith(p + "2_")), "other")
    # fix: match longest prefix
    prefix = max(
        (p for p in _CATEGORIES if scenario.id.startswith(p + "_")),
        key=len,
        default="other",
    )

    _results.append({
        "id": scenario.id,
        "description": scenario.description,
        "category": prefix,
        "asserted": asserted,
        "correct": correct,
        "passed": len(failures) == 0,
        "field_results": field_results,
        "llm_meta": meta,
    })
    _persist_progress()

    if failures:
        pytest.fail(
            f"\n[{scenario.id}] {scenario.description}\n"
            f"FAILURES ({len(failures)}/{asserted}):\n" + "\n".join(failures) +
            f"\n\nFull result:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _save_json_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"results_{_PROVIDER}.json"
    # strip non-serialisable objects before saving
    safe = []
    for r in _results:
        safe.append({k: v for k, v in r.items() if k != "llm_meta"})
    out.write_text(json.dumps(safe, ensure_ascii=False, indent=2))
    return out


def _make_charts() -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np
    except ImportError:
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    # ── helpers ──────────────────────────────────────────────────────────────
    def _cat_stats() -> dict[str, dict]:
        stats: dict[str, dict] = {}
        for r in _results:
            cat = r["category"]
            s = stats.setdefault(cat, {"pass": 0, "total": 0, "correct": 0, "asserted": 0})
            s["total"] += 1
            s["pass"] += int(r["passed"])
            s["correct"] += r["correct"]
            s["asserted"] += r["asserted"]
        return stats

    cat_stats = _cat_stats()

    # ── 1. Category pass-rate bar chart ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    labels, rates, colors = [], [], []
    for prefix, (label, color) in _CATEGORIES.items():
        if prefix not in cat_stats:
            continue
        s = cat_stats[prefix]
        labels.append(label)
        rates.append(100 * s["pass"] / s["total"] if s["total"] else 0)
        colors.append(color)

    y_pos = range(len(labels))
    bars = ax.barh(list(y_pos), rates, color=colors, height=0.55, alpha=0.88)
    ax.set_xlim(0, 108)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("Pass rate (%)", fontsize=11)
    ax.set_title("Відсоток успішних тест-кейсів за категорією", fontsize=13, fontweight="bold", pad=14)
    for bar, rate in zip(bars, rates):
        ax.text(rate + 1, bar.get_y() + bar.get_height() / 2,
                f"{rate:.0f}%", va="center", fontsize=10, fontweight="bold")
    ax.axvline(80, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(80.5, len(labels) - 0.5, "80%", color="gray", fontsize=9)
    plt.tight_layout()
    fig.savefig(REPORTS_DIR / "category_pass_rate.png", bbox_inches="tight")
    plt.close(fig)

    # ── 2. Field-level failure frequency (top-20) ────────────────────────────
    from collections import Counter
    fail_counter: Counter = Counter()
    for r in _results:
        for fr in r["field_results"]:
            if not fr["ok"]:
                # normalise field names for grouping
                field = fr["field"]
                if field.startswith("comp.") and ".present" not in field:
                    parts = field.split(".")
                    field = ".".join(parts[2:]) if len(parts) >= 3 else field
                fail_counter[field] += 1

    if fail_counter:
        top_fields = fail_counter.most_common(20)
        field_names = [f for f, _ in reversed(top_fields)]
        field_counts = [c for _, c in reversed(top_fields)]

        fig, ax = plt.subplots(figsize=(10, max(4, len(field_names) * 0.42)))
        palette = ["#C44E52" if c >= 5 else "#DD8452" if c >= 3 else "#4C72B0"
                   for c in field_counts]
        bars = ax.barh(field_names, field_counts, color=palette, height=0.6, alpha=0.88)
        ax.set_xlabel("Кількість провалів", fontsize=11)
        ax.set_title("Найчастіші помилки по полях (топ-20)", fontsize=13,
                     fontweight="bold", pad=14)
        for bar, cnt in zip(bars, field_counts):
            ax.text(cnt + 0.1, bar.get_y() + bar.get_height() / 2,
                    str(cnt), va="center", fontsize=9)
        legend_patches = [
            mpatches.Patch(color="#C44E52", label="≥5 провалів"),
            mpatches.Patch(color="#DD8452", label="3–4 провали"),
            mpatches.Patch(color="#4C72B0", label="1–2 провали"),
        ]
        ax.legend(handles=legend_patches, fontsize=9, loc="lower right")
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "field_failure_freq.png", bbox_inches="tight")
        plt.close(fig)

    # ── 3. Radar / Spider chart — F1 per category ────────────────────────────
    cat_f1: dict[str, float] = {}
    cat_labels_merged: dict[str, str] = {
        "ext":    "Базова\nекстракція",
        "conf":   "Тест на\nплутанину",
        "multi":  "Multi-turn",
        "guard":  "Guardrails",
        "edge":   "Edge\ncases",
        "stress": "Stress\ntests",
    }
    for group_prefix, display in cat_labels_merged.items():
        combined = [r for r in _results
                    if r["category"] in (group_prefix, group_prefix + "2", group_prefix + "3", group_prefix + "4")]
        if not combined:
            continue
        total_a = sum(r["asserted"] for r in combined)
        total_c = sum(r["correct"] for r in combined)
        f1 = total_c / total_a if total_a else 0
        cat_f1[display] = round(f1 * 100, 1)

    if len(cat_f1) >= 3:
        cats = list(cat_f1.keys())
        vals = [cat_f1[c] for c in cats]
        N = len(cats)
        angles = [n / float(N) * 2 * 3.14159 for n in range(N)]
        angles += angles[:1]
        vals_plot = vals + vals[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
        ax.set_theta_offset(3.14159 / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(cats, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color="grey")
        ax.plot(angles, vals_plot, "o-", linewidth=2, color="#4C72B0")
        ax.fill(angles, vals_plot, alpha=0.22, color="#4C72B0")
        for angle, val in zip(angles[:-1], vals):
            ax.text(angle, val + 6, f"{val:.0f}%", ha="center", va="center",
                    fontsize=9, fontweight="bold", color="#4C72B0")
        ax.set_title("Field Extraction Score за категорією", fontsize=12,
                     fontweight="bold", pad=20)
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "radar_category_f1.png", bbox_inches="tight")
        plt.close(fig)

    # ── 4. Overall F1 gauge ───────────────────────────────────────────────────
    total_a = sum(r["asserted"] for r in _results)
    total_c = sum(r["correct"] for r in _results)
    f1_overall = total_c / total_a if total_a else 0

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 0.6)
    ax.axis("off")

    # Gauge background arc
    theta = np.linspace(0, np.pi, 200)
    for i, (t_start, t_end, col) in enumerate([
        (0, np.pi * 0.5,  "#C44E52"),
        (np.pi * 0.5, np.pi * 0.75, "#DD8452"),
        (np.pi * 0.75, np.pi, "#55A868"),
    ]):
        t = np.linspace(t_start, t_end, 100)
        ax.fill_between(
            0.5 + 0.38 * np.cos(t),
            0.02 + 0.38 * np.sin(t),
            0.02 + 0.28 * np.sin(t),
            color=col, alpha=0.35,
        )
    # Needle
    needle_angle = np.pi * (1 - f1_overall)
    ax.annotate(
        "", xy=(0.5 + 0.33 * np.cos(needle_angle), 0.02 + 0.33 * np.sin(needle_angle)),
        xytext=(0.5, 0.02),
        arrowprops={"arrowstyle": "-|>", "lw": 2.5, "color": "#2d2d2d"},
    )
    ax.add_patch(plt.Circle((0.5, 0.02), 0.025, color="#2d2d2d"))
    ax.text(0.5, 0.27, f"{f1_overall * 100:.1f}%", ha="center", va="center",
            fontsize=28, fontweight="bold", color="#2d2d2d")
    ax.text(0.5, 0.12, "Field Extraction F1", ha="center", va="center",
            fontsize=12, color="#555")
    ax.text(0.12, 0.01, "Низько", ha="center", fontsize=9, color="#C44E52")
    ax.text(0.5, 0.01, "Добре", ha="center", fontsize=9, color="#DD8452")
    ax.text(0.88, 0.01, "Відмінно", ha="center", fontsize=9, color="#55A868")
    ax.set_title("Загальна метрика якості екстракції", fontsize=12,
                 fontweight="bold", pad=8)
    plt.tight_layout()
    fig.savefig(REPORTS_DIR / "f1_gauge.png", bbox_inches="tight")
    plt.close(fig)


def _rich_report() -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
    except ImportError:
        return

    console = Console()

    total_a = sum(r["asserted"] for r in _results)
    total_c = sum(r["correct"] for r in _results)
    total_s = len(_results)
    passing_s = sum(1 for r in _results if r["passed"])
    f1 = total_c / total_a if total_a else 0.0

    # ── Summary panel ─────────────────────────────────────────────────────────
    f1_color = "green" if f1 >= 0.85 else "yellow" if f1 >= 0.70 else "red"
    pass_color = "green" if passing_s / total_s >= 0.85 else "yellow" if passing_s / total_s >= 0.70 else "red"

    summary = (
        f"[bold]Сценаріїв:[/bold]  {total_s}   "
        f"[bold]Пройшло:[/bold] [{pass_color}]{passing_s}/{total_s} "
        f"({100*passing_s/total_s:.1f}%)[/{pass_color}]   "
        f"[bold]Field F1:[/bold] [{f1_color}]{f1*100:.1f}%[/{f1_color}]"
    )
    console.print()
    console.print(Panel(summary, title="[bold cyan]EVALUATION RESULTS[/bold cyan]",
                        border_style="cyan", expand=False))

    # ── Category table ─────────────────────────────────────────────────────────
    table = Table(
        title="Результати за категоріями",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
        title_style="bold",
    )
    table.add_column("Категорія", style="bold", min_width=22)
    table.add_column("Пройшло", justify="center", min_width=12)
    table.add_column("Pass rate", justify="center", min_width=10)
    table.add_column("Field F1", justify="center", min_width=10)
    table.add_column("Провалених полів", justify="center", min_width=16)

    # group by merged category (ext+ext2, conf+conf2 etc.)
    group_map = {
        "Базова екстракція":  ["ext", "ext2", "ext3", "ext4"],
        "Тест на плутанину":  ["conf", "conf2", "conf3"],
        "Multi-turn":         ["multi", "multi2", "multi3", "multi4"],
        "Guardrails":         ["guard", "guard2", "guard3", "guard4"],
        "Edge cases":         ["edge", "edge2", "edge3", "edge4"],
        "Stress tests":       ["stress"],
    }

    for group_label, prefixes in group_map.items():
        rows = [r for r in _results if r["category"] in prefixes]
        if not rows:
            continue
        g_pass = sum(1 for r in rows if r["passed"])
        g_total = len(rows)
        g_correct = sum(r["correct"] for r in rows)
        g_asserted = sum(r["asserted"] for r in rows)
        g_failed_fields = sum(r["asserted"] - r["correct"] for r in rows)
        g_f1 = g_correct / g_asserted if g_asserted else 0
        rate = g_pass / g_total if g_total else 0

        rate_color = "green" if rate >= 0.85 else "yellow" if rate >= 0.70 else "red"
        f1_c = "green" if g_f1 >= 0.90 else "yellow" if g_f1 >= 0.75 else "red"

        table.add_row(
            group_label,
            f"[{rate_color}]{g_pass}/{g_total}[/{rate_color}]",
            f"[{rate_color}]{rate*100:.0f}%[/{rate_color}]",
            f"[{f1_c}]{g_f1*100:.1f}%[/{f1_c}]",
            f"[red]{g_failed_fields}[/red]" if g_failed_fields else "[green]0[/green]",
        )

    console.print()
    console.print(table)

    # ── Failures detail ────────────────────────────────────────────────────────
    failed = [r for r in _results if not r["passed"]]
    if failed:
        fail_table = Table(
            title=f"Провалені сценарії ({len(failed)})",
            box=box.SIMPLE_HEAD,
            header_style="bold red",
            title_style="bold red",
        )
        fail_table.add_column("ID", style="dim", min_width=42)
        fail_table.add_column("Опис", min_width=40)
        fail_table.add_column("Вірно", justify="center", min_width=10)
        for r in failed:
            pct = 100 * r["correct"] / r["asserted"] if r["asserted"] else 0
            pct_color = "yellow" if pct >= 60 else "red"
            fail_table.add_row(
                r["id"],
                r["description"][:55],
                f"[{pct_color}]{r['correct']}/{r['asserted']} ({pct:.0f}%)[/{pct_color}]",
            )
        console.print()
        console.print(fail_table)

    # ── Charts path ───────────────────────────────────────────────────────────
    charts = list(REPORTS_DIR.glob("*.png")) if REPORTS_DIR.exists() else []
    if charts:
        console.print()
        console.print(Panel(
            "\n".join(f"  [cyan]{p.name}[/cyan]" for p in sorted(charts)),
            title="[bold green]Збережені графіки[/bold green]",
            border_style="green",
            expand=False,
        ))

    console.print()


# ---------------------------------------------------------------------------
# pytest hook → see conftest.py (hooks in test files are not called by pytest)
# ---------------------------------------------------------------------------
