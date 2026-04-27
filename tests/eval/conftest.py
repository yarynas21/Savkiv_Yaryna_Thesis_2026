def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    from tests.eval.test_extraction import _results, _save_json_report, _make_charts, _rich_report
    if not _results:
        return
    _save_json_report()
    _make_charts()
    _rich_report()
