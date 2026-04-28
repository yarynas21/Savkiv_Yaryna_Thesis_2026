"""
LLM Factory — returns LangChain chat models based on .env and agent role.

Supported providers:
  - openai     → ChatOpenAI (GPT-4o by default)
  - anthropic  → ChatAnthropic (claude-3-5-sonnet by default)

Per-role model overrides (optional; fallback to global model for provider):
  OPENAI_MODEL_CLIENT_INTERFACE, OPENAI_MODEL_TECHNOLOGIST, ...
  ANTHROPIC_MODEL_CLIENT_INTERFACE, ...
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from agents.registry import AgentLLMRole
from utils.logger import get_logger

logger = get_logger(__name__)

_TEMPERATURE = 0.2

_ROLE_ENV_SUFFIX: dict[AgentLLMRole, str] = {
    "client_interface": "CLIENT_INTERFACE",
    "technologist": "TECHNOLOGIST",
    "validation": "VALIDATION",
    "generation": "GENERATION",
}


def _model_for_role_openai(role: AgentLLMRole) -> str:
    suffix = _ROLE_ENV_SUFFIX[role]
    return os.getenv(f"OPENAI_MODEL_{suffix}") or os.getenv("OPENAI_MODEL", "gpt-4o")


def _model_for_role_anthropic(role: AgentLLMRole) -> str:
    suffix = _ROLE_ENV_SUFFIX[role]
    return os.getenv(f"ANTHROPIC_MODEL_{suffix}") or os.getenv(
        "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"
    )


@lru_cache(maxsize=32)
def _build_llm(provider: str, model: str, temperature: float) -> BaseChatModel:
    """Створює один екземпляр чат-моделі (кеш за provider+model+temp)."""
    provider = provider.lower().strip()
    logger.debug(f"Building LLM: provider={provider}, model={model}")

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set in environment")
        return ChatOpenAI(model=model, temperature=temperature)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("ANTHROPIC_API_KEY not set in environment")
        return ChatAnthropic(model=model, temperature=temperature)

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider}'. "
        "Supported values: openai, anthropic"
    )


def _get_runtime_setting() -> tuple[str, str] | None:
    """Returns (provider, model) from DB runtime setting, or None on failure."""
    try:
        from services import admin_service
        row = admin_service.get_llm_runtime_setting()
        if row and row.get("provider") and row.get("model"):
            return row["provider"].lower().strip(), row["model"].strip()
    except Exception as exc:
        logger.warning(f"Could not read LLM runtime setting from DB: {exc}")
    return None


def get_llm_for_agent(role: AgentLLMRole) -> BaseChatModel:
    """Повертає чат-модель для конкретної ролі агента."""
    db_setting = _get_runtime_setting()
    if db_setting:
        provider, model = db_setting
    else:
        provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
        if provider == "openai":
            model = _model_for_role_openai(role)
        elif provider == "anthropic":
            model = _model_for_role_anthropic(role)
        else:
            logger.error(f"Unknown LLM_PROVIDER: {provider}")
            raise ValueError(
                f"Unknown LLM_PROVIDER='{provider}'. "
                "Supported values: openai, anthropic"
            )

    logger.info(f"LLM for agent role={role!r}, provider={provider}")
    logger.info(f"Resolved model for {role!r}: {model}")
    return _build_llm(provider, model, _TEMPERATURE)


def get_llm() -> BaseChatModel:
    """Зворотна сумісність: повертає модель для ролі client_interface."""
    return get_llm_for_agent("client_interface")
