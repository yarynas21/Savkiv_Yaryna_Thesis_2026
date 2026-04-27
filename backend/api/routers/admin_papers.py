"""
Admin CRUD for ``papers``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_role
from api.schemas.admin import PaperIn, PaperOut
from services import admin_service

router = APIRouter(prefix="/admin/papers", tags=["admin"])


@router.get("", response_model=list[PaperOut])
def list_papers(_: dict = Depends(require_role("admin"))) -> list[dict]:
    return admin_service.list_papers()


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def create_paper(
    body: PaperIn,
    _: dict = Depends(require_role("admin")),
) -> dict:
    try:
        return admin_service.upsert_paper(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: str,
    body: PaperIn,
    _: dict = Depends(require_role("admin")),
) -> dict:
    payload = body.model_dump()
    payload["id"] = paper_id
    return admin_service.upsert_paper(payload)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: str,
    _: dict = Depends(require_role("admin")),
) -> None:
    ok = admin_service.delete_paper(paper_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper not found or still referenced elsewhere",
        )
