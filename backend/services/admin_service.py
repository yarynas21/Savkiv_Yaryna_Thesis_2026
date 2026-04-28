"""
Admin-side orchestration: thin wrappers around the admin repositories that
validate/normalise data before forwarding it to SQL.

Kept here so routers don't reach into repositories directly and so business
rules (e.g. "admin can't delete themselves") live in one place.
"""

from __future__ import annotations

import os
from typing import Any

from db.repositories import admin as admin_repo
from db.repositories import users as users_repo
from utils.logger import get_logger

logger = get_logger(__name__)


# game_components

def list_game_components() -> list[dict]:
    return admin_repo.list_game_components()


def upsert_game_component(payload: dict[str, Any]) -> dict:
    required = {"id", "name", "category", "unit", "price_uah"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    return admin_repo.upsert_game_component(payload)


def delete_game_component(component_id: str) -> bool:
    return admin_repo.delete_game_component(component_id)


# cost_rates

def list_cost_rates() -> list[dict]:
    return admin_repo.list_cost_rates()


def upsert_cost_rate(payload: dict[str, Any]) -> dict:
    required = {"category", "rate_key", "value_numeric"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    return admin_repo.upsert_cost_rate(payload)


def delete_cost_rate(category: str, rate_key: str) -> bool:
    return admin_repo.delete_cost_rate(category, rate_key)


# papers

def list_papers() -> list[dict]:
    return admin_repo.list_papers()


def upsert_paper(payload: dict[str, Any]) -> dict:
    required = {"id", "name", "type", "weight_gsm", "compatible_with", "typical_use"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    return admin_repo.upsert_paper(payload)


def delete_paper(paper_id: str) -> bool:
    return admin_repo.delete_paper(paper_id)


# users

def list_users() -> list[dict]:
    return users_repo.list_users()


def create_user(payload: dict[str, Any]) -> dict:
    required = {"email", "username", "password"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    return users_repo.create_user(
        email=payload["email"],
        username=payload["username"],
        password=payload["password"],
        role=payload.get("role", "client"),
        is_active=bool(payload.get("is_active", True)),
    )


def update_user(user_id: str, payload: dict[str, Any]) -> dict:
    return users_repo.update_user(
        user_id,
        role=payload.get("role"),
        is_active=payload.get("is_active"),
        password=payload.get("password"),
        email=payload.get("email"),
    )


def delete_user(user_id: str, *, acting_user_id: str | None = None) -> bool:
    if acting_user_id and str(acting_user_id) == str(user_id):
        raise PermissionError("Admins cannot delete their own account")
    return users_repo.delete_user(user_id)


# runtime llm setting

_ALLOWED_GLOBAL_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-6",
}


def _validate_llm_runtime_setting(payload: dict[str, Any]) -> tuple[str, str]:
    """Validate provider/model pair and return normalized values."""
    provider = str(payload.get("provider", "")).strip().lower()
    model = str(payload.get("model", "")).strip()

    if provider not in _ALLOWED_GLOBAL_MODELS:
        raise ValueError("Unsupported provider. Allowed: openai, anthropic")

    expected_model = _ALLOWED_GLOBAL_MODELS[provider]
    if model != expected_model:
        raise ValueError(
            f"Unsupported model for provider '{provider}'. Expected: {expected_model}"
        )

    return provider, model


def get_llm_runtime_setting() -> dict[str, Any]:
    row = admin_repo.get_llm_runtime_setting("global")
    if row:
        try:
            provider, model = _validate_llm_runtime_setting(row)
            row["provider"] = provider
            row["model"] = model
            return row
        except ValueError as exc:
            logger.warning(
                "Invalid LLM runtime setting in DB, falling back to default. "
                "provider=%r model=%r error=%s",
                row.get("provider"),
                row.get("model"),
                exc,
            )
    # Safe default when DB row does not exist yet.
    return {
        "setting_key": "global",
        "provider": "openai",
        "model": "gpt-4o",
        "updated_by": None,
        "updated_at": None,
    }


def update_llm_runtime_setting(payload: dict[str, Any], *, actor_user_id: str | None = None) -> dict[str, Any]:
    provider, model = _validate_llm_runtime_setting(payload)

    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError(
            "Не вдалося перемкнути модель на Sonnet 4.6: відсутній `ANTHROPIC_API_KEY` "
            "у конфігурації бекенду (.env). Додайте ключ і спробуйте ще раз."
        )

    return admin_repo.upsert_llm_runtime_setting(
        {
            "setting_key": "global",
            "provider": provider,
            "model": model,
            "updated_by": actor_user_id,
        }
    )
