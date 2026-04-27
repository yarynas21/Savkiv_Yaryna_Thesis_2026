"""
Expert-facing inbox of completed client interviews.

Mounted under ``/api/inbox`` to avoid clashing with ``/api/interviews`` which
is reserved for the client role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from api.deps import get_current_user_db, require_role
from api.routers.interviews_client import _detail, _summary
from api.schemas.interviews import (
    InterviewDetail,
    InterviewLaunchResponse,
    InterviewSummary,
)
from db.repositories import interviews as interviews_repo
from services import production_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/inbox", tags=["interviews-expert"])


@router.get("", response_model=list[InterviewSummary])
def list_inbox(
    _: dict = Depends(require_role("expert", "admin")),
) -> list[InterviewSummary]:
    """All completed / processed client interviews (newest first)."""
    rows = interviews_repo.list_inbox()
    return [_summary(r) for r in rows]


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview_detail(
    interview_id: str,
    _: dict = Depends(require_role("expert", "admin")),
) -> InterviewDetail:
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return _detail(record)


@router.post("/{interview_id}/launch", response_model=InterviewLaunchResponse)
def launch_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("expert", "admin")),
) -> InterviewLaunchResponse:
    """Seed a production_graph thread from the saved interview and run it."""
    try:
        payload = production_service.launch_from_interview(
            interview_id, expert_user_id=str(current_user["id"])
        )
    except LookupError as exc:
        if str(exc) == "Interview not found":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        logger.error("[%s] unexpected LookupError on launch: %s", interview_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("[%s] launch_from_interview failed: %s", interview_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return InterviewLaunchResponse(
        interview_id=payload["interview_id"],
        production_thread_id=payload["thread_id"],
        messages=payload.get("messages", []),
        product_components=payload.get("product_components", []),
        production_routes=payload.get("production_routes", []),
        work_order=payload.get("work_order"),
        cost_estimates=payload.get("cost_estimates"),
        awaiting_human=payload.get("awaiting_human", False),
        ambiguities=payload.get("ambiguities", []),
        finished=payload.get("finished", False),
        current_agent=payload.get("current_agent", ""),
        excel_ready=payload.get("excel_ready", False),
    )


@router.get("/{interview_id}/excel")
def download_interview_excel(
    interview_id: str,
    _: dict = Depends(require_role("expert", "admin")),
) -> Response:
    """Download the Excel work-order that a launched production saved back."""
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    excel_bytes: bytes | None = record.get("excel_bytes")
    if not excel_bytes:
        # snapshot may not be flushed yet; try live thread
        production_thread_id = record.get("production_thread_id")
        if production_thread_id:
            try:
                excel_bytes, order_no = production_service.get_excel_bytes(
                    str(production_thread_id), graph="production"
                )
            except LookupError:
                excel_bytes = None
    if not excel_bytes:
        raise HTTPException(status_code=404, detail="Excel not ready yet")

    work_order = record.get("work_order") or {}
    order_no = work_order.get("order_number", f"interview_{interview_id}")
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{order_no}.xlsx"'},
    )
