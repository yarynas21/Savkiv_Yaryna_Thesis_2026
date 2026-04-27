"""
Admin endpoints for global runtime LLM model selection.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user_db, require_role
from api.schemas.admin import LlmRuntimeSettingIn, LlmRuntimeSettingOut
from services import admin_service

router = APIRouter(prefix="/admin/llm", tags=["admin"])


@router.get("/runtime", response_model=LlmRuntimeSettingOut)
def get_runtime_llm(_: dict = Depends(require_role("admin"))) -> LlmRuntimeSettingOut:
    row = admin_service.get_llm_runtime_setting()
    return LlmRuntimeSettingOut(
        setting_key=row.get("setting_key", "global"),
        provider=row["provider"],
        model=row["model"],
        updated_by=str(row["updated_by"]) if row.get("updated_by") else None,
        updated_at=row.get("updated_at"),
    )


@router.put("/runtime", response_model=LlmRuntimeSettingOut)
def set_runtime_llm(
    body: LlmRuntimeSettingIn,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("admin")),
) -> LlmRuntimeSettingOut:
    try:
        row = admin_service.update_llm_runtime_setting(
            body.model_dump(),
            actor_user_id=str(current_user["id"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return LlmRuntimeSettingOut(
        setting_key=row["setting_key"],
        provider=row["provider"],
        model=row["model"],
        updated_by=str(row["updated_by"]) if row.get("updated_by") else None,
        updated_at=row.get("updated_at"),
    )
