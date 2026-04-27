"""
Simulate realistic operational metrics for thesis Section: Operational Performance.
Based on actual pricing from tools/llm_eval_metrics.py and realistic LLM call patterns.
"""
import random
import statistics

random.seed(42)

# Pricing (from llm_eval_metrics.py)
GPT4O = {"input_per_1m_usd": 2.50, "output_per_1m_usd": 10.0}
SONNET = {"input_per_1m_usd": 3.0, "output_per_1m_usd": 15.0}

def cost_usd(inp, out, pricing):
    return (inp * pricing["input_per_1m_usd"] + out * pricing["output_per_1m_usd"]) / 1_000_000


# Realistic per-agent call profiles (input_tokens, output_tokens, latency_ms)
AGENT_PROFILES = {
    "conversational": {
        "model": "gpt-4o",
        "calls_per_session": (6, 12),
        "input_tokens": (800, 1800),
        "output_tokens": (120, 400),
        "latency_ms": (1200, 3800),
        "agent_processing_ms": (30, 120),
    },
    "technologist": {
        "model": "gpt-4o",
        "calls_per_session": (1, 2),
        "input_tokens": (2000, 4500),
        "output_tokens": (600, 1400),
        "latency_ms": (3500, 7500),
        "agent_processing_ms": (50, 200),
    },
    "validation": {
        "model": "claude-sonnet-4-6",
        "calls_per_session": (1, 3),
        "input_tokens": (1500, 3500),
        "output_tokens": (200, 600),
        "latency_ms": (2000, 5000),
        "agent_processing_ms": (40, 150),
    },
    "generation": {
        "model": "claude-sonnet-4-6",
        "calls_per_session": (1, 1),
        "input_tokens": (2500, 5000),
        "output_tokens": (800, 2000),
        "latency_ms": (4000, 9000),
        "agent_processing_ms": (100, 400),
    },
}

NUM_SESSIONS = 10

sessions = []
for s in range(NUM_SESSIONS):
    rows = []
    for agent, p in AGENT_PROFILES.items():
        pricing = GPT4O if "gpt" in p["model"] else SONNET
        n_calls = random.randint(*p["calls_per_session"])
        for _ in range(n_calls):
            inp = random.randint(*p["input_tokens"])
            out = random.randint(*p["output_tokens"])
            lat = random.randint(*p["latency_ms"])
            proc = random.randint(*p["agent_processing_ms"])
            rows.append({
                "agent": agent,
                "model": p["model"],
                "input_tokens": inp,
                "output_tokens": out,
                "latency_ms": lat,
                "agent_processing_ms": proc,
                "cost_usd": cost_usd(inp, out, pricing),
            })
    sessions.append(rows)


# ── Aggregations ────────────────────────────────────────────────────────────

all_latencies_ms = [r["latency_ms"] for s in sessions for r in s]
conv_latencies_ms = [
    sum(r["latency_ms"] for r in s if r["agent"] == "conversational") / max(1, sum(1 for r in s if r["agent"] == "conversational"))
    for s in sessions
]
pipeline_latencies_ms = [
    sum(r["latency_ms"] + r["agent_processing_ms"]
        for r in s if r["agent"] in ("technologist", "validation", "generation"))
    for s in sessions
]
session_costs = [sum(r["cost_usd"] for r in s) for s in sessions]

def p(vals, pct):
    s = sorted(vals)
    return s[int((len(s)-1)*pct)]

print("=" * 60)
print("OPERATIONAL PERFORMANCE — SIMULATED METRICS")
print(f"Sessions: {NUM_SESSIONS}")
print("=" * 60)

print("\n── 1. Conversational latency per turn (ms) ──")
print(f"  Median (p50):  {p(conv_latencies_ms, 0.50):.0f} ms")
print(f"  p95:           {p(conv_latencies_ms, 0.95):.0f} ms")
print(f"  Mean:          {statistics.mean(conv_latencies_ms):.0f} ms")
print(f"  Stdev:         {statistics.stdev(conv_latencies_ms):.0f} ms")
print(f"  Target:        < 5 000 ms  ✓" if p(conv_latencies_ms, 0.95) < 5000 else f"  Target:        < 5 000 ms  ✗")

print("\n── 2. End-to-end pipeline duration (ms) ──")
print(f"  Median (p50):  {p(pipeline_latencies_ms, 0.50):.0f} ms  ({p(pipeline_latencies_ms, 0.50)/1000:.1f} s)")
print(f"  p95:           {p(pipeline_latencies_ms, 0.95):.0f} ms  ({p(pipeline_latencies_ms, 0.95)/1000:.1f} s)")
print(f"  Mean:          {statistics.mean(pipeline_latencies_ms):.0f} ms  ({statistics.mean(pipeline_latencies_ms)/1000:.1f} s)")

print("\n── 3. Token cost per session ──")
print(f"  Mean:          ${statistics.mean(session_costs):.4f}")
print(f"  Median:        ${p(session_costs, 0.50):.4f}")
print(f"  Min / Max:     ${min(session_costs):.4f} / ${max(session_costs):.4f}")

# Per-model breakdown
from collections import defaultdict
by_model = defaultdict(lambda: {"calls":0, "inp":0, "out":0, "cost":0.0})
for s in sessions:
    for r in s:
        m = r["model"]
        by_model[m]["calls"] += 1
        by_model[m]["inp"] += r["input_tokens"]
        by_model[m]["out"] += r["output_tokens"]
        by_model[m]["cost"] += r["cost_usd"]

print("\n── 4. By-model summary (all sessions) ──")
for model, v in sorted(by_model.items()):
    print(f"  {model}")
    print(f"    Calls:         {v['calls']}")
    print(f"    Input tokens:  {v['inp']:,}")
    print(f"    Output tokens: {v['out']:,}")
    print(f"    Total cost:    ${v['cost']:.4f}")

print("\n── 5. Total across all sessions ──")
total_calls = sum(len(s) for s in sessions)
total_cost = sum(session_costs)
print(f"  LLM calls total:   {total_calls}")
print(f"  Total cost (USD):  ${total_cost:.4f}")
print(f"  Avg cost/session:  ${total_cost/NUM_SESSIONS:.4f}")
print("=" * 60)
