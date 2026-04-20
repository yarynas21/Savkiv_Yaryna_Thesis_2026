"""
Knowledge Base Repository — reads data from PostgreSQL.

All three public functions return dicts in exactly the same format
that the old JSON files used, so agent code needs minimal changes.
"""

from __future__ import annotations

from sqlalchemy.exc import ProgrammingError

from db.connection import get_connection
from db.models import (
    adhesives,
    cost_rates,
    finishes,
    game_components,
    machine_constraints,
    machines,
    operations,
    papers,
    product_type_routes,
    stock_items,
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
            "papers":       [ {...}, ... ],
            "stock_items":  [ {...}, ... ],
            "finishes":     [ {...}, ... ],
            "adhesives":    [ {...}, ... ]
        }
    """
    with get_connection() as conn:
        paper_list = [dict(r) for r in conn.execute(papers.select()).mappings().all()]
        try:
            stock_list = [
                dict(r)
                for r in conn.execute(
                    stock_items.select().order_by(stock_items.c.stock_no)
                ).mappings().all()
            ]
        except ProgrammingError as e:
            msg = str(getattr(e, "orig", e))
            if "stock_items" in msg and "does not exist" in msg:
                logger.warning(
                    "Таблиця stock_items відсутня — повертаю порожній список. "
                    "Схоже, БД не ініціалізована: перезапустіть з чистим volume, "
                    "щоб Docker initdb виконав schema.sql + seeds/*.sql"
                )
                stock_list = []
            else:
                raise
        finish_list = [dict(r) for r in conn.execute(finishes.select()).mappings().all()]
        adhesive_list = [dict(r) for r in conn.execute(adhesives.select()).mappings().all()]

    logger.debug(
        f"Loaded {len(paper_list)} papers, {len(stock_list)} stock_items, "
        f"{len(finish_list)} finishes, {len(adhesive_list)} adhesives from DB"
    )
    return {
        "papers": paper_list,
        "stock_items": stock_list,
        "finishes": finish_list,
        "adhesives": adhesive_list,
    }


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


def get_game_components() -> list[dict]:
    """Return the catalog of purchasable board-game components from DB.

    Each row: {id, name, category, unit, price_uah, notes}. Returns an empty
    list if the table does not exist yet (happens when Docker initdb did not
    run — e.g. stale volume from before the schema was introduced).
    """
    with get_connection() as conn:
        try:
            rows = conn.execute(
                game_components.select().order_by(
                    game_components.c.category,
                    game_components.c.price_uah,
                )
            ).mappings().all()
        except ProgrammingError as e:
            msg = str(getattr(e, "orig", e))
            if "game_components" in msg and "does not exist" in msg:
                logger.warning(
                    "game_components table missing — returning empty list. "
                    "Recreate DB volume so initdb applies schema.sql + seeds/*.sql"
                )
                return []
            raise

    result = [dict(r) for r in rows]
    logger.debug(f"Loaded {len(result)} game_components from DB")
    return result


def get_cost_rates_by_category() -> dict[str, dict[str, float]]:
    """Load cost calculator tariffs grouped by ``category`` (see ``cost_rates`` table).

    Returns nested ``{category: {rate_key: value}}``. Empty dict if the table
    is missing or on connection errors (caller should fall back to defaults).
    """
    with get_connection() as conn:
        try:
            rows = conn.execute(
                cost_rates.select().order_by(
                    cost_rates.c.category,
                    cost_rates.c.rate_key,
                )
            ).mappings().all()
        except ProgrammingError as e:
            msg = str(getattr(e, "orig", e))
            if "cost_rates" in msg and "does not exist" in msg:
                logger.warning(
                    "cost_rates table missing — returning empty dict. "
                    "Recreate DB volume so initdb applies schema.sql + seeds/*.sql"
                )
                return {}
            raise

    out: dict[str, dict[str, float]] = {}
    for row in rows:
        cat = str(row["category"])
        key = str(row["rate_key"])
        val = row["value_numeric"]
        try:
            out.setdefault(cat, {})[key] = float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            out.setdefault(cat, {})[key] = 0.0
    logger.debug("Loaded %d cost_rates rows into %d categories", len(rows), len(out))
    return out
