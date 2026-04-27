"""
LLM-eval metrics endpoints. Locked to admin + expert.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_role
from api.schemas.sessions import MetricsOverview, SessionMetrics
from services import metrics_service

router = APIRouter(tags=["metrics"])


@router.get("/metrics/overview", response_model=MetricsOverview)
def metrics_overview(
    _: dict = Depends(require_role("admin", "expert")),
) -> MetricsOverview:
    return MetricsOverview(**metrics_service.overview())


@router.get("/sessions/{thread_id}/metrics", response_model=SessionMetrics)
def session_metrics(
    thread_id: str,
    _: dict = Depends(require_role("admin", "expert")),
) -> SessionMetrics:
    try:
        return SessionMetrics(**metrics_service.session_metrics(thread_id, graph="full"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
