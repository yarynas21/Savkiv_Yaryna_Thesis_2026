"""
Admin CRUD for ``users`` (role & activity management).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user_db, require_role
from api.schemas.admin import UserAdminIn, UserAdminOut, UserAdminPatch
from services import admin_service

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _to_out(row: dict) -> UserAdminOut:
    return UserAdminOut(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        role=row["role"],
        is_active=row["is_active"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=list[UserAdminOut])
def list_users(_: dict = Depends(require_role("admin"))) -> list[UserAdminOut]:
    return [_to_out(r) for r in admin_service.list_users()]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserAdminIn,
    _: dict = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        return _to_out(admin_service.create_user(body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: str,
    body: UserAdminPatch,
    _: dict = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        return _to_out(admin_service.update_user(user_id, body.model_dump(exclude_none=True)))
    except LookupError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("admin")),
) -> None:
    try:
        ok = admin_service.delete_user(user_id, acting_user_id=str(current_user["id"]))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
