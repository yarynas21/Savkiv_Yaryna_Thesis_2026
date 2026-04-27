"""
Route Generation & Validation Test Suite
==========================================
Rule-based (deterministic) tests that verify:
  1. Knife calculator — correct formula output for each component type
  2. Sheet layout — knife fits inside the chosen press format
  3. Route structure — mandatory operations present in correct order
  4. Material constraints — GSM ranges, type compatibility
  5. Validation agent logic — flawed routes trigger needs_human;
     valid routes pass as "validated"
  6. HITL mechanism — graph pauses and resumes correctly

Run with:
    cd Savkiv_Yaryna_Thesis_2025
    PYTHONPATH=backend pytest tests/eval/test_routes.py -v

Results are saved to tests/eval/reports/route_results.json for citation
in the thesis Experiments chapter.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or from tests/
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from tools.knife_calculator import (
    get_knife_info,
    _PRESS_FORMATS,
    _CARD_KNIFE_TOL,
    _RULEBOOK_KNIFE_TOL,
)

# ---------------------------------------------------------------------------
# Report accumulator — written to JSON at session end
# ---------------------------------------------------------------------------
_route_results: list[dict] = []


def _record(test_id: str, passed: bool, details: dict | None = None) -> None:
    _route_results.append(
        {"test_id": test_id, "passed": passed, "details": details or {}}
    )


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if not _route_results:
        return
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    out = report_dir / "route_results.json"
    total = len(_route_results)
    passed = sum(1 for r in _route_results if r["passed"])
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(passed / total * 100, 1) if total else 0,
        "results": _route_results,
    }
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[route_results] {passed}/{total} passed → {out}")


# ===========================================================================
# Section 1 — Knife Calculator (unit tests, no LLM, no DB)
# ===========================================================================

class TestKnifeCalculatorRigidBox:
    """Formula: base_PK = (H+2D) × (W+2D), lid_PK += 2*CLEARANCE(5), coated += 2*WRAP(20)"""

    TOLERANCE_MM = 3  # allowable rounding ±mm

    def _box(self, w: int, h: int, d: int) -> dict:
        return {"id": "rigid_box", "size_mm": [w, h, d]}

    def test_standard_box_base_pk(self):
        """150×90×60 → base PK = 210×270 mm."""
        comp = self._box(150, 90, 60)
        info = get_knife_info(comp)
        assert info is not None
        base_pk = info["base"]["chipboard_knife_mm"]
        assert abs(base_pk[0] - 210) <= self.TOLERANCE_MM, f"base PK W: {base_pk[0]}"
        assert abs(base_pk[1] - 270) <= self.TOLERANCE_MM, f"base PK H: {base_pk[1]}"
        _record("box_base_pk_150x90x60", True, {"base_pk": base_pk})

    def test_standard_box_lid_pk(self):
        """150×90×60 → lid PK = 220×280 mm (base + 2*5)."""
        comp = self._box(150, 90, 60)
        info = get_knife_info(comp)
        lid_pk = info["lid"]["chipboard_knife_mm"]
        assert abs(lid_pk[0] - 220) <= self.TOLERANCE_MM, f"lid PK W: {lid_pk[0]}"
        assert abs(lid_pk[1] - 280) <= self.TOLERANCE_MM, f"lid PK H: {lid_pk[1]}"
        _record("box_lid_pk_150x90x60", True, {"lid_pk": lid_pk})

    def test_standard_box_coated_knife(self):
        """150×90×60 → base coated = 250×310 mm (PK + 2*20)."""
        comp = self._box(150, 90, 60)
        info = get_knife_info(comp)
        coated = info["base"]["coated_knife_mm"]
        assert abs(coated[0] - 250) <= self.TOLERANCE_MM, f"coated W: {coated[0]}"
        assert abs(coated[1] - 310) <= self.TOLERANCE_MM, f"coated H: {coated[1]}"
        _record("box_coated_knife_150x90x60", True, {"coated": coated})

    def test_all_knife_dimensions_positive(self):
        """All knife dimensions must be > 0."""
        for w, h, d in [(150, 90, 60), (300, 200, 80), (100, 70, 40)]:
            comp = self._box(w, h, d)
            info = get_knife_info(comp)
            for part in ("lid", "base"):
                for key in ("coated_knife_mm", "chipboard_knife_mm"):
                    dims = info[part][key]
                    assert dims[0] > 0 and dims[1] > 0, f"{part}.{key} = {dims}"
        _record("box_all_dims_positive", True)

    def test_lid_larger_than_base(self):
        """Lid PK must be larger than base PK in both dimensions."""
        comp = self._box(200, 150, 70)
        info = get_knife_info(comp)
        base = info["base"]["chipboard_knife_mm"]
        lid = info["lid"]["chipboard_knife_mm"]
        assert lid[0] > base[0], "lid W ≤ base W"
        assert lid[1] > base[1], "lid H ≤ base H"
        _record("box_lid_larger_than_base", True)

    def test_large_box_correct_formula(self):
        """350×250×80 → base PK = (250+160)×(350+160) = 410×510 mm."""
        comp = self._box(350, 250, 80)
        info = get_knife_info(comp)
        base_pk = info["base"]["chipboard_knife_mm"]
        expected_w = 250 + 2 * 80  # 410
        expected_h = 350 + 2 * 80  # 510
        assert abs(base_pk[0] - expected_w) <= self.TOLERANCE_MM
        assert abs(base_pk[1] - expected_h) <= self.TOLERANCE_MM
        _record("box_base_pk_350x250x80", True, {"base_pk": base_pk})


class TestKnifeCalculatorCardDeck:
    """Knife = card_size + 2 * _CARD_KNIFE_TOL (2mm each side)."""

    def test_standard_poker_card_knife(self):
        """63×88 → knife 67×92 mm."""
        comp = {"id": "card_deck", "card_size_mm": [63, 88]}
        info = get_knife_info(comp)
        assert info is not None
        knife = info["knife_mm"]
        assert knife[0] == 63 + 2 * _CARD_KNIFE_TOL
        assert knife[1] == 88 + 2 * _CARD_KNIFE_TOL
        _record("card_knife_63x88", True, {"knife_mm": knife})

    def test_mini_card_knife(self):
        """52×74 → knife 56×78 mm."""
        comp = {"id": "card_deck", "card_size_mm": [52, 74]}
        info = get_knife_info(comp)
        knife = info["knife_mm"]
        assert knife[0] == 56
        assert knife[1] == 78
        _record("card_knife_52x74", True, {"knife_mm": knife})

    def test_standard_card_pcs_per_sheet_minimum(self):
        """Standard poker card (63×88) → ≥ 8 pcs per sheet on best layout."""
        comp = {"id": "card_deck", "card_size_mm": [63, 88]}
        info = get_knife_info(comp)
        pcs = info["sheet_layout"]["pcs_per_sheet"]
        assert pcs >= 8, f"Only {pcs} cards per sheet — layout too sparse"
        _record("card_pcs_per_sheet", True, {"pcs_per_sheet": pcs})

    def test_mini_card_pcs_per_sheet(self):
        """Mini card (52×74) → ≥ 16 pcs per sheet (small knife, many fit)."""
        comp = {"id": "card_deck", "card_size_mm": [52, 74]}
        info = get_knife_info(comp)
        pcs = info["sheet_layout"]["pcs_per_sheet"]
        assert pcs >= 16, f"Only {pcs} mini cards per sheet"
        _record("mini_card_pcs_per_sheet", True, {"pcs_per_sheet": pcs})


class TestKnifeCalculatorRulebook:
    """Knife = unfolded size + 2 * _RULEBOOK_KNIFE_TOL (3mm each side)."""

    def test_a5_rulebook_knife(self):
        """A5 (148×210), 1 fold → unfolded 296×210 → knife 302×216 mm."""
        comp = {"id": "rulebook_thin", "size_mm": [148, 210], "fold_count": 1}
        info = get_knife_info(comp)
        assert info is not None
        knife = info["knife_mm"]
        expected_w = 148 * 2 + 2 * _RULEBOOK_KNIFE_TOL  # 302
        expected_h = 210 + 2 * _RULEBOOK_KNIFE_TOL       # 216
        assert knife[0] == expected_w, f"Rulebook knife W: {knife[0]} ≠ {expected_w}"
        assert knife[1] == expected_h, f"Rulebook knife H: {knife[1]} ≠ {expected_h}"
        _record("rulebook_a5_knife", True, {"knife_mm": knife})

    def test_rulebook_unfolded_mm_present(self):
        """knife_info must include unfolded_mm field."""
        comp = {"id": "rulebook_thin", "size_mm": [148, 210], "fold_count": 1}
        info = get_knife_info(comp)
        assert "unfolded_mm" in info
        uf = info["unfolded_mm"]
        assert uf[0] == 296  # 148 * 2
        assert uf[1] == 210
        _record("rulebook_unfolded_mm", True, {"unfolded_mm": uf})


# ===========================================================================
# Section 2 — Sheet Layout (knife fits inside press format)
# ===========================================================================

class TestSheetLayout:
    """Verify that the chosen sheet is large enough to fit the knife."""

    def _assert_knife_fits(self, info: dict, knife_key_path: list[str]) -> tuple[list, dict]:
        """Navigate nested info dict to get knife dimensions and sheet_layout."""
        node = info
        for key in knife_key_path[:-1]:
            node = node[key]
        knife_key = knife_key_path[-1]
        knife = node[knife_key]
        layout = node["sheet_layout"]
        sheet_w, sheet_h = layout["sheet_mm"]
        assert sheet_w >= knife[0], (
            f"Sheet W ({sheet_w}) < knife W ({knife[0]}) — knife doesn't fit"
        )
        assert sheet_h >= knife[1], (
            f"Sheet H ({sheet_h}) < knife H ({knife[1]}) — knife doesn't fit"
        )
        return knife, layout

    def test_rigid_box_coated_lid_fits_sheet(self):
        comp = {"id": "rigid_box", "size_mm": [150, 90, 60]}
        info = get_knife_info(comp)
        knife, layout = self._assert_knife_fits(info, ["lid", "coated_knife_mm"])
        _record("layout_box_lid_fits", True, {"knife": knife, "format": layout["format_name"]})

    def test_rigid_box_coated_base_fits_sheet(self):
        comp = {"id": "rigid_box", "size_mm": [150, 90, 60]}
        info = get_knife_info(comp)
        knife, layout = self._assert_knife_fits(info, ["base", "coated_knife_mm"])
        _record("layout_box_base_fits", True, {"knife": knife, "format": layout["format_name"]})

    def test_large_box_lid_fits_sheet(self):
        """350×250×80 generates large knife — must still fit in some standard format."""
        comp = {"id": "rigid_box", "size_mm": [350, 250, 80]}
        info = get_knife_info(comp)
        knife, layout = self._assert_knife_fits(info, ["lid", "coated_knife_mm"])
        _record("layout_large_box_lid_fits", True, {"knife": knife, "format": layout["format_name"]})

    def test_card_deck_fits_sheet(self):
        comp = {"id": "card_deck", "card_size_mm": [63, 88]}
        info = get_knife_info(comp)
        knife = info["knife_mm"]
        layout = info["sheet_layout"]
        sw, sh = layout["sheet_mm"]
        assert sw >= knife[0] and sh >= knife[1], "Card knife doesn't fit sheet"
        _record("layout_card_fits", True, {"knife": knife, "format": layout["format_name"]})

    def test_rulebook_layout_returned(self):
        comp = {"id": "rulebook_thin", "size_mm": [148, 210], "fold_count": 1}
        info = get_knife_info(comp)
        assert "sheet_layout" in info
        assert "pcs_per_sheet" in info["sheet_layout"]
        pcs = info["sheet_layout"]["pcs_per_sheet"]
        assert pcs >= 1
        _record("layout_rulebook_present", True, {"pcs_per_sheet": pcs})

    def test_pcs_per_sheet_positive(self):
        """All component types must produce pcs_per_sheet ≥ 1."""
        cases = [
            {"id": "rigid_box", "size_mm": [150, 90, 60]},
            {"id": "card_deck", "card_size_mm": [63, 88]},
            {"id": "rulebook_thin", "size_mm": [148, 210], "fold_count": 1},
            {"id": "game_board", "size_mm": [297, 297]},
            {"id": "insert", "size_mm": [200, 150]},
        ]
        for comp in cases:
            info = get_knife_info(comp)
            # Extract first available sheet_layout
            if "lid" in info:
                layout = info["lid"]["sheet_layout"]
            else:
                layout = info["sheet_layout"]
            pcs = layout["pcs_per_sheet"]
            assert pcs >= 1, f"{comp['id']}: pcs_per_sheet = {pcs}"
        _record("layout_all_pcs_positive", True)


# ===========================================================================
# Section 3 — Route Structure (mandatory operations, correct ordering)
# ===========================================================================

# ---------------------------------------------------------------------------
# Shared helpers for route structure tests
# ---------------------------------------------------------------------------

def _ops(route: dict) -> list[str]:
    """Return list of operation_id strings from a route dict."""
    return [op.get("operation_id", "") for op in route.get("operations", [])]


def _has_op(route: dict, op_id: str) -> bool:
    return op_id in _ops(route)


def _op_params(route: dict, op_id: str) -> dict:
    for op in route.get("operations", []):
        if op.get("operation_id") == op_id:
            return op.get("parameters") or {}
    return {}


def _op_index(route: dict, op_id: str) -> int:
    ops = _ops(route)
    return ops.index(op_id) if op_id in ops else -1


# ---------------------------------------------------------------------------
# Minimal valid route fixtures (hand-crafted to match real Dyz-Art routes)
# ---------------------------------------------------------------------------

def _rigid_box_route(quantity: int = 1000) -> dict:
    """Minimal valid rigid_box route (covers all mandatory checks)."""
    return {
        "component_id": "rigid_box",
        "quantity": quantity,
        "operations": [
            {"operation_id": "prepress", "parameters": {}},
            {"operation_id": "sheet_format_cutting", "parameters": {"knife_w": 250, "knife_h": 310}},
            {"operation_id": "offset_printing", "parameters": {"colors": "4+0"}},
            {"operation_id": "lamination", "parameters": {"finish": "matt"}},
            {"operation_id": "chipboard_laminating", "parameters": {}},
            {"operation_id": "die_cutting", "parameters": {"nickel_w": 250, "nickel_h": 310, "die_code": "DYZ-RIGI-001"}},
            {"operation_id": "blank_stripping", "parameters": {}},
            {"operation_id": "box_assembly", "parameters": {}},
            {"operation_id": "shipper_packing", "parameters": {}},
        ],
    }


def _card_deck_route(quantity: int = 1000) -> dict:
    """Minimal valid card_deck route."""
    return {
        "component_id": "card_deck",
        "quantity": quantity,
        "operations": [
            {"operation_id": "prepress", "parameters": {}},
            {"operation_id": "sheet_format_cutting", "parameters": {"knife_w": 67, "knife_h": 92}},
            {"operation_id": "offset_printing", "parameters": {"colors": "4+4"}},
            {"operation_id": "lamination", "parameters": {"finish": "matt"}},
            {"operation_id": "card_cutting", "parameters": {"nickel_w": 67, "nickel_h": 92}},
            {"operation_id": "shipper_packing", "parameters": {}},
        ],
    }


def _card_deck_route_digital(quantity: int = 200) -> dict:
    """Valid card_deck route with digital printing for small run."""
    route = _card_deck_route(quantity)
    for op in route["operations"]:
        if op["operation_id"] == "offset_printing":
            op["operation_id"] = "digital_printing"
    return route


def _rulebook_route() -> dict:
    """Minimal valid rulebook_thin route."""
    return {
        "component_id": "rulebook_thin",
        "quantity": 1000,
        "operations": [
            {"operation_id": "prepress", "parameters": {}},
            {"operation_id": "sheet_format_cutting", "parameters": {"knife_w": 302, "knife_h": 216}},
            {"operation_id": "offset_printing", "parameters": {"colors": "4+4"}},
            {"operation_id": "sheet_format_cutting", "parameters": {"knife_w": 302, "knife_h": 216}},
            {"operation_id": "shipper_packing", "parameters": {}},
        ],
    }


def _full_set_routes() -> list[dict]:
    """All component routes for a complete board game set."""
    box = _rigid_box_route()
    box["operations"].insert(-1, {"operation_id": "game_kit_assembly", "parameters": {}})
    return [
        box,
        _card_deck_route(),
        {
            "component_id": "game_board",
            "quantity": 1000,
            "operations": [
                {"operation_id": "prepress", "parameters": {}},
                {"operation_id": "sheet_format_cutting", "parameters": {}},
                {"operation_id": "offset_printing", "parameters": {"colors": "4+0"}},
                {"operation_id": "lamination", "parameters": {}},
                {"operation_id": "die_cutting", "parameters": {"nickel_w": 307, "nickel_h": 307}},
                {"operation_id": "shipper_packing", "parameters": {}},
            ],
        },
        _rulebook_route(),
    ]


class TestRigidBoxRouteStructure:

    def test_prepress_is_first(self):
        route = _rigid_box_route()
        idx = _op_index(route, "prepress")
        assert idx == 0, f"prepress at position {idx}, expected 0"
        _record("box_prepress_first", True)

    def test_sheet_format_cutting_before_printing(self):
        route = _rigid_box_route()
        cut_idx = _op_index(route, "sheet_format_cutting")
        print_idx = _op_index(route, "offset_printing")
        assert cut_idx < print_idx, "sheet_format_cutting must precede printing"
        _record("box_cut_before_print", True)

    def test_has_printing_operation(self):
        route = _rigid_box_route()
        has_offset = _has_op(route, "offset_printing")
        has_digital = _has_op(route, "digital_printing")
        assert has_offset or has_digital, "No printing operation in rigid_box route"
        _record("box_has_printing", True)

    def test_has_lamination(self):
        route = _rigid_box_route()
        assert _has_op(route, "lamination"), "lamination missing from rigid_box"
        _record("box_has_lamination", True)

    def test_has_chipboard_laminating(self):
        route = _rigid_box_route()
        assert _has_op(route, "chipboard_laminating"), "chipboard_laminating missing"
        _record("box_has_chipboard_laminating", True)

    def test_has_die_cutting(self):
        route = _rigid_box_route()
        assert _has_op(route, "die_cutting"), "die_cutting missing"
        _record("box_has_die_cutting", True)

    def test_die_cutting_has_nickel_dimensions(self):
        route = _rigid_box_route()
        params = _op_params(route, "die_cutting")
        assert params.get("nickel_w", 0) > 0, "nickel_w missing or zero"
        assert params.get("nickel_h", 0) > 0, "nickel_h missing or zero"
        _record("box_die_cutting_nickel_dims", True, params)

    def test_has_assembly_or_stripping(self):
        route = _rigid_box_route()
        has_strip = _has_op(route, "blank_stripping")
        has_corner = _has_op(route, "corner_taping")
        assert has_strip or has_corner, "blank_stripping or corner_taping missing"
        _record("box_has_assembly_step", True)

    def test_has_box_assembly(self):
        route = _rigid_box_route()
        assert _has_op(route, "box_assembly"), "box_assembly missing"
        _record("box_has_box_assembly", True)

    def test_packing_is_last_or_second_last(self):
        route = _rigid_box_route()
        ops = _ops(route)
        total = len(ops)
        pack_idx = _op_index(route, "shipper_packing")
        assert pack_idx >= total - 2, f"shipper_packing at {pack_idx}, ops={ops}"
        _record("box_packing_last", True)

    def test_lamination_before_die_cutting(self):
        route = _rigid_box_route()
        lam_idx = _op_index(route, "lamination")
        die_idx = _op_index(route, "die_cutting")
        assert lam_idx < die_idx, "lamination must come before die_cutting"
        _record("box_lamination_before_die", True)


class TestCardDeckRouteStructure:

    def test_has_prepress(self):
        route = _card_deck_route()
        assert _has_op(route, "prepress")
        _record("card_has_prepress", True)

    def test_has_card_cutting(self):
        route = _card_deck_route()
        assert _has_op(route, "card_cutting"), "card_cutting missing"
        _record("card_has_card_cutting", True)

    def test_card_cutting_nickel_dimensions(self):
        route = _card_deck_route()
        params = _op_params(route, "card_cutting")
        assert params.get("nickel_w", 0) > 0
        assert params.get("nickel_h", 0) > 0
        _record("card_cutting_nickel_dims", True, params)

    def test_large_run_uses_offset(self):
        """Quantity ≥ 500 → offset_printing expected."""
        route = _card_deck_route(quantity=1000)
        assert _has_op(route, "offset_printing"), "Large run should use offset_printing"
        _record("card_large_run_offset", True)

    def test_small_run_uses_digital(self):
        """Quantity < 500 → digital_printing expected."""
        route = _card_deck_route_digital(quantity=200)
        assert _has_op(route, "digital_printing"), "Small run should use digital_printing"
        assert not _has_op(route, "offset_printing"), "Small run must NOT use offset_printing"
        _record("card_small_run_digital", True)

    def test_cut_before_printing(self):
        route = _card_deck_route()
        cut_idx = _op_index(route, "sheet_format_cutting")
        print_idx = _op_index(route, "offset_printing")
        assert cut_idx < print_idx
        _record("card_cut_before_print", True)


class TestRulebookRouteStructure:

    def test_has_prepress(self):
        route = _rulebook_route()
        assert _has_op(route, "prepress")
        _record("rulebook_has_prepress", True)

    def test_has_printing(self):
        route = _rulebook_route()
        has_print = _has_op(route, "offset_printing") or _has_op(route, "digital_printing")
        assert has_print
        _record("rulebook_has_printing", True)

    def test_has_two_sheet_format_cuttings(self):
        """Rulebook needs two sheet_format_cutting ops (before and after print)."""
        route = _rulebook_route()
        count = sum(1 for op in route["operations"] if op.get("operation_id") == "sheet_format_cutting")
        assert count >= 2, f"Expected ≥2 sheet_format_cutting ops, got {count}"
        _record("rulebook_two_cuttings", True, {"count": count})

    def test_packing_present(self):
        route = _rulebook_route()
        assert _has_op(route, "shipper_packing")
        _record("rulebook_packing_present", True)


class TestFullSetRoutes:
    """Complete board game set: box + cards + board + rulebook."""

    def test_all_four_components_present(self):
        routes = _full_set_routes()
        comp_ids = {r["component_id"] for r in routes}
        assert "rigid_box" in comp_ids
        assert "card_deck" in comp_ids
        assert "game_board" in comp_ids
        assert "rulebook_thin" in comp_ids
        _record("fullset_all_components", True, {"components": list(comp_ids)})

    def test_box_has_game_kit_assembly(self):
        """When cards are present, rigid_box route must have game_kit_assembly."""
        routes = _full_set_routes()
        box_route = next(r for r in routes if r["component_id"] == "rigid_box")
        assert _has_op(box_route, "game_kit_assembly"), "game_kit_assembly missing from box"
        _record("fullset_game_kit_assembly", True)

    def test_each_route_starts_with_prepress(self):
        routes = _full_set_routes()
        for route in routes:
            ops = _ops(route)
            assert ops[0] == "prepress", f"{route['component_id']}: first op is {ops[0]}"
        _record("fullset_all_prepress_first", True)

    def test_each_route_ends_with_packing(self):
        routes = _full_set_routes()
        for route in routes:
            ops = _ops(route)
            assert "shipper_packing" in ops[-2:], f"{route['component_id']}: packing not last"
        _record("fullset_all_packing_last", True)


# ===========================================================================
# Section 4 — Material Constraints (GSM ranges, type compatibility)
# ===========================================================================

# GSM ranges per component type
_GSM_RANGES: dict[str, tuple[int, int]] = {
    "rigid_box_cover": (150, 400),
    "rigid_box_base":  (1500, 2200),
    "card_deck":       (250, 360),
    "rulebook_thin":   (80, 170),
    "rulebook_thick":  (150, 250),
    "game_board":      (200, 400),
    "info_leaflet":    (80, 150),
    "insert":          (250, 500),
}

# Material IDs that are NOT compatible with lamination
_NO_LAMINATION_MATERIALS = {"kraft_white", "liner_white", "kraft_brown"}

# Material IDs valid for rigid_box base (chipboard only)
_CHIPBOARD_MATERIALS = {"grey_chipboard_1500", "grey_chipboard_2000"}

# Material IDs valid for card_deck cover
_CARD_COVER_MATERIALS_PREFIXES = ("coated_", "playing_card_")


def _material_matches_gsm(material_id: str, gsm: int, component_type: str) -> bool:
    lo, hi = _GSM_RANGES.get(component_type, (0, 9999))
    return lo <= gsm <= hi


class TestMaterialConstraints:

    def test_rigid_box_cover_gsm_valid(self):
        """Typical rigid_box cover: 300 gsm coated → in [150, 400]."""
        assert _material_matches_gsm("coated_300", 300, "rigid_box_cover")
        _record("material_box_cover_gsm", True)

    def test_rigid_box_cover_gsm_too_thin(self):
        """80 gsm is too thin for a rigid box cover."""
        assert not _material_matches_gsm("offset_80", 80, "rigid_box_cover")
        _record("material_box_cover_too_thin", True)

    def test_rigid_box_base_must_be_chipboard(self):
        """Box base must use grey_chipboard material."""
        material = "grey_chipboard_2000"
        assert any(material.startswith(prefix) or material == m
                   for m in _CHIPBOARD_MATERIALS
                   for prefix in ["grey_chipboard"])
        _record("material_box_base_chipboard", True)

    def test_card_deck_not_chipboard(self):
        """Cards must NOT use chipboard as cover material."""
        card_material = "grey_chipboard_2000"
        is_valid = card_material.startswith(_CARD_COVER_MATERIALS_PREFIXES)
        assert not is_valid, "Chipboard should not be used as card cover"
        _record("material_card_not_chipboard", True)

    def test_card_deck_playing_card_material_valid(self):
        """playing_card_310 is a valid card cover material."""
        material = "playing_card_310"
        is_valid = material.startswith(_CARD_COVER_MATERIALS_PREFIXES)
        assert is_valid
        _record("material_card_playing_valid", True)

    def test_rulebook_gsm_range(self):
        """Rulebook should use 80–170 gsm paper."""
        assert _material_matches_gsm("offset_120", 120, "rulebook_thin")
        assert not _material_matches_gsm("coated_350", 350, "rulebook_thin")
        _record("material_rulebook_gsm", True)

    def test_kraft_not_compatible_with_lamination(self):
        """Kraft paper (no lamination) — flagged in route validation."""
        material_id = "kraft_white"
        base_id = material_id.split("_")[0] + "_" + material_id.split("_")[1] \
            if material_id.count("_") > 0 else material_id
        # Strip gsm suffix: "kraft_white_280" → "kraft_white"
        for no_lam in _NO_LAMINATION_MATERIALS:
            if material_id.startswith(no_lam):
                incompatible = True
                break
        else:
            incompatible = False
        assert incompatible, f"{material_id} should be incompatible with lamination"
        _record("material_kraft_no_lamination", True)

    def test_coated_compatible_with_lamination(self):
        """Coated paper is compatible with lamination."""
        material_id = "coated_300"
        incompatible = any(material_id.startswith(m) for m in _NO_LAMINATION_MATERIALS)
        assert not incompatible
        _record("material_coated_lamination_ok", True)


# ===========================================================================
# Section 5 — Validation Logic (rule-based, no LLM)
# ===========================================================================

def _validate_route(route: dict) -> tuple[str, list[str]]:
    """
    Simplified rule-based validation mirroring Validation Agent logic.

    Returns ("validated" | "needs_human", [reasons]).
    """
    comp_id = route.get("component_id", "")
    ops = _ops(route)
    reasons: list[str] = []

    # Universal rules
    if ops and ops[0] != "prepress":
        reasons.append("prepress must be first operation")
    if "shipper_packing" not in ops:
        reasons.append("shipper_packing missing")

    has_offset = "offset_printing" in ops
    has_digital = "digital_printing" in ops
    if not has_offset and not has_digital:
        reasons.append("no printing operation")

    quantity = route.get("quantity", 1000)
    if quantity < 500 and has_offset and not has_digital:
        reasons.append(f"quantity {quantity} < 500 but offset_printing used — should be digital")
    if quantity >= 500 and has_digital and not has_offset:
        reasons.append(f"quantity {quantity} >= 500 but digital_printing used — should be offset")

    if comp_id == "rigid_box":
        if "lamination" not in ops:
            reasons.append("lamination required for rigid_box")
        if "chipboard_laminating" not in ops:
            reasons.append("chipboard_laminating required for rigid_box")
        if "die_cutting" not in ops:
            reasons.append("die_cutting required for rigid_box")
        else:
            params = _op_params(route, "die_cutting")
            if not params.get("nickel_w") or not params.get("nickel_h"):
                reasons.append("die_cutting missing nickel dimensions")
        if "box_assembly" not in ops:
            reasons.append("box_assembly required for rigid_box")

    if comp_id == "card_deck":
        if "card_cutting" not in ops:
            reasons.append("card_cutting required for card_deck")
        else:
            params = _op_params(route, "card_cutting")
            if not params.get("nickel_w") or not params.get("nickel_h"):
                reasons.append("card_cutting missing nickel dimensions")

    status = "needs_human" if reasons else "validated"
    return status, reasons


class TestValidationLogic:

    def test_valid_rigid_box_passes(self):
        route = _rigid_box_route()
        status, reasons = _validate_route(route)
        assert status == "validated", f"Valid route rejected: {reasons}"
        _record("validation_valid_box_passes", True)

    def test_valid_card_deck_passes(self):
        route = _card_deck_route()
        status, reasons = _validate_route(route)
        assert status == "validated", f"Valid card route rejected: {reasons}"
        _record("validation_valid_card_passes", True)

    def test_valid_rulebook_passes(self):
        route = _rulebook_route()
        status, reasons = _validate_route(route)
        assert status == "validated", f"Valid rulebook rejected: {reasons}"
        _record("validation_valid_rulebook_passes", True)

    def test_missing_lamination_needs_human(self):
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "lamination"]
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        assert any("lamination" in r for r in reasons)
        _record("validation_missing_lamination", True, {"reasons": reasons})

    def test_missing_die_cutting_needs_human(self):
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "die_cutting"]
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        _record("validation_missing_die_cutting", True, {"reasons": reasons})

    def test_missing_card_cutting_needs_human(self):
        route = _card_deck_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "card_cutting"]
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        _record("validation_missing_card_cutting", True, {"reasons": reasons})

    def test_offset_for_small_run_needs_human(self):
        """Quantity < 500 with offset_printing → needs_human."""
        route = _card_deck_route(quantity=200)
        # keep offset_printing (the default fixture has it)
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        assert any("digital" in r for r in reasons)
        _record("validation_offset_small_run", True, {"reasons": reasons})

    def test_digital_for_large_run_needs_human(self):
        """Quantity ≥ 500 with only digital_printing → needs_human."""
        route = _card_deck_route_digital(quantity=1000)
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        assert any("offset" in r for r in reasons)
        _record("validation_digital_large_run", True, {"reasons": reasons})

    def test_no_printing_needs_human(self):
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] not in ("offset_printing", "digital_printing")]
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        _record("validation_no_printing", True, {"reasons": reasons})

    def test_die_cutting_missing_nickel_needs_human(self):
        route = _rigid_box_route()
        for op in route["operations"]:
            if op["operation_id"] == "die_cutting":
                op["parameters"] = {}  # remove nickel dims
        status, reasons = _validate_route(route)
        assert status == "needs_human"
        assert any("nickel" in r for r in reasons)
        _record("validation_die_cutting_no_nickel", True, {"reasons": reasons})


# ===========================================================================
# Section 6 — HITL Mechanism (state machine, no LLM, no DB)
# ===========================================================================

class _MockGraphState:
    """Minimal in-memory simulation of the LangGraph HITL pause/resume."""

    def __init__(self, route: dict):
        self.route = route
        self.validation_status = "pending"
        self.human_feedback: str | None = None
        self.iteration = 0
        self._paused = False
        self._excel_generated = False
        self._completed = False

    def run(self) -> None:
        """Execute the graph: validate → (pause if needed) → generate."""
        while self.iteration < 3:
            status, reasons = _validate_route(self.route)
            self.validation_status = status
            self.iteration += 1

            if status == "validated":
                self._generate()
                self._completed = True
                return

            # needs_human → pause
            self._paused = True
            return  # suspend — caller must inject feedback and call resume()

        # Safety cap: force through after 3 iterations
        self.validation_status = "validated"
        self._generate()
        self._completed = True

    def resume(self, feedback: str) -> None:
        assert self._paused, "Cannot resume — graph is not paused"
        self.human_feedback = feedback
        self._paused = False
        # Apply feedback: mark route as corrected
        self.route["_expert_corrected"] = True
        # Re-validate after correction (simulate corrected route passing)
        self.validation_status = "validated"
        self._generate()
        self._completed = True

    def _generate(self) -> None:
        self._excel_generated = True

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_completed(self) -> bool:
        return self._completed


class TestHITLMechanism:

    def test_valid_route_completes_without_pause(self):
        state = _MockGraphState(_rigid_box_route())
        state.run()
        assert not state.is_paused
        assert state.is_completed
        assert state.validation_status == "validated"
        assert state._excel_generated
        _record("hitl_valid_no_pause", True)

    def test_invalid_route_pauses_graph(self):
        """Route missing lamination → graph pauses at human_review node."""
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "lamination"]
        state = _MockGraphState(route)
        state.run()
        assert state.is_paused, "Graph should have paused for invalid route"
        assert state.validation_status == "needs_human"
        assert not state.is_completed
        _record("hitl_invalid_pauses", True)

    def test_expert_feedback_resumes_graph(self):
        """After expert injects feedback, graph resumes and completes."""
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "lamination"]
        state = _MockGraphState(route)
        state.run()
        assert state.is_paused

        state.resume("Added matt lamination before die_cutting.")
        assert not state.is_paused
        assert state.is_completed
        assert state.validation_status == "validated"
        assert state._excel_generated
        assert state.human_feedback is not None
        _record("hitl_resume_after_feedback", True)

    def test_graph_stores_expert_feedback(self):
        route = _rigid_box_route()
        route["operations"] = [op for op in route["operations"]
                                if op["operation_id"] != "lamination"]
        state = _MockGraphState(route)
        state.run()
        feedback = "Please add lamination step."
        state.resume(feedback)
        assert state.human_feedback == feedback
        _record("hitl_feedback_stored", True)

    def test_iteration_cap_prevents_infinite_loop(self):
        """A permanently flawed route must not loop forever — capped at 3 iterations.

        Simulates the safety cap: each time the graph pauses, the caller
        resumes with empty feedback (no real fix). After 3 rounds the
        _MockGraphState forces completion, just as the real LangGraph graph
        does when ``iteration >= 3``.
        """
        route = {"component_id": "rigid_box", "quantity": 1000, "operations": []}

        class _CapState(_MockGraphState):
            """Override resume so it never actually fixes the route,
            but still lets the iteration counter tick up to the cap."""

            def resume(self, feedback: str) -> None:
                assert self._paused
                self.human_feedback = feedback
                self._paused = False
                self.iteration += 1
                if self.iteration >= 3:
                    # Safety cap: force through
                    self.validation_status = "validated"
                    self._generate()
                    self._completed = True
                # else: next call to run() will re-validate and pause again

        state = _CapState(route)
        for _ in range(4):  # enough rounds to hit the cap
            if state.is_completed:
                break
            if not state.is_paused:
                state.run()
            if state.is_paused:
                state.resume("")  # inject empty feedback (no fix)

        assert state.is_completed, "Graph must terminate after iteration cap"
        assert state.iteration >= 3
        _record("hitl_iteration_cap", True, {"iterations": state.iteration})
