from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
from typing import TypedDict


class SessionEval(TypedDict, total=False):
    latency_ms: float
    input_tokens: int
    output_tokens: int


class ModelPricing(TypedDict):
    input_per_1m_usd: float
    output_per_1m_usd: float


def _rollup_conversation(rows: Iterable[SessionEval]) -> list[SessionEval]:
    data = list(rows)
    if not data:
        return []

    return [
        {
            "latency_ms": sum(float(r.get("latency_ms", 0.0)) for r in data if float(r.get("latency_ms", 0.0)) >= 0),
            "input_tokens": sum(int(r.get("input_tokens", 0)) for r in data),
            "output_tokens": sum(int(r.get("output_tokens", 0)) for r in data),
        },
    ]


def calculate_latency_metrics(
    latency_ms: Iterable[float],
    scope: Literal["call", "conversation"] = "call",
) -> dict[str, float]:
    raw_values = list(latency_ms)
    if scope == "conversation":
        values = [sum(x for x in raw_values if x >= 0)]
    else:
        values = sorted(x for x in raw_values if x >= 0)
    if not values:
        return {"latency_p50_min": 0.0, "latency_p95_min": 0.0}

    def _percentile(sorted_values: list[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        idx = int((len(sorted_values) - 1) * p)
        return sorted_values[idx]

    return {
        "latency_p50_min": round(_percentile(values, 0.50) / 60_000, 4),
        "latency_p95_min": round(_percentile(values, 0.95) / 60_000, 4),
    }


def calculate_cost_usd(
    input_tokens_total: int,
    output_tokens_total: int,
    pricing: ModelPricing,
) -> float:
    input_cost = (input_tokens_total * pricing["input_per_1m_usd"]) / 1_000_000
    output_cost = (output_tokens_total * pricing["output_per_1m_usd"]) / 1_000_000
    return round(input_cost + output_cost, 6)


def calculate_cost_from_rows(
    rows: Iterable[SessionEval],
    pricing: ModelPricing,
    scope: Literal["call", "conversation"] = "call",
) -> dict[str, float]:
    if scope == "conversation":
        data = _rollup_conversation(rows)
    else:
        data = list(rows)
    total_input = sum(int(r.get("input_tokens", 0)) for r in data)
    total_output = sum(int(r.get("output_tokens", 0)) for r in data)
    total_cost = calculate_cost_usd(total_input, total_output, pricing)

    return {
        "input_tokens_total": float(total_input),
        "output_tokens_total": float(total_output),
        "total_cost_usd": total_cost,
    }


def gpt_4o_pricing() -> ModelPricing:
    # OpenAI GPT-4o pricing used in your previous estimate.
    return {"input_per_1m_usd": 5.0, "output_per_1m_usd": 15.0}

