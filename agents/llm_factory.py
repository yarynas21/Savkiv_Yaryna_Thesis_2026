"""
LLM Factory — returns the correct LangChain chat model based on .env settings.

Supported providers:
  - openai     → ChatOpenAI (GPT-4o by default)
  - anthropic  → ChatAnthropic (claude-3-5-sonnet by default)
  - google     → ChatGoogleGenerativeAI (gemini-1.5-pro by default)
"""

import os
from functools import lru_cache
from langchain_core.language_models import BaseChatModel
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Reads LLM_PROVIDER from the environment and returns the matching model.
    Defaults to OpenAI if not set.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    logger.info(f"Initializing LLM: provider={provider}")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        logger.info(f"Using OpenAI model: {model}")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set in environment")
        return ChatOpenAI(
            model=model,
            temperature=0.2,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        logger.info(f"Using Anthropic model: {model}")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set in environment")
        return ChatAnthropic(
            model=model,
            temperature=0.2,
        )

    elif provider in ("google", "gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")
        logger.info(f"Using Google model: {model}")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set in environment")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.2,
        )

    else:
        logger.error(f"Unknown LLM_PROVIDER: {provider}")
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider}'. "
            "Supported values: openai, anthropic, google"
        )
