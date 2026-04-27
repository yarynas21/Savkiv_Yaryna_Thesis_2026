"""Interview-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class InterviewSummary(BaseModel):
    """Row shown in a client's history or an expert's inbox (no message blob)."""

    id: str
    thread_id: str
    client_user_id: str
    title: Optional[str] = None
    status: str
    expert_user_id: Optional[str] = None
    production_thread_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    excel_ready: bool = False


class InterviewDetail(InterviewSummary):
    """Full row including messages + collected requirements (used in detail views)."""

    messages: list[dict] = []
    collected_data: Optional[dict] = None
    work_order: Optional[dict] = None
    cost_estimates: Optional[dict] = None


class InterviewMessageResponse(BaseModel):
    """Response after posting a message to an in-progress interview."""

    interview_id: str
    thread_id: str
    status: str
    messages: list[dict]
    product_components: list[dict] = []
    production_routes: list[dict] = []
    ambiguities: list[str] = []
    finished: bool = False
    current_agent: str = ""


class InterviewLaunchResponse(BaseModel):
    interview_id: str
    production_thread_id: str
    messages: list[dict]
    product_components: list[dict] = []
    production_routes: list[dict] = []
    work_order: Optional[dict] = None
    cost_estimates: Optional[dict] = None
    awaiting_human: bool = False
    ambiguities: list[str] = []
    finished: bool = False
    current_agent: str = ""
    excel_ready: bool = False
