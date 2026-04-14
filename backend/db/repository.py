"""
Knowledge Base Repository — reads data from PostgreSQL.

All three public functions return dicts in exactly the same format
that the old JSON files used, so agent code needs minimal changes.
"""

from __future__ import annotations

from db.connection import get_connection
from db.models import (
    adhesives,
    finishes,
    machine_constraints,
    machines,
    operations,
    papers,
    product_type_routes,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def get_kb_machines() -> dict:
    """
    Returns:
        {
            "machines":    [ {...}, ... ],
            "constraints": { "key": value, ... }
        }
    """
    with get_connection() as conn:
        rows = conn.execute(machines.select()).mappings().all()
        machine_list = [dict(r) for r in rows]

        constraint_rows = conn.execute(machine_constraints.select()).mappings().all()
        # Coerce stored string values back to their original Python types
        constraints: dict = {}
        for r in constraint_rows:
            raw = r["value"]
            # Try int → float → bool → str
            if raw.lower() == "true":
                constraints[r["key"]] = True
            elif raw.lower() == "false":
                constraints[r["key"]] = False
            else:
                try:
                    constraints[r["key"]] = int(raw)
                except ValueError:
                    try:
                        constraints[r["key"]] = float(raw)
                    except ValueError:
                        constraints[r["key"]] = raw

    logger.debug(f"Loaded {len(machine_list)} machines from DB")
    return {"machines": machine_list, "constraints": constraints}


def get_kb_materials() -> dict:
    """
    Returns:
        {
            "papers":    [ {...}, ... ],
            "finishes":  [ {...}, ... ],
            "adhesives": [ {...}, ... ]
        }
    """
    with get_connection() as conn:
        paper_list = [dict(r) for r in conn.execute(papers.select()).mappings().all()]
        finish_list = [dict(r) for r in conn.execute(finishes.select()).mappings().all()]
        adhesive_list = [dict(r) for r in conn.execute(adhesives.select()).mappings().all()]

    logger.debug(
        f"Loaded {len(paper_list)} papers, {len(finish_list)} finishes, "
        f"{len(adhesive_list)} adhesives from DB"
    )
    return {"papers": paper_list, "finishes": finish_list, "adhesives": adhesive_list}


def get_kb_operations() -> dict:
    """
    Returns:
        {
            "operations":          [ {...}, ... ],
            "product_type_routes": { "rigid_box": ["op1", "op2", ...], ... }
        }
    """
    with get_connection() as conn:
        op_list = [dict(r) for r in conn.execute(operations.select()).mappings().all()]

        route_rows = conn.execute(
            product_type_routes.select().order_by(
                product_type_routes.c.product_type,
                product_type_routes.c.sort_order,
            )
        ).mappings().all()

    # Reconstruct the { product_type: [operation_id, ...] } dict
    routes: dict[str, list[str]] = {}
    for r in route_rows:
        routes.setdefault(r["product_type"], []).append(r["operation_id"])

    logger.debug(f"Loaded {len(op_list)} operations, {len(routes)} product routes from DB")
    return {"operations": op_list, "product_type_routes": routes}
