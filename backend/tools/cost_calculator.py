"""
Cost Calculator
===============
Розрахунок собівартості за методологією реального виробництва:

  Папір       : (арк.тираж + приладка) × площа_аркуша м² × г/м² кг × ціна/кг
  Друк        : к-сть фарб × ставка_за_прогін  [+ Pantone кг × ціна/кг]
  Ламінація   : аркуші × площа м² × ставка/м²
  Флатування  : вага_паперу кг × ставка/кг
  Висічка     : приладка + аркуші × ставка/аркуш
  Рицовка     : приладка + аркуші × ставка/аркуш
  Праця (решта): к-сть / продуктивність шт/год × ставка_год

Ставки — наближені, не відображають реальних конфіденційних тарифів.
Тарифи в PostgreSQL (``cost_rates``); якщо БД недоступна — підставляються значення з
``backend/db/seeds/10_cost_rates.sql`` (той самий файл, який initdb сидить у БД).
"""

from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

# Дефолти з db/seeds/10_cost_rates.sql (без дублювання чисел у Python)

_COST_RATES_SEED_SQL = (
    Path(__file__).resolve().parent.parent / "db" / "seeds" / "10_cost_rates.sql"
)
# Рядки сиду: ('category', 'rate_key', <number>, …
_COST_RATE_TUPLE_RE = re.compile(
    r"\(\s*'(?P<cat>[a-z0-9_]+)'\s*,\s*'(?P<key>[^']+)'\s*,\s*(?P<val>\d+(?:\.\d+)?)\b",
    re.MULTILINE,
)

_seed_rates_cache: dict[str, Any] | None = None


def _minimal_rates_fallback() -> dict[str, Any]:
    """Якщо seeds/10_cost_rates.sql відсутній або не парситься — щоб не падати."""
    return {
        "global": {"default_margin": 1.10, "hourly_rate_uah": 300.0},
        "paper_kg": {"_default": 75.0},
        "lam_m2": {"_default": 12.0},
        "makeready": {"_default": 200},
        "productivity": {"_default": 500.0},
        "papers_gsm": {"grey_chipboard_1500": 1500, "grey_chipboard_2000": 2000, "_default": 1500},
    }


def _default_rates_from_seed_sql() -> dict[str, Any]:
    """Побудувати вкладений dict з INSERT-рядків ``seeds/10_cost_rates.sql``."""
    if not _COST_RATES_SEED_SQL.is_file():
        logger.warning(
            "cost_rates seed SQL not found at %s — using minimal fallback",
            _COST_RATES_SEED_SQL,
        )
        return _minimal_rates_fallback()

    text = _COST_RATES_SEED_SQL.read_text(encoding="utf-8")
    out: dict[str, dict[str, float]] = {}
    for m in _COST_RATE_TUPLE_RE.finditer(text):
        cat, key, val_s = m.group("cat"), m.group("key"), m.group("val")
        try:
            val = float(val_s) if "." in val_s else float(int(val_s))
        except ValueError:
            continue
        out.setdefault(cat, {})[key] = val

    if not out.get("global"):
        logger.warning("Parsed no global rates from %s — fallback", _COST_RATES_SEED_SQL)
        return _minimal_rates_fallback()
    return out


def _default_rates_template() -> dict[str, Any]:
    """Один раз парсимо сид; далі deepcopy у ``_load_merged_rates``."""
    global _seed_rates_cache
    if _seed_rates_cache is None:
        _seed_rates_cache = _default_rates_from_seed_sql()
    return _seed_rates_cache


def _load_papers_gsm_map() -> dict[str, int]:
    """Завантажити {paper_id: weight_gsm} з таблиці papers; fallback — порожній dict."""
    try:
        from db.repository import get_kb_materials

        materials = get_kb_materials()
        return {
            str(row["id"]): int(row["weight_gsm"])
            for row in materials.get("papers", [])
            if row.get("id") and row.get("weight_gsm") is not None
        }
    except Exception as exc:
        logger.warning("papers gsm map: DB load failed (%s)", exc)
        return {}


def _load_merged_rates() -> dict[str, Any]:
    """Deep-copy defaults (з 006 SQL) і накладання рядків з ``cost_rates`` у БД."""
    merged = copy.deepcopy(_default_rates_template())
    try:
        from db.repository import get_cost_rates_by_category

        db_rates = get_cost_rates_by_category()
    except Exception as exc:
        logger.warning("cost_rates: DB load failed, using Python defaults only (%s)", exc)
        db_rates = {}
    for cat in merged:
        if cat not in db_rates:
            continue
        patch = db_rates[cat]
        if isinstance(patch, dict) and isinstance(merged[cat], dict):
            merged[cat].update({k: float(v) for k, v in patch.items()})

    # Додаємо gsm з таблиці papers (перекриває fallback-значення)
    db_gsm = _load_papers_gsm_map()
    if db_gsm:
        merged.setdefault("papers_gsm", {}).update(db_gsm)

    return merged


def _global_rate(rates: dict[str, Any], key: str) -> float:
    return float(rates["global"][key])


def _paper_price(paper_id: str | None, rates: dict[str, Any]) -> float:
    d = rates["paper_kg"]
    return float(d.get(paper_id or "", d.get("_default", 75.0)))


def _paper_gsm(paper_id: str | None, rates: dict[str, Any]) -> int:
    d = rates.get("papers_gsm", {})
    return int(d.get(paper_id or "", d.get("_default", 1500)))


def _lam_rate(lam_type: str | None, rates: dict[str, Any]) -> float:
    d = rates["lam_m2"]
    return float(d.get(lam_type or "", d.get("_default", 12.0)))


def _makeready(op_id: str, rates: dict[str, Any]) -> int:
    m = rates["makeready"]
    v = m.get(op_id, m.get("_default", 200))
    return int(round(float(v)))


def _productivity(op_id: str, rates: dict[str, Any]) -> float:
    p = rates["productivity"]
    return float(p.get(op_id, p.get("_default", 500.0)))


# Допоміжні функції

def _parse_print_colors(print_colors: str | None) -> tuple[int, int]:
    """'4+0' → (4, 0); '5+0' → (5, 0); None → (4, 0)."""
    if not print_colors:
        return 4, 0
    parts = str(print_colors).split("+")
    try:
        front = int(parts[0])
        back  = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        front, back = 4, 0
    return front, back


def _sheet_area_m2(size_mm: list[int | float]) -> float:
    """Площа аркуша з 15 мм запасом на кожну сторону."""
    w = (size_mm[0] + 30) / 1000
    h = (size_mm[1] + 30) / 1000
    return round(w * h, 6)


# Закупні комплектуючі (catalog + notes parsing)


def _parse_qty_from_text(text: str) -> int | None:
    """Extract first integer quantity from free-form note fragment."""
    m = re.search(r"\b(\d{1,7})\b", text)
    if not m:
        return None
    try:
        qty = int(m.group(1))
        return qty if qty > 0 else None
    except ValueError:
        return None


def _load_game_components_catalog() -> list[dict[str, Any]]:
    """Load game components from DB; return [] if unavailable."""
    try:
        from db.repository import get_game_components

        rows = get_game_components()
    except Exception as exc:
        logger.warning("Could not load game_components catalog: %s", exc)
        return []

    return rows if isinstance(rows, list) else []


def _calc_game_components_from_requirements(
    client_requirements: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Calculate extra cost for purchased game components from requirements.

    Supports two input styles:
    1) Structured list: client_requirements["game_components_selected"] = [
           {"id": "dice_d6", "qty": 100}, ...
       ]
    2) Free-text notes in client_requirements["game_components_notes"].
    """
    req = client_requirements or {}
    if not req.get("has_game_components"):
        return None

    notes = str(req.get("game_components_notes") or "").strip()

    if req.get("customer_provides_components"):
        logger.info("Game components are customer-provided, skipping purchase cost.")
        return {
            "component_id": "game_components_purchase",
            "component_name": "Закупні комплектуючі",
            "line_items": [
                {
                    "item": "Комплектуючі надає замовник",
                    "qty": "—",
                    "rate": "0 грн",
                    "total": 0.0,
                }
            ],
            "subtotal": 0.0,
        }

    catalog_rows = _load_game_components_catalog()
    if not catalog_rows:
        return None

    by_id = {str(row.get("id", "")).strip().lower(): row for row in catalog_rows}
    selected: dict[str, int] = {}

    # Structured format has highest priority when present.
    for item in req.get("game_components_selected", []) or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip().lower()
        if not item_id or item_id not in by_id:
            continue
        qty_raw = item.get("qty", item.get("quantity", 1))
        try:
            qty = max(1, int(qty_raw))
        except Exception:
            qty = 1
        selected[item_id] = selected.get(item_id, 0) + qty

    # Fallback: parse text notes if no structured selections.
    if not selected and notes:
        chunks = [chunk.strip() for chunk in re.split(r"[,\n;]+", notes) if chunk.strip()]
        for chunk in chunks:
            chunk_l = chunk.lower()
            qty = _parse_qty_from_text(chunk_l) or 1
            for row in catalog_rows:
                item_id = str(row.get("id", "")).strip().lower()
                name_l = str(row.get("name", "")).strip().lower()
                if not item_id:
                    continue
                if item_id in chunk_l or (name_l and name_l in chunk_l):
                    selected[item_id] = selected.get(item_id, 0) + qty
                    break

    if not selected:
        return None

    line_items: list[dict[str, Any]] = []
    for item_id, qty in selected.items():
        row = by_id.get(item_id)
        if not row:
            continue
        try:
            unit_price = float(row.get("price_uah", 0) or 0)
        except Exception:
            unit_price = 0.0
        total = round(unit_price * qty, 2)
        line_items.append(
            {
                "item": f"{row.get('name', item_id)}",
                "qty": f"{qty} {row.get('unit', 'шт')}",
                "rate": f"{unit_price:.2f} грн/{row.get('unit', 'шт')}",
                "total": total,
            }
        )

    if not line_items:
        return None

    subtotal = round(sum(item["total"] for item in line_items), 2)
    return {
        "component_id": "game_components_purchase",
        "component_name": "Закупні комплектуючі",
        "line_items": line_items,
        "subtotal": subtotal,
    }


# Розрахунок для одного компонента

def _calc_component(
    route: dict,
    component: dict | None,
    quantity: int,
    rates: dict[str, Any],
) -> dict[str, Any]:
    """
    Повертає рядкову калькуляцію (line_items) для одного компонента.
    """
    comp    = component or {}
    ops     = route.get("operations", [])
    op_ids  = {op.get("operation_id", "") for op in ops}
    mat     = route.get("material", {})

    # --- Базові параметри ------------------------------------------------
    size_mm = comp.get("size_mm") or [200, 200]
    gsm     = comp.get("gsm") or 300
    paper_id = mat.get("cover") or mat.get("paper_id")

    pcs_per_sheet = comp.get("pcs_per_sheet", 1)
    # для кришка+дно на одному аркуші → 2
    if comp.get("construction") in ("lid_and_base",):
        pcs_per_sheet = 2

    sheets_run  = math.ceil(quantity / pcs_per_sheet)
    area_m2     = _sheet_area_m2(size_mm)
    price_kg    = _paper_price(paper_id, rates)
    gsm_kg      = gsm / 1000.0

    # Приладка: береться максимальна серед операцій що є
    priladka = max(
        (_makeready(op.get("operation_id", ""), rates) for op in ops),
        default=_makeready("_default", rates),
    )
    sheets_total = sheets_run + priladka

    line_items: list[dict] = []

    # --- 1. Папір --------------------------------------------------------
    weight_kg   = sheets_total * area_m2 * gsm_kg
    paper_cost  = round(weight_kg * price_kg, 2)
    line_items.append({
        "item":   f"Папір ({paper_id or 'матеріал'}, {gsm}г/м²)",
        "qty":    f"{weight_kg:.2f} кг",
        "rate":   f"{price_kg} грн/кг",
        "total":  paper_cost,
    })

    # --- 2. Флатування (якщо є в маршруті) --------------------------------
    if "flatting" in op_ids:
        flat_kg_rate = _global_rate(rates, "flatting_rate_per_kg")
        flat_cost = round(weight_kg * flat_kg_rate, 2)
        line_items.append({
            "item":  "Флатування",
            "qty":   f"{weight_kg:.2f} кг",
            "rate":  f"{flat_kg_rate} грн/кг",
            "total": flat_cost,
        })

    # --- 3. Друк ---------------------------------------------------------
    print_colors_str = comp.get("print_colors")
    # також перевіряємо параметри операції
    for op in ops:
        if op.get("operation_id") in ("offset_printing", "digital_printing"):
            print_colors_str = print_colors_str or op.get("parameters", {}).get("colors")
            break

    front_colors, back_colors = _parse_print_colors(print_colors_str)
    total_colors = front_colors + back_colors
    has_pantone  = front_colors >= 5 or back_colors >= 5

    if "offset_printing" in op_ids:
        # Кількість реальних CMYK прогонів (не рахуємо 5й/6й як Pantone тут — нижче)
        cmyk_colors = min(front_colors, 4) + min(back_colors, 4)
        offset_rate = _global_rate(rates, "offset_rate_per_color")
        print_cost  = round(cmyk_colors * offset_rate, 2)
        line_items.append({
            "item":  f"Офсетний друк {print_colors_str or '4+0'}",
            "qty":   f"{cmyk_colors} прогони",
            "rate":  f"{offset_rate:.0f} грн/прогін",
            "total": print_cost,
        })
        if has_pantone:
            pantone_qty  = (1 if front_colors >= 5 else 0) + (1 if back_colors >= 5 else 0)
            p_kg = _global_rate(rates, "pantone_kg_per_run")
            p_price = _global_rate(rates, "pantone_price_per_kg")
            pantone_cost = round(pantone_qty * p_kg * p_price, 2)
            line_items.append({
                "item":  f"Pantone фарба ({pantone_qty}×{p_kg}кг)",
                "qty":   f"{pantone_qty * p_kg} кг",
                "rate":  f"{p_price} грн/кг",
                "total": pantone_cost,
            })
    elif "digital_printing" in op_ids:
        digital_rate = _global_rate(rates, "digital_rate_per_1k_sheets")
        print_cost = round(digital_rate * sheets_run / 1000, 2)
        line_items.append({
            "item":  f"Цифровий друк {print_colors_str or '4+0'}",
            "qty":   f"{sheets_run} арк.",
            "rate":  f"{digital_rate} грн/1000арк.",
            "total": print_cost,
        })

    # --- 4. Ламінація ----------------------------------------------------
    lam_type = comp.get("lamination")
    if not lam_type:
        for op in ops:
            if op.get("operation_id") == "lamination":
                lam_type = op.get("parameters", {}).get("type", "matte")
                break
    if "lamination" in op_ids:
        lam_type    = lam_type or "matte"
        rate_m2     = _lam_rate(lam_type, rates)
        lam_area    = sheets_total * area_m2
        lam_cost    = round(lam_area * rate_m2, 2)
        line_items.append({
            "item":  f"Ламінація ({lam_type})",
            "qty":   f"{lam_area:.2f} м²",
            "rate":  f"{rate_m2} грн/м²",
            "total": lam_cost,
        })

    # --- 5. УФ-лакування -------------------------------------------------
    if "uv_varnishing" in op_ids:
        uv_area = sheets_total * area_m2
        uv_m2 = _global_rate(rates, "uv_rate_m2")
        uv_cost = round(uv_area * uv_m2, 2)
        line_items.append({
            "item":  "УФ-лакування",
            "qty":   f"{uv_area:.2f} м²",
            "rate":  f"{uv_m2} грн/м²",
            "total": uv_cost,
        })

    # --- 6. Каширування --------------------------------------------------
    if "chipboard_laminating" in op_ids:
        base_paper_id = mat.get("base")
        base_price    = _paper_price(base_paper_id, rates)
        base_gsm      = _paper_gsm(base_paper_id, rates)
        base_weight   = sheets_total * area_m2 * (base_gsm / 1000)
        base_cost     = round(base_weight * base_price, 2)
        line_items.append({
            "item":  f"Підкашировка ({base_paper_id or 'ПК'})",
            "qty":   f"{base_weight:.2f} кг",
            "rate":  f"{base_price} грн/кг",
            "total": base_cost,
        })
        kash_area = sheets_total * area_m2
        kash_m2 = _global_rate(rates, "kashire_rate_m2")
        kash_cost = round(kash_area * kash_m2, 2)
        line_items.append({
            "item":  "Каширування",
            "qty":   f"{kash_area:.2f} м²",
            "rate":  f"{kash_m2} грн/м²",
            "total": kash_cost,
        })

    # --- 7. Висічка ------------------------------------------------------
    if "die_cutting" in op_ids:
        v_setup = _global_rate(rates, "vysichka_setup_uah")
        v_sheet = _global_rate(rates, "vysichka_rate_per_sheet")
        vys_cost = round(v_setup + sheets_total * v_sheet, 2)
        line_items.append({
            "item":  "Висічка",
            "qty":   f"приладка + {sheets_total} арк.",
            "rate":  f"{v_setup:.0f}грн + {v_sheet}грн/арк.",
            "total": vys_cost,
        })

    # --- 8. Рицовка (creasing) -------------------------------------------
    if "creasing" in op_ids:
        for op in ops:
            if op.get("operation_id") == "creasing":
                crease_count = op.get("parameters", {}).get("crease_count", 1)
                break
        else:
            crease_count = 1
        cr_setup = _global_rate(rates, "creasing_setup_uah")
        cr_sheet = _global_rate(rates, "creasing_rate_per_sheet")
        cr_cost = round(
            (cr_setup + sheets_total * cr_sheet) * crease_count,
            2,
        )
        line_items.append({
            "item":  f"Рицовка ({crease_count} біговки)",
            "qty":   f"{sheets_total} арк.",
            "rate":  f"{cr_setup:.0f}грн + {cr_sheet}грн/арк.",
            "total": cr_cost,
        })

    # --- 9. Трудомісткі операції (qty / продуктивність × ставка/год) -----
    LABOUR_OPS = {
        "blank_stripping":    "Витруска",
        "corner_taping":      "Обклейка кутиків (машинна)",
        "box_assembly":       "Складання коробки",
        "quality_control":    "Контроль якості",
        "card_cutting":       "Порізка карт",
        "shrink_wrapping":    "Термозбіжка / термопакування",
        "game_kit_assembly":  "Комплектування набору гри",
        "shipper_packing":    "Пакування в ящики",
        "palletizing":        "Паллетування",
    }
    for op_id, label in LABOUR_OPS.items():
        if op_id in op_ids:
            prod      = _productivity(op_id, rates)
            hourly    = _global_rate(rates, "hourly_rate_uah")
            labour    = round(quantity / prod * hourly, 2)
            line_items.append({
                "item":  label,
                "qty":   f"{quantity} шт.",
                "rate":  f"{prod:.0f} шт/год × {hourly:.0f} грн/год",
                "total": labour,
            })

    component_total = round(sum(li["total"] for li in line_items), 2)
    return {
        "component_id":   route.get("component_id", ""),
        "component_name": route.get("component_name", "Компонент"),
        "line_items":     line_items,
        "subtotal":       component_total,
    }


# Публічна функція (зворотно сумісна з generation/node.py)

def calculate_costs(
    routes: list[dict],
    base_quantity: int,
    components: list[dict] | None = None,
    client_requirements: dict[str, Any] | None = None,
    margin: float | None = None,
) -> dict[str, Any]:
    """
    Розраховує собівартість замовлення за реальною методологією.

    Parameters
    ----------
    routes        : маршрути від TechnologistAgent
    base_quantity : тираж із вимог замовника
    components    : компоненти із ProductionState (опціонально)
    client_requirements : вимоги замовника (для підхоплення комплектуючих)
    margin        : коефіцієнт рентабельності; якщо ``None`` — береться з БД
                    (``cost_rates.global.default_margin``) або дефолт 1.10

    Returns
    -------
    dict з ключами:
        base_quantity, margin, breakdown (по компонентах),
        total_cost, cost_per_unit, price_per_unit, total_payment, currency
    """
    logger.info(f"Розрахунок собівартості: {len(routes)} маршрутів, тираж {base_quantity}")

    rates = _load_merged_rates()
    margin_eff = float(margin) if margin is not None else _global_rate(rates, "default_margin")

    comp_map: dict[str, dict] = {}
    for c in (components or []):
        comp_map[c.get("id", "")] = c

    breakdown: list[dict] = []
    for route in routes:
        comp_id   = route.get("component_id", "")
        component = comp_map.get(comp_id)
        result    = _calc_component(route, component, base_quantity, rates)
        breakdown.append(result)
        logger.debug(f"  {result['component_name']}: {result['subtotal']} грн")

    purchased_components = _calc_game_components_from_requirements(client_requirements)
    if purchased_components:
        breakdown.append(purchased_components)
        logger.debug(
            "  %s: %s грн",
            purchased_components["component_name"],
            purchased_components["subtotal"],
        )

    total_cost    = round(sum(b["subtotal"] for b in breakdown), 2)
    cost_per_unit = round(total_cost / base_quantity, 3) if base_quantity else 0
    price_per_unit = round(cost_per_unit * margin_eff, 2)
    total_payment  = round(price_per_unit * base_quantity, 2)

    logger.info(
        f"Собівартість: {total_cost} грн | "
        f"За одиницю: {cost_per_unit} грн | "
        f"До оплати: {total_payment} грн"
    )

    # --- tiers (для сумісності з generation/node.py) ----------------------
    tiers: dict[str, float] = {}
    v_setup_tier = _global_rate(rates, "vysichka_setup_uah")
    c_setup_tier = _global_rate(rates, "creasing_setup_uah")
    for qty in sorted({base_quantity, 500, 1_000, 2_500, 5_000}):
        # Пропорційне масштабування (тільки змінні витрати; приладка — фіксована)
        fixed   = sum(
            v_setup_tier + c_setup_tier
            for b in breakdown
            for li in b["line_items"]
            if "приладка" in li["item"].lower() or "висічка" in li["item"].lower()
        ) / max(len(breakdown), 1)
        variable_ratio = qty / base_quantity if base_quantity else 1
        est = round((total_cost - fixed) * variable_ratio * margin_eff + fixed, 2)
        tiers[f"{qty:,} шт."] = est

    return {
        "base_quantity":   base_quantity,
        "margin":          margin_eff,
        "breakdown":       breakdown,
        "total_cost":      total_cost,
        "cost_per_unit":   cost_per_unit,
        "price_per_unit":  price_per_unit,
        "total_payment":   total_payment,
        "tiers":           tiers,
        "currency":        "UAH",
        "note": (
            "Орієнтовна вартість без ПДВ. "
            "Ставки наближені — для точного розрахунку уточнюйте у менеджера."
        ),
    }
