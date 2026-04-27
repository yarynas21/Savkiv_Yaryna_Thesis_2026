"""
Client-facing interview flow.

All routes require role=``client`` — clients can only create and advance
their OWN interviews; experts have their own routes under ``/api/inbox``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user_db, require_role
from api.schemas.interviews import (
    InterviewCreate,
    InterviewDetail,
    InterviewMessageResponse,
    InterviewSummary,
)
from api.schemas.sessions import MessageRequest
from db.repositories import interviews as interviews_repo
from services import interview_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/interviews", tags=["interviews-client"])


def _summary(record: dict) -> InterviewSummary:
    return InterviewSummary(
        id=str(record["id"]),
        thread_id=str(record["thread_id"]),
        client_user_id=str(record["client_user_id"]),
        title=record.get("title"),
        status=record["status"],
        expert_user_id=str(record["expert_user_id"]) if record.get("expert_user_id") else None,
        production_thread_id=(
            str(record["production_thread_id"])
            if record.get("production_thread_id") else None
        ),
        created_at=record["created_at"],
        completed_at=record.get("completed_at"),
        processed_at=record.get("processed_at"),
        excel_ready=bool(record.get("excel_bytes")),
    )


def _detail(record: dict) -> InterviewDetail:
    base = _summary(record).model_dump()
    base.update(
        messages=record.get("messages") or [],
        collected_data=record.get("collected_data"),
        work_order=record.get("work_order"),
        cost_estimates=record.get("cost_estimates"),
    )
    return InterviewDetail(**base)


@router.post("", response_model=InterviewSummary, status_code=status.HTTP_201_CREATED)
def create_interview(
    body: InterviewCreate,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("client")),
) -> InterviewSummary:
    record = interview_service.create_interview(str(current_user["id"]), title=body.title)
    return _summary(record)


@router.get("/me", response_model=list[InterviewSummary])
def list_my_interviews(
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("client")),
) -> list[InterviewSummary]:
    rows = interview_service.list_my_interviews(str(current_user["id"]))
    return [_summary(r) for r in rows]


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("client")),
) -> InterviewDetail:
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    if str(record["client_user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Not your interview")
    return _detail(record)


@router.post("/{interview_id}/messages", response_model=InterviewMessageResponse)
def send_interview_message(
    interview_id: str,
    body: MessageRequest,
    current_user: dict = Depends(get_current_user_db),
    _: dict = Depends(require_role("client")),
) -> InterviewMessageResponse:
    record = interviews_repo.get_interview(interview_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    if str(record["client_user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Not your interview")
    if record["status"] != "in_progress":
        raise HTTPException(
            status_code=409,
            detail=f"Interview is {record['status']} — cannot send more messages",
        )
    try:
        payload = interview_service.send_message(interview_id, body.message)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("[%s] interview send_message failed: %s", interview_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return InterviewMessageResponse(
        interview_id=payload["interview_id"],
        thread_id=payload["thread_id"],
        status=payload["status"],
        messages=payload["messages"],
        product_components=payload.get("product_components", []),
        production_routes=payload.get("production_routes", []),
        ambiguities=payload.get("ambiguities", []),
        finished=payload.get("status") == "completed",
        current_agent=payload.get("current_agent", ""),
    )
