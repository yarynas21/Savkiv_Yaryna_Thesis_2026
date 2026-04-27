"""
Admin-facing CRUD helpers for knowledge-base tables.

Scope (per the plan's "prices_plus" option):
* ``game_components``
* ``cost_rates``
* ``papers``

Machines / finishes / adhesives / operations / routes are deliberately left
out of scope — agents still read them via ``repositories.kb`` but there is no
admin UI surface for them yet.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from db.connection import get_connection
from db.models import cost_rates, game_components, llm_runtime_settings, papers
from utils.logger import get_logger

logger = get_logger(__name__)


# game_components

def list_game_components() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            game_components.select().order_by(
                game_components.c.category, game_components.c.id
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def upsert_game_component(data: dict[str, Any]) -> dict:
    """Insert or update a game component by ``id``."""
    with get_connection() as conn:
        existing = conn.execute(
            select(game_components.c.id).where(game_components.c.id == data["id"])
        ).fetchone()
        if existing:
            row = conn.execute(
                update(game_components)
                .where(game_components.c.id == data["id"])
                .values(**data)
                .returning(*game_components.c)
            ).mappings().one()
        else:
            row = conn.execute(
                insert(game_components).values(**data).returning(*game_components.c)
            ).mappings().one()
    return dict(row)


def delete_game_component(component_id: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            delete(game_components).where(game_components.c.id == component_id)
        )
    return result.rowcount > 0


# cost_rates (composite key: category + rate_key)

def list_cost_rates() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            cost_rates.select().order_by(
                cost_rates.c.category, cost_rates.c.rate_key
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def upsert_cost_rate(data: dict[str, Any]) -> dict:
    with get_connection() as conn:
        existing = conn.execute(
            select(cost_rates.c.category).where(
                and_(
                    cost_rates.c.category == data["category"],
                    cost_rates.c.rate_key == data["rate_key"],
                )
            )
        ).fetchone()
        if existing:
            row = conn.execute(
                update(cost_rates)
                .where(
                    and_(
                        cost_rates.c.category == data["category"],
                        cost_rates.c.rate_key == data["rate_key"],
                    )
                )
                .values(**data)
                .returning(*cost_rates.c)
            ).mappings().one()
        else:
            row = conn.execute(
                insert(cost_rates).values(**data).returning(*cost_rates.c)
            ).mappings().one()
    return dict(row)


def delete_cost_rate(category: str, rate_key: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            delete(cost_rates).where(
                and_(
                    cost_rates.c.category == category,
                    cost_rates.c.rate_key == rate_key,
                )
            )
        )
    return result.rowcount > 0


# papers

def list_papers() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            papers.select().order_by(papers.c.type, papers.c.id)
        ).mappings().all()
    return [dict(r) for r in rows]


def upsert_paper(data: dict[str, Any]) -> dict:
    with get_connection() as conn:
        existing = conn.execute(
            select(papers.c.id).where(papers.c.id == data["id"])
        ).fetchone()
        if existing:
            row = conn.execute(
                update(papers)
                .where(papers.c.id == data["id"])
                .values(**data)
                .returning(*papers.c)
            ).mappings().one()
        else:
            row = conn.execute(
                insert(papers).values(**data).returning(*papers.c)
            ).mappings().one()
    return dict(row)


def delete_paper(paper_id: str) -> bool:
    with get_connection() as conn:
        try:
            result = conn.execute(delete(papers).where(papers.c.id == paper_id))
        except IntegrityError as exc:
            logger.warning("Cannot delete paper %s — referenced: %s", paper_id, exc)
            return False
    return result.rowcount > 0


# llm_runtime_settings

def get_llm_runtime_setting(setting_key: str = "global") -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            select(llm_runtime_settings).where(
                llm_runtime_settings.c.setting_key == setting_key
            )
        ).mappings().first()
    return dict(row) if row else None


def upsert_llm_runtime_setting(data: dict[str, Any]) -> dict[str, Any]:
    payload = {**data, "updated_at": text("NOW()")}
    with get_connection() as conn:
        existing = conn.execute(
            select(llm_runtime_settings.c.setting_key).where(
                llm_runtime_settings.c.setting_key == payload["setting_key"]
            )
        ).fetchone()
        if existing:
            row = conn.execute(
                update(llm_runtime_settings)
                .where(llm_runtime_settings.c.setting_key == payload["setting_key"])
                .values(**payload)
                .returning(*llm_runtime_settings.c)
            ).mappings().one()
        else:
            row = conn.execute(
                insert(llm_runtime_settings)
                .values(**payload)
                .returning(*llm_runtime_settings.c)
            ).mappings().one()
    return dict(row)
