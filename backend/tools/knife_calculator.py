"""
Knife & Sheet Layout Calculator
================================
Calculates die-cutting knife dimensions and sheet layout (розкладка)
for each component type based on product dimensions.

Knife formulas are derived from real Dyz-Art production calculations.
"""

from __future__ import annotations

import math
from typing import Any

# Standard press sheet formats (width × height, mm)
# Ordered from smallest to largest
_PRESS_FORMATS: list[tuple[str, int, int]] = [
    ("A3",  297, 420),
    ("B3",  350, 500),
    ("A2",  420, 594),
    ("B2",  500, 700),
    ("A1",  594, 841),
    ("B1",  700, 1000),
    ("A0",  841, 1189),
]

# Wrap-around margin (mm) when coated paper wraps inside the box wall
_WRAP_MARGIN = 15
# Bleed margin per side (mm) for printing bleeds
_PRINT_BLEED = 5
# Die-cut tolerance (mm) added to each side of knife for cards/rulebooks
_CARD_KNIFE_TOL = 2
_RULEBOOK_KNIFE_TOL = 3
# Minimum pieces per sheet to consider a layout efficient
_MIN_PIECES_PER_SHEET = 2


def _best_layout(
    knife_w: int, knife_h: int
) -> tuple[str, int, int, int, int, int]:
    """
    Find the most suitable press format for the given knife size.

    Returns (format_name, sheet_w, sheet_h, cols, rows, pcs_per_sheet).
    Tries all standard formats in both orientations; picks the smallest
    sheet that fits at least _MIN_PIECES_PER_SHEET pieces.
    """
    best: tuple[str, int, int, int, int, int] | None = None
    best_pcs = 0

    for name, sw, sh in _PRESS_FORMATS:
        for fw, fh in [(sw, sh), (sh, sw)]:  # both orientations
            cols = fw // knife_w
            rows = fh // knife_h
            pcs  = cols * rows
            if pcs < _MIN_PIECES_PER_SHEET:
                continue
            if best is None or pcs < best_pcs or (
                pcs == best_pcs and fw * fh < best[1] * best[2]
            ):
                best = (name, fw, fh, cols, rows, pcs)
                best_pcs = pcs

    if best is None:
        # Fallback: use B1 (largest standard)
        fw, fh = 700, 1000
        cols = max(1, fw // knife_w)
        rows = max(1, fh // knife_h)
        best = ("B1", fw, fh, cols, rows, cols * rows)

    return best



def _knife_rigid_box(
    box_w: int, box_h: int, box_d: int
) -> dict[str, Any]:
    """
    Rigid box — telegram/telescope type (кришка + дно).

    Formula reverse-engineered from real Dyz-Art narad files:

    Box 150×90×60 (W×H×D):
      base PK  = (H+2D) × (W+2D)  = 210×270 mm   ← cross-shaped blank
      lid  PK  = base_PK + 2*CLEARANCE             = 219×279 mm
      base coated = base_PK + 2*WRAP               = 250×310 mm
      lid  coated = lid_PK  + 2*WRAP               = 259×319 mm

    Constants:
      WRAP      = 20 mm  (inside wrap of coated paper over chipboard wall)
      CLEARANCE = 4.5 mm (lid over base sliding clearance)
    """
    WRAP      = 20    # mm — coated paper wrap inside the box wall
    CLEARANCE = 5     # mm — lid slightly larger than base (per side)

    # Base (inner/bottom box): cross-shaped PK blank
    # Short arm = H + 2*D, long arm = W + 2*D
    pk_base_w = box_h + 2 * box_d
    pk_base_h = box_w + 2 * box_d

    # Lid (outer sleeve): same cross shape but larger by CLEARANCE
    pk_lid_w = pk_base_w + 2 * CLEARANCE
    pk_lid_h = pk_base_h + 2 * CLEARANCE

    # Coated paper (обклейка): PK blank + WRAP on each side
    c_base_w = pk_base_w + 2 * WRAP
    c_base_h = pk_base_h + 2 * WRAP
    c_lid_w  = pk_lid_w  + 2 * WRAP
    c_lid_h  = pk_lid_h  + 2 * WRAP

    lid_layout  = _best_layout(c_lid_w,  c_lid_h)
    base_layout = _best_layout(c_base_w, c_base_h)

    return {
        "lid": {
            "coated_knife_mm":    [c_lid_w,  c_lid_h],
            "chipboard_knife_mm": [pk_lid_w, pk_lid_h],
            "sheet_layout":        _format_layout(lid_layout),
        },
        "base": {
            "coated_knife_mm":    [c_base_w, c_base_h],
            "chipboard_knife_mm": [pk_base_w, pk_base_h],
            "sheet_layout":        _format_layout(base_layout),
        },
    }


def _knife_card_deck(card_w: int, card_h: int) -> dict[str, Any]:
    """
    Card deck.

    Knife = card size + _CARD_KNIFE_TOL on each side (die registration margin).
    Layout: pack as many cards on the sheet as possible.
    """
    kw = card_w + 2 * _CARD_KNIFE_TOL
    kh = card_h + 2 * _CARD_KNIFE_TOL
    layout = _best_layout(kw, kh)
    return {
        "knife_mm": [kw, kh],
        "sheet_layout": _format_layout(layout),
    }


def _knife_rulebook(page_w: int, page_h: int, folds: int = 1) -> dict[str, Any]:
    """
    Rulebook / leaflet.

    The knife size equals the unfolded sheet size.
    For a booklet folded in half (folds=1): unfolded_w = page_w * 2.
    For a 4-panel (folds=2): unfolded_w = page_w * 4, etc.
    Sheet layout is for the folded page unit on press.
    """
    unfolded_w = page_w * (2 ** folds)
    unfolded_h = page_h
    kw = unfolded_w + 2 * _RULEBOOK_KNIFE_TOL
    kh = unfolded_h + 2 * _RULEBOOK_KNIFE_TOL
    # Press layout: use the folded page size to find how many fit per sheet
    layout = _best_layout(page_w + _PRINT_BLEED, page_h + _PRINT_BLEED)
    return {
        "knife_mm": [kw, kh],
        "unfolded_mm": [unfolded_w, unfolded_h],
        "sheet_layout": _format_layout(layout),
    }


def _knife_game_board(board_w: int, board_h: int) -> dict[str, Any]:
    """
    Game board (foldable, printed on coated paper then laminated).

    Knife = board size + bleed on each side.
    """
    kw = board_w + 2 * _PRINT_BLEED
    kh = board_h + 2 * _PRINT_BLEED
    layout = _best_layout(kw, kh)
    return {
        "knife_mm": [kw, kh],
        "sheet_layout": _format_layout(layout),
    }


def _knife_insert(w: int, h: int) -> dict[str, Any]:
    """Generic insert / inlay."""
    kw = w + 2 * _CARD_KNIFE_TOL
    kh = h + 2 * _CARD_KNIFE_TOL
    layout = _best_layout(kw, kh)
    return {
        "knife_mm": [kw, kh],
        "sheet_layout": _format_layout(layout),
    }


def _format_layout(layout: tuple) -> dict[str, Any]:
    name, fw, fh, cols, rows, pcs = layout
    return {
        "format_name": name,
        "sheet_mm": [fw, fh],
        "cols": cols,
        "rows": rows,
        "pcs_per_sheet": pcs,
        "label": f"{fw/1000:.3g}×{fh/1000:.3g} м  ({cols}×{rows}={pcs} шт.)",
    }



def get_knife_info(component: dict[str, Any]) -> dict[str, Any] | None:
    """
    Given a product_component dict (from ProductionState), return knife
    and layout information.

    Expected component keys:
    - "id" / "component_id": component type identifier
    - "size_mm": [width, height] or [width, height, depth] for boxes
    - "card_size_mm": [w, h] for card decks
    - "fold_count": number of folds for rulebooks
    """
    comp_id  = str(component.get("id") or component.get("component_id") or "").lower()
    size_mm: list[int] = component.get("size_mm") or []

    def _s(i: int, default: int = 100) -> int:
        try:
            return int(size_mm[i])
        except (IndexError, TypeError, ValueError):
            return default

    if comp_id in ("rigid_box", "folding_box"):
        w, h, d = _s(0, 150), _s(1, 90), _s(2, 60)
        return _knife_rigid_box(w, h, d)

    if comp_id == "card_deck":
        card_size = component.get("card_size_mm") or size_mm
        try:
            cw, ch = int(card_size[0]), int(card_size[1])
        except (IndexError, TypeError, ValueError):
            cw, ch = 63, 88  # standard poker card
        return _knife_card_deck(cw, ch)

    if comp_id in ("rulebook_thin", "rulebook_thick", "info_leaflet"):
        w, h = _s(0, 148), _s(1, 210)
        folds = int(component.get("fold_count") or 1)
        return _knife_rulebook(w, h, folds)

    if comp_id == "game_board":
        w, h = _s(0, 297), _s(1, 297)
        return _knife_game_board(w, h)

    if comp_id == "insert":
        w, h = _s(0, 200), _s(1, 150)
        return _knife_insert(w, h)

    return None


def enrich_component_with_knife(component: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *component* with knife_info added."""
    info = get_knife_info(component)
    if info:
        component = dict(component)
        component["knife_info"] = info
    return component
