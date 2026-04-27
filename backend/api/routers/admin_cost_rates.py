"""
Admin CRUD for ``cost_rates`` (composite key: category + rate_key).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_role
from api.schemas.admin import CostRateIn, CostRateOut, CostRatePatch
from services import admin_service

router = APIRouter(prefix="/admin/cost_rates", tags=["admin"])


@router.get("", response_model=list[CostRateOut])
def list_rates(_: dict = Depends(require_role("admin"))) -> list[dict]:
    return admin_service.list_cost_rates()


@router.post("", response_model=CostRateOut, status_code=status.HTTP_201_CREATED)
def create_rate(
    body: CostRateIn,
    _: dict = Depends(require_role("admin")),
) -> dict:
    try:
        return admin_service.upsert_cost_rate(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{category}/{rate_key}", response_model=CostRateOut)
def upsert_rate(
    category: str,
    rate_key: str,
    body: CostRatePatch,
    _: dict = Depends(require_role("admin")),
) -> dict:
    payload = {
        k: v for k, v in body.model_dump(exclude_none=True).items()
    }
    payload["category"] = category
    payload["rate_key"] = rate_key
    if "value_numeric" not in payload:
        raise HTTPException(status_code=400, detail="value_numeric is required")
    return admin_service.upsert_cost_rate(payload)


@router.delete("/{category}/{rate_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate(
    category: str,
    rate_key: str,
    _: dict = Depends(require_role("admin")),
) -> None:
    ok = admin_service.delete_cost_rate(category, rate_key)
    if not ok:
        raise HTTPException(status_code=404, detail="Rate not found")
