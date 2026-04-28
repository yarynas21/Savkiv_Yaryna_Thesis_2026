import json
import os
from pathlib import Path


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    try:
        from tests.eval.test_extraction import _results, _save_json_report, _make_charts, _rich_report
    except Exception:
        pass
    else:
        if _results:
            _save_json_report()
            _make_charts()
            _rich_report()

    _save_routes_llm_report()


def _save_routes_llm_report() -> None:
    try:
        from tests.eval import test_routes_llm as mod
    except Exception:
        return
    results = getattr(mod, "_results", None)
    if not results:
        return
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    out = report_dir / f"route_llm_results_{provider}.json"
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    summary = {
        "provider": provider,
        "model": (
            os.getenv("OPENAI_MODEL", "gpt-4o")
            if provider == "openai"
            else os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        ),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(passed / total * 100, 1) if total else 0,
        "results": results,
    }
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[route_llm_results:{provider}] {passed}/{total} passed → {out}")
