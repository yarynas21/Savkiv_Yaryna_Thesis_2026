from __future__ import annotations

import contextlib
import time
from typing import Any

from agents.conversational.schema import ClientExtractionOutput
from agents.json_parser import RobustJsonOutputParser
from utils.logger import get_logger

logger = get_logger(__name__)


def _extract_usage(raw: Any) -> tuple[int, int]:
    """Extract input/output token usage from a LangChain response object."""
    usage = getattr(raw, "usage_metadata", None) or {}
    if not usage and hasattr(raw, "response_metadata"):
        response_meta = getattr(raw, "response_metadata", {}) or {}
        usage = response_meta.get("token_usage", {}) or {}

    input_tokens = int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("input_token_count")
        or 0
    )
    output_tokens = int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("output_token_count")
        or 0
    )
    return input_tokens, output_tokens


def _model_name(raw: Any, llm: Any) -> str:
    if hasattr(raw, "response_metadata"):
        response_meta = getattr(raw, "response_metadata", {}) or {}
        model = response_meta.get("model_name") or response_meta.get("model")
        if model:
            return str(model)
    return str(getattr(llm, "model_name", getattr(llm, "model", "unknown")))


def _log_messages(messages: list) -> None:
    """Log each message in the conversation context at INFO level."""
    logger.info("─── LLM prompt (%d messages) ───────────────────────", len(messages))
    for i, msg in enumerate(messages):
        role = type(msg).__name__
        content = getattr(msg, "content", str(msg))
        preview = content if len(content) <= 800 else content[:800] + "…"
        logger.info("[%d] %s: %s", i, role, preview)
    logger.info("────────────────────────────────────────────────────")


def _invoke_llm(prompt, messages: list, llm) -> tuple[dict[str, Any], dict[str, Any]]:
    """Invoke the LLM chain using a three-tier fallback strategy.

    1. **Structured output** — attempts ``llm.with_structured_output`` with
       function-calling to get a typed ``ClientExtractionOutput`` directly.
    2. **JSON parser** — falls back to raw LLM output piped through
       ``RobustJsonOutputParser`` when structured output fails.
    3. **Plain text fallback** — invokes the chain without any parser and wraps
       the raw content in an ``incomplete`` envelope so downstream nodes can
       treat it as a follow-up question.

    Args:
        prompt: A ``ChatPromptTemplate`` that accepts a ``messages`` variable.
        messages: The current conversation history to pass to the prompt.
        llm: A LangChain chat model instance.

    Returns:
        Tuple of:
          1) extraction result dict (status/client_requirements/product_components/follow_up_question)
          2) invoke metadata dict (tier/model/latency/token usage)
    """
    _log_messages(messages)
    chain_input = {"messages": messages}
    started_at = time.perf_counter()

    with contextlib.suppress(Exception):
        structured = llm.with_structured_output(ClientExtractionOutput, method="function_calling")
        raw = (prompt | structured).invoke(chain_input)
        input_tokens, output_tokens = _extract_usage(raw)
        metadata = {
            "tier": "structured_output",
            "model": _model_name(raw, llm),
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usage_available": bool(input_tokens or output_tokens),
            "success": True,
        }
        if isinstance(raw, ClientExtractionOutput):
            logger.info("LLM tier: structured_output (function_calling)")
            return raw.model_dump(), metadata
        if isinstance(raw, dict):
            logger.info("LLM tier: structured_output (dict)")
            return raw, metadata

    logger.warning("LLM tier: structured_output failed, falling back to JSON parser")
    with contextlib.suppress(Exception):
        raw = (prompt | llm).invoke(chain_input)
        result = RobustJsonOutputParser().invoke(raw)
        input_tokens, output_tokens = _extract_usage(raw)
        logger.info("LLM tier: json_parser")
        return result, {
            "tier": "json_parser",
            "model": _model_name(raw, llm),
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usage_available": bool(input_tokens or output_tokens),
            "success": True,
        }

    logger.warning("LLM tier: JSON parser failed, falling back to plain text")
    raw = (prompt | llm).invoke(chain_input)
    input_tokens, output_tokens = _extract_usage(raw)
    return (
        {
            "status": "incomplete",
            "follow_up_question": getattr(raw, "content", str(raw)),
            "client_requirements": {},
            "product_components": [],
        },
        {
            "tier": "plain_text_fallback",
            "model": _model_name(raw, llm),
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usage_available": bool(input_tokens or output_tokens),
            "success": True,
        },
    )
