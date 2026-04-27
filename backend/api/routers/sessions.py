"""
Expert full_graph sessions.

Experts can run the full pipeline themselves (e.g. while collecting the
client's requirements over the phone). All routes require role=``expert``
or ``admin``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from api.deps import require_role
from api.schemas.sessions import (
    MessageRequest,
    ReviewRequest,
    SessionCreated,
    SessionState,
)
from services import metrics_service, production_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreated, status_code=201)
def create_session(
    _: dict = Depends(require_role("expert", "admin")),
) -> SessionCreated:
    payload = production_service.create_full_session()
    metrics_service.register_thread(payload["thread_id"], graph="full")
    return SessionCreated(thread_id=payload["thread_id"])


@router.post("/{thread_id}/messages", response_model=SessionState)
def send_message(
    thread_id: str,
    body: MessageRequest,
    _: dict = Depends(require_role("expert", "admin")),
) -> SessionState:
    try:
        payload = production_service.send_message(thread_id, body.message, graph="full")
    except Exception as exc:
        logger.error("[%s] full_graph send_message failed: %s", thread_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    metrics_service.register_thread(thread_id, graph="full")
    return SessionState(**payload)


@router.post("/{thread_id}/review", response_model=SessionState)
def submit_review(
    thread_id: str,
    body: ReviewRequest,
    _: dict = Depends(require_role("expert", "admin")),
) -> SessionState:
    try:
        payload = production_service.submit_review(thread_id, body.feedback, graph="full")
    except Exception as exc:
        logger.error("[%s] full_graph submit_review failed: %s", thread_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    return SessionState(**payload)


@router.get("/{thread_id}/excel")
def download_excel(
    thread_id: str,
    _: dict = Depends(require_role("expert", "admin")),
) -> Response:
    try:
        excel_bytes, order_no = production_service.get_excel_bytes(thread_id, graph="full")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{order_no}.xlsx"'},
    )
