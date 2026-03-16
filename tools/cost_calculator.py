"""
Cost Calculator
===============
Estimates production costs for different quantity tiers based on the
synthesised production routes.

Pricing model:
- Each operation has a base cost per 1000 units
- Quantity discounts are applied at tiers: 500, 1000, 2500, 5000
- Special operations (foil, embossing) have setup (cliché/die) costs
"""

from __future__ import annotations

from typing import Any
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Operation base costs (UAH per 1000 units)
# ---------------------------------------------------------------------------
_OP_COST_PER_1K: dict[str, float] = {
    "prepress":           800.0,
    "offset_printing":    1_200.0,
    "digital_printing":   2_500.0,
    "lamination":         600.0,
    "uv_varnishing":      500.0,
    "hot_foil_stamping":  1_800.0,
    "embossing":          1_500.0,
    "die_cutting":        700.0,
    "creasing":           300.0,
    "chipboard_laminating": 900.0,
    "box_assembly":       1_100.0,
    "card_cutting":       400.0,
    "saddle_stitching":   350.0,
    "perfect_binding":    600.0,
    "quality_control":    200.0,
    "packaging":          250.0,
}

# One-time setup costs (clichés, dies) — UAH
_SETUP_COSTS: dict[str, float] = {
    "hot_foil_stamping": 3_500.0,   # foil cliché
    "embossing":         2_800.0,   # embossing die
    "die_cutting":       1_200.0,   # cutting die
}

# Quantity discount tiers: (min_qty, discount_fraction)
_DISCOUNT_TIERS: list[tuple[int, float]] = [
    (5_000, 0.25),
    (2_500, 0.15),
    (1_000, 0.08),
    (500,   0.03),
    (0,     0.00),
]

_QUANTITY_TIERS = [500, 1_000, 2_500, 5_000]


def _get_discount(qty: int) -> float:
    for min_qty, discount in _DISCOUNT_TIERS:
        if qty >= min_qty:
            return discount
    return 0.0


def _route_variable_cost_per_1k(routes: list[dict]) -> float:
    """Sum up variable costs across all routes for 1000 units."""
    total = 0.0
    for route in routes:
        for op in route.get("operations", []):
            op_id = op.get("operation_id", "")
            total += _OP_COST_PER_1K.get(op_id, 0.0)
    return total


def _route_setup_costs(routes: list[dict]) -> float:
    """One-time setup costs (cliché, die) — paid once regardless of quantity."""
    seen: set[str] = set()
    total = 0.0
    for route in routes:
        for op in route.get("operations", []):
            op_id = op.get("operation_id", "")
            if op_id in _SETUP_COSTS and op_id not in seen:
                total += _SETUP_COSTS[op_id]
                seen.add(op_id)
    return total


def calculate_costs(routes: list[dict], base_quantity: int) -> dict[str, Any]:
    """
    Calculate cost estimates for multiple quantity tiers.

    Parameters
    ----------
    routes        : validated production routes
    base_quantity : the quantity requested by the client

    Returns
    -------
    dict with keys:
        base_quantity  – requested qty
        variable_cost_per_1k – UAH per 1000 units (no discount, no setup)
        setup_costs    – one-time tooling costs
        tiers          – {qty_label: total_cost_UAH}
        currency       – "UAH"
    """
    logger.info(f"Calculating costs for {len(routes)} routes, base quantity: {base_quantity}")
    var_per_1k = _route_variable_cost_per_1k(routes)
    setup = _route_setup_costs(routes)
    logger.debug(f"Variable cost per 1k: {var_per_1k:.2f} UAH, Setup costs: {setup:.2f} UAH")

    # Always include base quantity + standard tiers
    quantities = sorted(set([base_quantity] + _QUANTITY_TIERS))

    tiers: dict[str, float] = {}
    for qty in quantities:
        discount = _get_discount(qty)
        variable_total = var_per_1k * (qty / 1_000) * (1 - discount)
        total = variable_total + setup
        label = f"{qty:,} шт."
        tiers[label] = round(total, 2)
        logger.debug(f"Tier {label}: {total:.2f} UAH")

    logger.info(f"Cost calculation complete: {len(tiers)} tiers")
    return {
        "base_quantity": base_quantity,
        "variable_cost_per_1k": round(var_per_1k, 2),
        "setup_costs": round(setup, 2),
        "tiers": tiers,
        "currency": "UAH",
        "note": (
            "Орієнтовна вартість без ПДВ. "
            "Включає: матеріали, друк, оздоблення, складання, пакування. "
            "Разові витрати (кліше, штампи) розподілені на перший тираж."
        ),
    }
