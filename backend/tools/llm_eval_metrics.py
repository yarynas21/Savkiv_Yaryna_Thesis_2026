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
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    input_cost = (input_tokens_total * pricing["input_per_1m_usd"]) / 1_000_000
    output_cost = (output_tokens_total * pricing["output_per_1m_usd"]) / 1_000_000
    # Cache read is billed at 10% of input price; cache creation at 25% extra
    cache_read_cost = (cache_read_tokens * pricing["input_per_1m_usd"] * 0.1) / 1_000_000
    cache_creation_cost = (cache_creation_tokens * pricing["input_per_1m_usd"] * 0.25) / 1_000_000
    return round(input_cost + output_cost + cache_read_cost + cache_creation_cost, 6)


def calculate_cost_from_rows(
    rows: Iterable[SessionEval],
    pricing: ModelPricing,
    scope: Literal["call", "conversation"] = "call",
) -> dict[str, float]:
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
    return {"input_per_1m_usd": 5.0, "output_per_1m_usd": 15.0}


_MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-4o": {"input_per_1m_usd": 5.0, "output_per_1m_usd": 15.0},
    "gpt-4o-mini": {"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.60},
    "gpt-4-turbo": {"input_per_1m_usd": 10.0, "output_per_1m_usd": 30.0},
    "gpt-3.5-turbo": {"input_per_1m_usd": 0.5, "output_per_1m_usd": 1.5},
    "claude-3-5-sonnet": {"input_per_1m_usd": 3.0, "output_per_1m_usd": 15.0},
    "claude-3-5-haiku": {"input_per_1m_usd": 0.8, "output_per_1m_usd": 4.0},
    "claude-3-opus": {"input_per_1m_usd": 15.0, "output_per_1m_usd": 75.0},
}


def pricing_for_model(model: str) -> ModelPricing:
    """Return pricing for the given model name, falling back to gpt-4o rates."""
    for key, pricing in _MODEL_PRICING.items():
        if key in model.lower():
            return pricing
    return gpt_4o_pricing()
