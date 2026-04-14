"""
Pydantic schemas for the Dyz-Art MAS API.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class MessageRequest(BaseModel):
    message: str


class ReviewRequest(BaseModel):
    feedback: str


class SessionCreated(BaseModel):
    thread_id: str


class SessionState(BaseModel):
    thread_id: str
    messages: list[dict]
    product_components: list[dict]
    production_routes: list[dict]
    work_order: Optional[dict]
    cost_estimates: Optional[dict]
    awaiting_human: bool
    ambiguities: list[str]
    finished: bool
    current_agent: str
    excel_ready: bool
