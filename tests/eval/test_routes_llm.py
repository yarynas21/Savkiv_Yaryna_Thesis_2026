"""
Route Generation — LLM Integration Tests
==========================================
End-to-end tests that invoke the real Technologist Agent (LLM call) and
verify the resulting production routes satisfy structural invariants.

Also includes 4 LLM-as-Judge scenarios where GPT-4.1 evaluates route quality
for properties that rule-based checks cannot capture.

Run with:
    cd Savkiv_Yaryna_Thesis_2025
    PYTHONPATH=backend pytest tests/eval/test_routes_llm.py -v -s

Results are saved to tests/eval/reports/route_llm_results.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ---------------------------------------------------------------------------
# Report accumulator
# ---------------------------------------------------------------------------
_results: list[dict] = []


def _record(test_id: str, passed: bool, details: dict | None = None) -> None:
    _results.append({"test_id": test_id, "passed": passed, "details": details or {}})


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if not _results:
        return
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    out = report_dir / "route_llm_results.json"
    total = len(_results)
    passed = sum(1 for r in _results if r["passed"])
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(passed / total * 100, 1) if total else 0,
        "results": _results,
    }
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[route_llm_results] {passed}/{total} passed → {out}")


# ---------------------------------------------------------------------------
# Helpers — invoke technologist agent directly
# ---------------------------------------------------------------------------

def _run_technologist(components: list[dict], requirements: dict) -> list[dict]:
    """Call technologist_node with a synthetic ProductionState and return routes."""
    from agents.technologist.node import technologist_node

    state: dict[str, Any] = {
        "product_components": components,
        "client_requirements": requirements,
        "production_routes": [],
        "validation_status": "pending",
        "messages": [],
        "llm_eval": {"rows": [], "session_call_count": 0},
    }
    result = technologist_node(state)
    return result.get("production_routes", [])


def _ops(route: dict) -> list[str]:
    return [op.get("operation_id", "") for op in route.get("operations", [])]


def _has_op(route: dict, op_id: str) -> bool:
    return op_id in _ops(route)


def _find_route(routes: list[dict], comp_id: str) -> dict | None:
    for r in routes:
        if r.get("component_id") == comp_id:
            return r
    return None


# ===========================================================================
# PART 1 — End-to-End LLM Route Generation Tests
# ===========================================================================

class TestLLMRigidBoxRoute:
    """Single rigid box order — LLM must produce a structurally valid route."""

    COMPONENTS = [
        {
            "id": "rigid_box",
            "type": "rigid_box",
            "name": "Test Box",
            "size_mm": [300, 200, 60],
            "construction": "lid_and_base",
            "material": "bookbinding_board",
            "board_thickness_mm": 1.75,
            "lamination": "matte",
            "print_sides": "outside_only",
            "uv_varnish": False,
            "shrink_wrap": False,
        }
    ]
    REQUIREMENTS = {
        "quantity": 1000,
        "product_name": "Test Game",
        "client_name": "Test Client",
        "deadline_days": 30,
    }

    @pytest.fixture(scope="class")
    def routes(self):
        return _run_technologist(self.COMPONENTS, self.REQUIREMENTS)

    def test_route_generated(self, routes):
        assert len(routes) >= 1, "No routes generated"
        _record("llm_box_route_generated", True, {"routes_count": len(routes)})

    def test_box_route_has_prepress(self, routes):
        route = _find_route(routes, "rigid_box")
        assert route is not None
        ops = _ops(route)
        assert ops[0] == "prepress", f"First op: {ops[0]}"
        _record("llm_box_prepress_first", True)

    def test_box_route_has_printing(self, routes):
        route = _find_route(routes, "rigid_box")
        has_print = _has_op(route, "offset_printing") or _has_op(route, "digital_printing")
        assert has_print, f"No printing op in: {_ops(route)}"
        _record("llm_box_has_printing", True)

    def test_box_route_has_lamination(self, routes):
        route = _find_route(routes, "rigid_box")
        assert _has_op(route, "lamination"), f"No lamination in: {_ops(route)}"
        _record("llm_box_has_lamination", True)

    def test_box_route_has_die_cutting(self, routes):
        route = _find_route(routes, "rigid_box")
        assert _has_op(route, "die_cutting"), f"No die_cutting in: {_ops(route)}"
        _record("llm_box_has_die_cutting", True)

    def test_box_route_ends_with_packing(self, routes):
        route = _find_route(routes, "rigid_box")
        ops = _ops(route)
        assert "shipper_packing" in ops[-2:], f"Packing not last: {ops}"
        _record("llm_box_packing_last", True)

    def test_large_run_uses_offset(self, routes):
        """quantity=1000 → must use offset_printing, not digital."""
        route = _find_route(routes, "rigid_box")
        assert _has_op(route, "offset_printing"), "Large run should use offset"
        assert not _has_op(route, "digital_printing"), "Large run must not use digital"
        _record("llm_box_offset_for_large_run", True)


class TestLLMCardDeckRoute:
    """Standalone card deck, small run — LLM should choose digital printing."""

    COMPONENTS = [
        {
            "id": "card_deck",
            "type": "card_deck",
            "name": "Test Cards",
            "card_count": 54,
            "card_size_mm": [63, 88],
            "gsm": 300,
            "print_colors": "4+4",
            "front_finish": "matte_lamination",
            "back_finish": "matte_lamination",
        }
    ]
    REQUIREMENTS = {
        "quantity": 200,
        "product_name": "Small Run Game",
        "client_name": "Test Client",
        "deadline_days": 14,
    }

    @pytest.fixture(scope="class")
    def routes(self):
        return _run_technologist(self.COMPONENTS, self.REQUIREMENTS)

    def test_card_route_generated(self, routes):
        assert len(routes) >= 1
        _record("llm_card_route_generated", True, {"routes_count": len(routes)})

    def test_card_has_card_cutting(self, routes):
        route = _find_route(routes, "card_deck")
        assert route is not None
        assert _has_op(route, "card_cutting"), f"No card_cutting in: {_ops(route)}"
        _record("llm_card_has_card_cutting", True)

    def test_small_run_uses_digital(self, routes):
        """quantity=200 → should use digital_printing."""
        route = _find_route(routes, "card_deck")
        has_digital = _has_op(route, "digital_printing")
        has_offset = _has_op(route, "offset_printing")
        assert has_digital or not has_offset, (
            f"Small run (200) should prefer digital. Ops: {_ops(route)}"
        )
        _record("llm_card_small_run_digital", has_digital, {"ops": _ops(route)})

    def test_card_route_ends_with_packing(self, routes):
        route = _find_route(routes, "card_deck")
        ops = _ops(route)
        assert "shipper_packing" in ops[-2:], f"Packing not last: {ops}"
        _record("llm_card_packing_last", True)


class TestLLMFullSetRoute:
    """Full board game: box + cards + rulebook — all three components routed."""

    COMPONENTS = [
        {
            "id": "rigid_box", "type": "rigid_box", "name": "Full Set Box",
            "size_mm": [300, 200, 60], "construction": "lid_and_base",
            "material": "bookbinding_board", "board_thickness_mm": 1.75,
            "lamination": "matte",
        },
        {
            "id": "card_deck", "type": "card_deck", "name": "Full Set Cards",
            "card_count": 90, "card_size_mm": [63, 88], "gsm": 300,
            "print_colors": "4+4", "front_finish": "matte_lamination",
            "back_finish": "matte_lamination",
        },
        {
            "id": "rulebook", "type": "rulebook_thin", "name": "Rulebook",
            "size_mm": [148, 210], "pages": 8, "binding": "saddle_stitch",
        },
    ]
    REQUIREMENTS = {
        "quantity": 500,
        "product_name": "Full Board Game",
        "client_name": "Test Client",
        "deadline_days": 21,
        "has_game_components": False,
        "has_additional_elements": False,
    }

    @pytest.fixture(scope="class")
    def routes(self):
        return _run_technologist(self.COMPONENTS, self.REQUIREMENTS)

    def test_all_components_routed(self, routes):
        comp_ids = {r.get("component_id") for r in routes}
        assert "rigid_box" in comp_ids, f"Missing rigid_box in {comp_ids}"
        assert "card_deck" in comp_ids, f"Missing card_deck in {comp_ids}"
        assert "rulebook" in comp_ids or "rulebook_thin" in comp_ids, f"Missing rulebook in {comp_ids}"
        _record("llm_fullset_all_routed", True, {"comp_ids": list(comp_ids)})

    def test_each_route_has_prepress(self, routes):
        for route in routes:
            ops = _ops(route)
            assert ops[0] == "prepress", f"{route.get('component_id')}: first op={ops[0]}"
        _record("llm_fullset_all_prepress_first", True)

    def test_each_route_ends_with_packing(self, routes):
        for route in routes:
            ops = _ops(route)
            assert "shipper_packing" in ops[-2:], f"{route.get('component_id')}: packing not last. ops={ops}"
        _record("llm_fullset_all_packing_last", True)


# ===========================================================================
# PART 2 — LLM-as-Judge Route Quality Evaluation
# ===========================================================================

JUDGE_MODEL = os.getenv("DEEPEVAL_JUDGE_MODEL", "gpt-4.1")

try:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

pytestmark_judge = pytest.mark.skipif(
    not DEEPEVAL_AVAILABLE, reason="deepeval not installed"
)


def _route_to_text(routes: list[dict]) -> str:
    """Serialize routes to readable text for the judge."""
    lines = []
    for r in routes:
        lines.append(f"Component: {r.get('component_id')}")
        for op in r.get("operations", []):
            params = op.get("parameters", {})
            param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "—"
            lines.append(f"  → {op.get('operation_id')} ({param_str})")
    return "\n".join(lines)


@pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")
class TestRouteJudge:
    """LLM-as-Judge evaluation of route quality (4 scenarios)."""

    def _judge_score(self, input_text: str, actual_output: str,
                     expected_output: str, criteria: str) -> tuple[float, bool]:
        metric = GEval(
            name="Route Quality",
            criteria=criteria,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=JUDGE_MODEL,
            threshold=0.6,
        )
        test_case = LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            expected_output=expected_output,
        )
        metric.measure(test_case)
        return metric.score, metric.score >= 0.6

    def test_judge_box_operation_order(self):
        """Judge: rigid_box route has correct logical operation sequence."""
        routes = _run_technologist(
            TestLLMRigidBoxRoute.COMPONENTS, TestLLMRigidBoxRoute.REQUIREMENTS
        )
        route_text = _route_to_text(routes)
        score, passed = self._judge_score(
            input_text="Generate a production route for a rigid box (300×200×60 mm, matte lamination, quantity 1000).",
            actual_output=route_text,
            expected_output=(
                "The route should follow this logical order: prepress → sheet cutting → "
                "offset printing (large run) → lamination → chipboard laminating → "
                "die cutting → blank stripping → box assembly → packing. "
                "Lamination must come before die cutting. Packing must be last."
            ),
            criteria=(
                "Evaluate whether the production route follows the correct logical sequence "
                "for a rigid box. Prepress must be first. Lamination must precede die cutting. "
                "Chipboard laminating must be present. Box assembly must appear before packing. "
                "Packing must be the last or second-to-last operation. "
                "Offset printing is appropriate for a run of 1000 units."
            ),
        )
        _record("judge_box_operation_order", passed, {"score": score})
        assert passed, f"Judge score {score:.2f} < 0.6 for box operation order"

    def test_judge_card_print_technology(self):
        """Judge: small-run card deck uses appropriate print technology."""
        routes = _run_technologist(
            TestLLMCardDeckRoute.COMPONENTS, TestLLMCardDeckRoute.REQUIREMENTS
        )
        route_text = _route_to_text(routes)
        score, passed = self._judge_score(
            input_text="Generate a route for a card deck (63×88 mm, 54 cards, quantity 200 — small run).",
            actual_output=route_text,
            expected_output=(
                "For a small run of 200 units, digital printing should be used instead of offset. "
                "The route must include card cutting with nickel dimensions. Packing is last."
            ),
            criteria=(
                "Evaluate whether the route correctly selects printing technology for the run size. "
                "For quantity < 500, digital printing is preferred over offset. "
                "Card cutting must be present with nickel_w and nickel_h parameters. "
                "The route should not use offset printing for 200 units."
            ),
        )
        _record("judge_card_print_technology", passed, {"score": score})
        assert passed, f"Judge score {score:.2f} < 0.6 for card print technology"

    def test_judge_fullset_component_independence(self):
        """Judge: each component in a full set has its own independent route."""
        routes = _run_technologist(
            TestLLMFullSetRoute.COMPONENTS, TestLLMFullSetRoute.REQUIREMENTS
        )
        route_text = _route_to_text(routes)
        score, passed = self._judge_score(
            input_text="Generate routes for a full board game set: rigid box + card deck + rulebook, quantity 500.",
            actual_output=route_text,
            expected_output=(
                "Three separate routes must be generated — one per component. "
                "Each route starts with prepress and ends with packing. "
                "The box route includes die cutting and box assembly. "
                "The card route includes card cutting. "
                "The rulebook route includes printing and folding/cutting steps."
            ),
            criteria=(
                "Evaluate whether all three components (rigid_box, card_deck, rulebook) have "
                "independent, complete routes. Each route must start with prepress and end with "
                "packing. Routes should not mix operations from different component types. "
                "Offset printing is appropriate for 500 units."
            ),
        )
        _record("judge_fullset_independence", passed, {"score": score})
        assert passed, f"Judge score {score:.2f} < 0.6 for full set independence"

    def test_judge_knife_params_used(self):
        """Judge: die_cutting and card_cutting use pre-calculated knife dimensions."""
        routes = _run_technologist(
            TestLLMRigidBoxRoute.COMPONENTS, TestLLMRigidBoxRoute.REQUIREMENTS
        )
        route_text = _route_to_text(routes)
        score, passed = self._judge_score(
            input_text="Generate a rigid box route. The pre-calculated knife dimensions are available.",
            actual_output=route_text,
            expected_output=(
                "The die_cutting operation must include nickel_w and nickel_h parameters "
                "with non-zero numeric values derived from the knife calculator. "
                "The sheet_format_cutting must also include knife dimensions."
            ),
            criteria=(
                "Evaluate whether the route correctly uses knife dimensions in the relevant operations. "
                "die_cutting must have nickel_w and nickel_h as non-zero numbers. "
                "sheet_format_cutting should include knife_w and knife_h parameters. "
                "Missing or zero knife dimensions indicate the LLM ignored the pre-calculated values."
            ),
        )
        _record("judge_knife_params_used", passed, {"score": score})
        assert passed, f"Judge score {score:.2f} < 0.6 for knife params"
