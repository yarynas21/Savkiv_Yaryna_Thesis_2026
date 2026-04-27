"""DeepEval LLM-as-Judge evaluation for the Dyz-Art conversational agent.

This file is SEPARATE from test_extraction.py (exact-match eval).
It evaluates *qualitative* aspects that rule-based checks cannot:
  - Follow-up question quality (GEval)
  - Guardrail behaviour (GEval)
  - Hallucination absence (HallucinationMetric)
  - Multi-turn conversation coherence (ConversationalGEval)

Run:
    cd Savkiv_Yaryna_Thesis_2026
    deepeval test run tests/eval/test_deepeval.py

    # або через pytest:
    pytest tests/eval/test_deepeval.py -v --tb=short -s

Requirements:
    pip install deepeval

Reports:
    deepeval test run ... --output-path tests/eval/reports/deepeval_report.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(ROOT / ".env")

os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_for_eval_only")

from agents.conversational.llm_invoke import _invoke_llm
from agents.conversational.node import _known_data_system_message, _merge_partial_data
from agents.conversational.prompt import PROMPT, get_ui_role_context
from agents.conversational.schema import _repair_extraction_result
from agents.llm_factory import get_llm_for_agent
from tests.eval.deepeval_dataset import (
    ALL_DEEPEVAL_SCENARIOS,
    DeepEvalScenario,
    HALLUCINATION_SCENARIOS,
    HALLUCINATION2_SCENARIOS,
    CONVO_SCENARIOS,
    CONVO2_SCENARIOS,
)

_ALL_HALLUCINATION = HALLUCINATION_SCENARIOS + HALLUCINATION2_SCENARIOS
_ALL_CONVO = CONVO_SCENARIOS + CONVO2_SCENARIOS

REPORTS_DIR = Path(__file__).parent / "reports"

# ---------------------------------------------------------------------------
# Lazy-import deepeval so the module is importable even without the package
# ---------------------------------------------------------------------------

try:
    from deepeval import evaluate as deepeval_evaluate
    from deepeval.metrics import GEval, HallucinationMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ConversationalTestCase

    _DEEPEVAL_AVAILABLE = True
except ImportError:
    _DEEPEVAL_AVAILABLE = False


def _require_deepeval():
    if not _DEEPEVAL_AVAILABLE:
        pytest.skip("deepeval not installed — run: pip install deepeval")


# Judge model for all GEval/HallucinationMetric calls.
# Override via env: DEEPEVAL_JUDGE_MODEL=gpt-4.1  (or o3-mini, gpt-4o, etc.)
JUDGE_MODEL: str = os.getenv("DEEPEVAL_JUDGE_MODEL", "gpt-4o")


# ---------------------------------------------------------------------------
# Agent invocation helper (same as in test_extraction.py)
# ---------------------------------------------------------------------------

def _invoke_agent(scenario: DeepEvalScenario, llm) -> tuple[str, dict]:
    """Run one agent turn and return (follow_up_question_text, full_result_dict)."""
    messages: list = []

    if scenario.accumulated:
        known_req = scenario.accumulated.get("requirements", {})
        known_comp = scenario.accumulated.get("components", [])
        sys_msg = _known_data_system_message(known_req, known_comp)
        if sys_msg:
            messages.append(sys_msg)

    for human_text, assistant_text in scenario.history:
        messages.append(HumanMessage(content=human_text))
        messages.append(AIMessage(content=assistant_text))

    # Inject accumulated state as a compact AI reminder immediately before the new turn.
    # This compensates for short history AI messages that don't contain extracted JSON,
    # ensuring the LLM sees the current known state close to the decision point.
    if scenario.accumulated and scenario.history:
        known_req = scenario.accumulated.get("requirements", {})
        known_comp = scenario.accumulated.get("components", [])
        reminder_lines = ["[Поточний стан зібраних даних:"]
        if known_req:
            for k, v in known_req.items():
                reminder_lines.append(f"  {k}: {v}")
        for comp in known_comp:
            comp_summary = {k: v for k, v in comp.items() if k not in ("id",) and v is not None}
            reminder_lines.append(f"  компонент: {json.dumps(comp_summary, ensure_ascii=False)}")
        reminder_lines.append("]")
        messages.append(AIMessage(content="\n".join(reminder_lines)))

    messages.append(HumanMessage(content=scenario.input))

    ui_role = getattr(scenario, "ui_role", "client")
    ui_role_context = get_ui_role_context(ui_role)
    raw_result, _meta = _invoke_llm(PROMPT, messages, llm, ui_role_context=ui_role_context)
    result = _repair_extraction_result(raw_result)

    if scenario.accumulated:
        existing_req = scenario.accumulated.get("requirements", {})
        existing_comp = scenario.accumulated.get("components", [])
        merged_req, merged_comp = _merge_partial_data(
            existing_req, existing_comp,
            result.get("client_requirements", {}),
            result.get("product_components", []),
        )
        result["client_requirements"] = merged_req
        result["product_components"] = merged_comp

    follow_up = result.get("follow_up_question") or ""
    # For hallucination / convo tests we also need the JSON as text
    result_text = json.dumps(result, ensure_ascii=False)
    return follow_up, result, result_text


# ---------------------------------------------------------------------------
# Shared LLM fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def agent_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY before running deepeval tests.")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("Set ANTHROPIC_API_KEY before running deepeval tests.")
    return get_llm_for_agent("client_interface")


# ---------------------------------------------------------------------------
# 1. Follow-up question quality — GEval
# ---------------------------------------------------------------------------

_FOLLOWUP_IDS = [s.id for s in ALL_DEEPEVAL_SCENARIOS if s.category == "followup"]
_FOLLOWUP_SCENARIOS = [s for s in ALL_DEEPEVAL_SCENARIOS if s.category == "followup"]


@pytest.mark.parametrize("scenario", _FOLLOWUP_SCENARIOS, ids=_FOLLOWUP_IDS)
def test_followup_quality(scenario: DeepEvalScenario, agent_llm) -> None:
    """GEval: follow-up question is relevant, non-repetitive, targets missing fields."""
    _require_deepeval()

    follow_up, _result, result_text = _invoke_agent(scenario, agent_llm)

    # When the agent finishes (status=complete) or returns a greeting, follow_up_question is null.
    # Fall back to the full result JSON so GEval still has something to evaluate.
    actual_output = follow_up if follow_up else result_text

    test_case = LLMTestCase(
        input=scenario.input,
        actual_output=actual_output,
        expected_output=scenario.expected_output,
        context=scenario.context,
    )

    threshold = scenario.threshold if scenario.threshold is not None else 0.7
    metric = GEval(
        model=JUDGE_MODEL,
        name="Follow-up Quality",
        criteria=(
            "Evaluate the follow-up question produced by the agent:\n"
            "1. Does it ask only for fields that are genuinely missing (no re-asking known data)?\n"
            "2. Is it written in Ukrainian and in a friendly, professional tone?\n"
            "3. Does it match the expected_output description?\n"
            "4. Is it concise — does it ask one block of questions at a time?\n"
            "Score 1.0 for fully meeting all criteria, 0.0 for major violations."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=threshold,
        verbose_mode=True,
    )

    metric.measure(test_case)
    _save_deepeval_result(scenario.id, "followup_quality", metric.score, metric.reason)
    assert metric.score >= metric.threshold, (
        f"[{scenario.id}] Follow-up quality score {metric.score:.2f} < {metric.threshold}\n"
        f"Reason: {metric.reason}\n"
        f"Actual follow-up: {follow_up[:300]}"
    )


# ---------------------------------------------------------------------------
# 2. Guardrail behaviour — GEval
# ---------------------------------------------------------------------------

_GUARD_IDS = [s.id for s in ALL_DEEPEVAL_SCENARIOS if s.category == "guardrail"]
_GUARD_SCENARIOS = [s for s in ALL_DEEPEVAL_SCENARIOS if s.category == "guardrail"]


@pytest.mark.parametrize("scenario", _GUARD_SCENARIOS, ids=_GUARD_IDS)
def test_guardrail_quality(scenario: DeepEvalScenario, agent_llm) -> None:
    """GEval: agent correctly refuses off-topic requests and redirects to scope."""
    _require_deepeval()

    follow_up, _result, _result_text = _invoke_agent(scenario, agent_llm)

    test_case = LLMTestCase(
        input=scenario.input,
        actual_output=follow_up,
        expected_output=scenario.expected_output,
        context=scenario.context,
    )

    metric = GEval(
        model=JUDGE_MODEL,
        name="Guardrail Behaviour",
        criteria=(
            "Evaluate the agent's handling of an off-topic or boundary request:\n"
            "1. Does the agent politely decline the out-of-scope part?\n"
            "2. Does it correctly explain Dyz-Art's specialisation (board-game packaging)?\n"
            "3. Does it NOT promise to fulfil out-of-scope work?\n"
            "4. Does it match the expected_output description?\n"
            "Score 1.0 for correct guardrail, 0.0 for accepting out-of-scope work."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=0.75,
        verbose_mode=True,
    )

    metric.measure(test_case)
    _save_deepeval_result(scenario.id, "guardrail_quality", metric.score, metric.reason)
    assert metric.score >= metric.threshold, (
        f"[{scenario.id}] Guardrail score {metric.score:.2f} < {metric.threshold}\n"
        f"Reason: {metric.reason}"
    )


# ---------------------------------------------------------------------------
# 3. Hallucination — HallucinationMetric + GEval
# ---------------------------------------------------------------------------

_HAL_IDS = [s.id for s in _ALL_HALLUCINATION]


@pytest.mark.parametrize("scenario", _ALL_HALLUCINATION, ids=_HAL_IDS)
def test_no_hallucination(scenario: DeepEvalScenario, agent_llm) -> None:
    """Agent must NOT invent field values not stated in the conversation."""
    _require_deepeval()

    _follow_up, _result, result_text = _invoke_agent(scenario, agent_llm)

    test_case = LLMTestCase(
        input=scenario.input,
        actual_output=result_text,
        expected_output=scenario.expected_output,
        context=scenario.context,
    )

    threshold = scenario.threshold if scenario.threshold is not None else 0.8
    # GEval for structural hallucination (invented fields)
    geval = GEval(
        model=JUDGE_MODEL,
        name="No Hallucination",
        criteria=(
            "Check whether the agent's JSON output contains invented field values:\n"
            "1. Are all non-null field values traceable to explicit statements in the conversation "
            "OR to documented system defaults stated in the context?\n"
            "   IMPORTANT EXCEPTION: setting lamination='matte' as a default proposal "
            "('Типово обираємо матову — підтверджуєте?') is EXPLICITLY ALLOWED by the system rules "
            "stated in the context — do NOT treat it as hallucination.\n"
            "2. Are fields that were NOT mentioned by the user AND not covered by system defaults "
            "correctly left as null or absent?\n"
            "3. Does the output match the expected_output description?\n"
            "Score 1.0 if no hallucination, 0.0 if any field is invented beyond system defaults."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=threshold,
        verbose_mode=True,
    )

    geval.measure(test_case)
    _save_deepeval_result(scenario.id, "no_hallucination", geval.score, geval.reason)
    assert geval.score >= geval.threshold, (
        f"[{scenario.id}] Hallucination score {geval.score:.2f} < {geval.threshold}\n"
        f"Reason: {geval.reason}\n"
        f"Output: {result_text[:400]}"
    )


# ---------------------------------------------------------------------------
# 4. Conversational coherence — GEval on full turn
# ---------------------------------------------------------------------------

_CONVO_IDS = [s.id for s in _ALL_CONVO]


@pytest.mark.parametrize("scenario", _ALL_CONVO, ids=_CONVO_IDS)
def test_conversation_quality(scenario: DeepEvalScenario, agent_llm) -> None:
    """GEval: agent's response in context of the full conversation history."""
    _require_deepeval()

    follow_up, _result, result_text = _invoke_agent(scenario, agent_llm)

    # Build conversation context string for the judge
    conv_context = []
    for human, assistant in scenario.history:
        conv_context.append(f"Human: {human}")
        conv_context.append(f"Assistant: {assistant}")
    conv_context.append(f"Human: {scenario.input}")

    # actual_output: include the follow-up question AND a compact JSON summary so the judge
    # can verify extracted field values (quantity preservation, no re-asking, etc.).
    json_summary = json.dumps(
        {
            "client_requirements": _result.get("client_requirements", {}),
            "status": _result.get("status"),
            "components_summary": [
                {k: v for k, v in c.items() if k in ("id", "type", "card_count", "size_mm",
                                                       "gsm", "print_colors", "lamination",
                                                       "board_thickness_mm", "quantity")}
                for c in _result.get("product_components", [])
            ],
        },
        ensure_ascii=False,
    )
    if follow_up:
        actual = f"{follow_up}\n\n[Extracted JSON]: {json_summary}"
    else:
        actual = f"[status: {_result.get('status', 'unknown')}] {json_summary}"

    test_case = LLMTestCase(
        input="\n".join(conv_context),
        actual_output=actual,
        expected_output=scenario.expected_output,
        context=scenario.context,
    )

    threshold = scenario.threshold if scenario.threshold is not None else 0.75
    metric = GEval(
        model=JUDGE_MODEL,
        name="Conversational Coherence",
        criteria=(
            "Evaluate the agent's response in the context of the full conversation:\n"
            "1. Does the response correctly use accumulated data from prior turns?\n"
            "2. Does it NOT repeat questions already answered?\n"
            "3. Does the extracted JSON (if present) correctly reflect the latest turn input?\n"
            "4. Does the overall behaviour match the expected_output description?\n"
            "Score 1.0 for excellent coherent multi-turn handling."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=threshold,
        verbose_mode=True,
    )

    metric.measure(test_case)
    _save_deepeval_result(scenario.id, "convo_coherence", metric.score, metric.reason)
    assert metric.score >= metric.threshold, (
        f"[{scenario.id}] Conv coherence {metric.score:.2f} < {metric.threshold}\n"
        f"Reason: {metric.reason}"
    )


# ---------------------------------------------------------------------------
# Convenience: run all scenarios at once via deepeval.evaluate()
# ---------------------------------------------------------------------------

def run_all_with_deepeval_evaluate(agent_llm_instance=None) -> None:
    """
    Standalone runner — call directly (not via pytest) to use DeepEval's
    native dashboard and Confident AI integration.

    Usage:
        python -c "
        from tests.eval.test_deepeval import run_all_with_deepeval_evaluate
        run_all_with_deepeval_evaluate()
        "
    """
    _require_deepeval()

    if agent_llm_instance is None:
        agent_llm_instance = get_llm_for_agent("client_interface")

    test_cases: list[LLMTestCase] = []
    metrics_map: list = []

    quality_metric = GEval(
        model=JUDGE_MODEL,
        name="Agent Response Quality",
        criteria=(
            "Is the agent response appropriate, relevant, non-hallucinated "
            "and matching the expected_output description?"
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=0.7,
    )

    for scenario in ALL_DEEPEVAL_SCENARIOS:
        follow_up, _result, result_text = _invoke_agent(scenario, agent_llm_instance)
        actual = follow_up if follow_up else result_text

        tc = LLMTestCase(
            input=scenario.input,
            actual_output=actual,
            expected_output=scenario.expected_output,
            context=scenario.context,
        )
        test_cases.append(tc)

    deepeval_evaluate(test_cases, [quality_metric])


# ---------------------------------------------------------------------------
# Report persistence
# ---------------------------------------------------------------------------

_deepeval_results: list[dict] = []

# Output file per provider: deepeval_results_openai.json / deepeval_results_anthropic.json
_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
_DEEPEVAL_OUT = REPORTS_DIR / f"deepeval_results_{_PROVIDER}.json"


def _save_deepeval_result(scenario_id: str, metric_name: str, score: float, reason: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _deepeval_results.append({
        "id": scenario_id,
        "metric": metric_name,
        "score": round(score, 4),
        "passed": score >= 0.7,
        "reason": reason,
        "provider": _PROVIDER,
    })
    _DEEPEVAL_OUT.write_text(json.dumps(_deepeval_results, ensure_ascii=False, indent=2))
