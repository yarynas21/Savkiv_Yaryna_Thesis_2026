"""
Admin CRUD for ``game_components`` (board-game parts catalog).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_role
from api.schemas.admin import GameComponentIn, GameComponentOut
from services import admin_service

router = APIRouter(prefix="/admin/game_components", tags=["admin"])


@router.get("", response_model=list[GameComponentOut])
def list_components(_: dict = Depends(require_role("admin"))) -> list[dict]:
    return admin_service.list_game_components()


@router.post("", response_model=GameComponentOut, status_code=status.HTTP_201_CREATED)
def create_component(
    body: GameComponentIn,
    _: dict = Depends(require_role("admin")),
) -> dict:
    try:
        return admin_service.upsert_game_component(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{component_id}", response_model=GameComponentOut)
def update_component(
    component_id: str,
    body: GameComponentIn,
    _: dict = Depends(require_role("admin")),
) -> dict:
    payload = body.model_dump()
    payload["id"] = component_id
    try:
        return admin_service.upsert_game_component(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_component(
    component_id: str,
    _: dict = Depends(require_role("admin")),
) -> None:
    ok = admin_service.delete_game_component(component_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Component not found")
