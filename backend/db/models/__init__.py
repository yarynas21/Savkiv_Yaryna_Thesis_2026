"""
SQLAlchemy Core table definitions (metadata only — no ORM classes).

Tables are split into domain modules so that each area of the system imports
only what it needs:

* ``kb``         — knowledge base (machines, papers, finishes, …)
* ``users``      — authentication / access control
* ``interviews`` — persisted client interview sessions

All tables share a single ``MetaData`` instance re-exported from this package
so that Alembic introspection and ``repository.*`` helpers keep working with
unchanged imports (``from db.models import machines`` still resolves).
"""

from __future__ import annotations

from sqlalchemy import MetaData

metadata = MetaData()

# Expose ``metadata`` to the per-domain modules before they define tables.
# Each module calls ``from db.models import metadata`` to attach its tables.

from db.models.kb import (  # noqa: E402  (import after metadata is defined)
    adhesives,
    cost_rates,
    finishes,
    game_components,
    llm_runtime_settings,
    machine_constraints,
    machines,
    operations,
    papers,
    product_type_routes,
    stock_items,
)
from db.models.users import users  # noqa: E402
from db.models.interviews import interview_sessions  # noqa: E402
from db.models.metrics import session_metrics, session_metrics_by_model  # noqa: E402

__all__ = [
    "metadata",
    # kb
    "machines",
    "machine_constraints",
    "papers",
    "stock_items",
    "finishes",
    "adhesives",
    "operations",
    "product_type_routes",
    "game_components",
    "cost_rates",
    "llm_runtime_settings",
    # users
    "users",
    # interviews
    "interview_sessions",
    # metrics
    "session_metrics",
    "session_metrics_by_model",
]
