"""
HTTP routers, one per domain / role.

Each router is a thin translation layer between Pydantic schemas and the
``services`` layer — no DB access, no graph invocation, no business rules.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routers import (
    admin_llm,
    admin_components,
    admin_cost_rates,
    admin_papers,
    admin_users,
    interviews_client,
    interviews_expert,
    metrics,
    sessions,
)


def build_api_router() -> APIRouter:
    """Mount every sub-router onto a single ``/api`` router for main.py."""
    api = APIRouter()
    api.include_router(interviews_client.router)
    api.include_router(interviews_expert.router)
    api.include_router(sessions.router)
    api.include_router(metrics.router)
    api.include_router(admin_components.router)
    api.include_router(admin_llm.router)
    api.include_router(admin_cost_rates.router)
    api.include_router(admin_papers.router)
    api.include_router(admin_users.router)
    return api
