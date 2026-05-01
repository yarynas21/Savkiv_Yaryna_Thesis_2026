"""
LLM Pipeline Benchmark
======================
Runs the full production pipeline (technologist → validation → generation)
for 3 realistic orders and measures:
  - Wall-clock time per agent and total
  - Token usage (input / output) per agent
  - Estimated USD cost (GPT-4o pricing)

Results saved to: tests/eval/reports/llm_benchmark.json

Usage:
    cd Savkiv_Yaryna_Thesis_2026
    PYTHONPATH=backend python tests/eval/benchmark_llm.py

Requirements:
    .env with OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic)
    No database needed — uses seed SQL fallback for cost rates.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Load .env if present
_env_file = Path(__file__).resolve().parents[2] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from agents.technologist.node import technologist_node
from agents.validation.node import validation_node
from agents.generation.node import generation_node
from tools.llm_eval_metrics import (
    calculate_cost_from_rows,
    gpt_4o_pricing,
    calculate_latency_metrics,
)

# ---------------------------------------------------------------------------
# Pricing tables for all supported models
# ---------------------------------------------------------------------------
_PRICING = {
    "gpt-4o":              {"input_per_1m_usd": 2.50, "output_per_1m_usd": 10.00},
    "claude-sonnet-4-6":   {"input_per_1m_usd": 3.00, "output_per_1m_usd": 15.00},
    # aliases for model name variants returned by API
    "claude-sonnet-4":     {"input_per_1m_usd": 3.00, "output_per_1m_usd": 15.00},
}

def _pricing_for_model(model_name: str) -> dict:
    for key, pricing in _PRICING.items():
        if key in model_name:
            return pricing
    return gpt_4o_pricing()  # default fallback


# ---------------------------------------------------------------------------
# Order scenarios (client_requirements + product_components → state dict)
# ---------------------------------------------------------------------------

ORDERS = [
    {
        "name": "Вовк в овечій шкурі — повний комплект",
        "narad": "20862 + 20828 + 20909",
        "client_requirements": {
            "client_name": "Орнер (Кирило Орднер)",
            "product_name": "Гра «Вовк в овечій шкурі»",
            "quantity": 2000,
            "deadline_days": 30,
            "finish": "matt_lamination",
            "print_colors": "4+4",
        },
        "product_components": [
            {
                "id": "rigid_box",
                "component_name": "Коробка",
                "size_mm": [150, 90, 60],
                "material_cover": "sbb_160",
                "gsm": 160,
                "print_colors": "4+0",
            },
            {
                "id": "card_deck",
                "component_name": "Картки 448 шт.",
                "card_size_mm": [85, 55],
                "cards_per_kit": 448,
                "gsm": 250,
                "print_colors": "4+4",
            },
            {
                "id": "rulebook_thin",
                "component_name": "Інструкція",
                "size_mm": [148, 170],
                "fold_count": 1,
                "gsm": 150,
                "print_colors": "4+4",
            },
        ],
    },
    {
        "name": "Гра про емоції (Польська) — повний комплект",
        "narad": "20993 + 21006 + 21009",
        "client_requirements": {
            "client_name": "Мемогеймс (Грицик М.С.)",
            "product_name": "Гра «Про емоції» Польська",
            "quantity": 2000,
            "deadline_days": 23,
            "finish": "matt_lamination",
        },
        "product_components": [
            {
                "id": "rigid_box",
                "component_name": "Коробка",
                "size_mm": [148, 100, 50],
                "material_cover": "sbb_160",
                "gsm": 160,
                "print_colors": "4+0",
            },
            {
                "id": "card_deck",
                "component_name": "Картки 53 шт.",
                "card_size_mm": [90, 130],
                "cards_per_kit": 53,
                "gsm": 300,
                "print_colors": "4+4",
            },
            {
                "id": "rulebook_thin",
                "component_name": "Інструкція",
                "size_mm": [135, 160],
                "fold_count": 1,
                "gsm": 150,
                "print_colors": "4+4",
            },
        ],
    },
    {
        "name": "Факт чи думка — картки",
        "narad": "20872",
        "client_requirements": {
            "client_name": "Мемогеймс (Грінік М.С.)",
            "product_name": "Карти «Факт чи думка»",
            "quantity": 3000,
            "deadline_days": 14,
            "finish": "no_lamination",
        },
        "product_components": [
            {
                "id": "card_deck",
                "component_name": "Картки 90 шт.",
                "card_size_mm": [50, 70],
                "cards_per_kit": 90,
                "gsm": 300,
                "print_colors": "4+4",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def _make_state(order: dict) -> dict:
    return {
        "messages": [],
        "client_requirements": order["client_requirements"],
        "product_components": order["product_components"],
        "requirements_complete": True,
        "production_routes": [],
        "validation_status": "pending",
        "ambiguities": [],
        "human_feedback": None,
        "work_order": None,
        "cost_estimates": None,
        "llm_eval": {"rows": [], "session_call_count": 0},
        "current_agent": "",
        "iteration": 0,
    }


def run_order(order: dict) -> dict:
    print(f"\n{'='*60}")
    print(f"  {order['name']}  (Наряд {order['narad']})")
    print(f"  qty={order['client_requirements']['quantity']}, "
          f"components={len(order['product_components'])}")
    print(f"{'='*60}")

    state = _make_state(order)
    timings: dict[str, float] = {}
    wall_start = time.perf_counter()

    # --- 1. Technologist ---
    print("  [1/3] Technologist...", end=" ", flush=True)
    t0 = time.perf_counter()
    state.update(technologist_node(state))
    timings["technologist_s"] = round(time.perf_counter() - t0, 2)
    print(f"{timings['technologist_s']}s  "
          f"routes={len(state.get('production_routes', []))}")

    # --- 2. Validation ---
    print("  [2/3] Validation...", end=" ", flush=True)
    t0 = time.perf_counter()
    state.update(validation_node(state))
    timings["validation_s"] = round(time.perf_counter() - t0, 2)
    print(f"{timings['validation_s']}s  "
          f"status={state.get('validation_status')}")

    # --- 3. Generation ---
    print("  [3/3] Generation...", end=" ", flush=True)
    t0 = time.perf_counter()
    state.update(generation_node(state))
    timings["generation_s"] = round(time.perf_counter() - t0, 2)
    cost = state.get("cost_estimates", {})
    print(f"{timings['generation_s']}s  "
          f"cost={cost.get('total_cost', 0):,.0f} грн")

    timings["total_s"] = round(time.perf_counter() - wall_start, 2)

    # --- Aggregate token metrics ---
    llm_eval = state.get("llm_eval") or {}
    rows = llm_eval.get("rows", [])

    per_agent: dict[str, dict] = {}
    for row in rows:
        agent = row.get("agent", "unknown")
        if agent not in per_agent:
            per_agent[agent] = {
                "model": row.get("model", "unknown"),
                "latency_ms": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
            }
        per_agent[agent]["latency_ms"] += float(row.get("latency_ms", 0))
        per_agent[agent]["input_tokens"] += int(row.get("input_tokens", 0))
        per_agent[agent]["output_tokens"] += int(row.get("output_tokens", 0))
        per_agent[agent]["calls"] += 1

    total_in  = sum(r.get("input_tokens", 0) for r in rows)
    total_out = sum(r.get("output_tokens", 0) for r in rows)
    model_name = rows[0].get("model", "gpt-4o") if rows else "gpt-4o"
    pricing = _pricing_for_model(model_name)
    cost_usd = round(
        (total_in * pricing["input_per_1m_usd"] +
         total_out * pricing["output_per_1m_usd"]) / 1_000_000,
        5,
    )

    # --- Print summary ---
    print(f"\n  Token summary ({model_name}):")
    for agent, m in per_agent.items():
        print(f"    {agent:12s}  in={m['input_tokens']:>6}  out={m['output_tokens']:>5}"
              f"  latency={m['latency_ms']:.0f}ms")
    print(f"    {'TOTAL':12s}  in={total_in:>6}  out={total_out:>5}"
          f"  cost=${cost_usd:.5f}")
    print(f"  Wall time: {timings['total_s']}s")

    return {
        "order": order["name"],
        "narad": order["narad"],
        "quantity": order["client_requirements"]["quantity"],
        "components": [c["id"] for c in order["product_components"]],
        "timings_s": timings,
        "per_agent": per_agent,
        "tokens": {
            "total_input": total_in,
            "total_output": total_out,
            "total": total_in + total_out,
        },
        "model": model_name,
        "pricing_per_1m_usd": pricing,
        "cost_usd": cost_usd,
        "cost_uah_estimate": round(cost_usd * 41, 2),  # ~41 UAH/USD
        "production_cost_uah": cost.get("total_cost", 0),
        "price_per_unit_uah": cost.get("price_per_unit", 0),
        "validation_status": state.get("validation_status"),
        "routes_count": len(state.get("production_routes", [])),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "="*60)
    print("  Dyz-Art MAS — LLM Pipeline Benchmark")
    print("="*60)

    provider = os.getenv("LLM_PROVIDER", "openai")
    print(f"  Provider: {provider}")

    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("\n  ERROR: OPENAI_API_KEY not set.")
        print("  Set it in .env or run:  export OPENAI_API_KEY=sk-...")
        sys.exit(1)
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("\n  ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    results = []
    for order in ORDERS:
        try:
            rec = run_order(order)
            results.append(rec)
        except Exception as exc:
            print(f"\n  FAILED: {order['name']}")
            print(f"  {type(exc).__name__}: {exc}")
            results.append({
                "order": order["name"],
                "error": str(exc),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })

    # --- Save report ---
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    out = report_dir / "llm_benchmark.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    # --- Print overall summary ---
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"  {'Order':<42}  {'Time':>6}  {'Tokens':>7}  {'Cost USD':>9}")
    print(f"  {'-'*42}  {'-'*6}  {'-'*7}  {'-'*9}")
    for r in results:
        if "error" in r:
            print(f"  {r['order']:<42}  ERROR: {r['error'][:30]}")
            continue
        print(f"  {r['order']:<42}  "
              f"{r['timings_s']['total_s']:>5.1f}s  "
              f"{r['tokens']['total']:>7,}  "
              f"${r['cost_usd']:>8.5f}")

    total_cost = sum(r.get("cost_usd", 0) for r in results if "error" not in r)
    total_tokens = sum(r.get("tokens", {}).get("total", 0) for r in results if "error" not in r)
    print(f"  {'TOTAL':<42}  {'':>6}  {total_tokens:>7,}  ${total_cost:>8.5f}")
    print(f"\n  Report saved → {out}")


if __name__ == "__main__":
    main()


