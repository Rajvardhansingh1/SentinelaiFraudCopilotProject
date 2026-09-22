"""Phase 8: CI/CD. Pure policy-evaluation tests (proxy/ci.py) plus the CLI
entrypoint (scripts/sentinel_ci.py) with HTTP mocked out."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.ci import CIPolicy, evaluate, format_human_summary, matching_results
from proxy.engine.registry import all_tests
from proxy.main import app


def _r(test_id, status, severity="high", category="prompt_injection", detail="d"):
    return {"test_id": test_id, "status": status, "severity": severity, "category": category, "detail": detail}


# --- proxy/ci.py pure logic ---


def test_default_policy_fails_on_any_fail_result():
    policy = CIPolicy()
    verdict = evaluate([_r("a", "PASS"), _r("b", "FAIL")], policy)
    assert verdict["should_fail"] is True
    assert [m["test_id"] for m in verdict["matching_results"]] == ["b"]


def test_default_policy_passes_when_nothing_fails():
    policy = CIPolicy()
    verdict = evaluate([_r("a", "PASS"), _r("b", "INCONCLUSIVE"), _r("c", "ERROR")], policy)
    assert verdict["should_fail"] is False


def test_max_failures_threshold_is_explicit_and_configurable():
    policy = CIPolicy(max_failures=2)
    verdict = evaluate([_r("a", "FAIL"), _r("b", "FAIL")], policy)
    assert verdict["should_fail"] is False  # exactly at threshold, not over

    verdict2 = evaluate([_r("a", "FAIL"), _r("b", "FAIL"), _r("c", "FAIL")], policy)
    assert verdict2["should_fail"] is True


def test_fail_on_severity_narrows_which_statuses_count():
    policy = CIPolicy(fail_on_severities=frozenset({"critical"}))
    verdict = evaluate([_r("a", "FAIL", severity="medium"), _r("b", "FAIL", severity="critical")], policy)
    assert [m["test_id"] for m in verdict["matching_results"]] == ["b"]
    assert verdict["should_fail"] is True


def test_fail_on_status_can_include_error_and_inconclusive():
    policy = CIPolicy(fail_on_statuses=frozenset({"FAIL", "ERROR"}))
    verdict = evaluate([_r("a", "ERROR"), _r("b", "INCONCLUSIVE")], policy)
    assert [m["test_id"] for m in verdict["matching_results"]] == ["a"]


def test_matching_results_is_independently_usable():
    policy = CIPolicy(fail_on_statuses=frozenset({"FAIL"}))
    matches = matching_results([_r("a", "PASS"), _r("b", "FAIL")], policy)
    assert [m["test_id"] for m in matches] == ["b"]


def test_regression_count_factors_into_the_verdict_only_when_report_given():
    policy = CIPolicy(max_regressions=0)
    no_report_verdict = evaluate([_r("a", "PASS")], policy, regression_report=None)
    assert no_report_verdict["should_fail"] is False
    assert no_report_verdict["regression_count"] == 0

    report = {"regressions": [{"test_id": "a"}]}
    with_report_verdict = evaluate([_r("a", "PASS")], policy, regression_report=report)
    assert with_report_verdict["should_fail"] is True
    assert with_report_verdict["regression_count"] == 1


def test_max_regressions_threshold_is_configurable():
    policy = CIPolicy(max_regressions=2)
    report = {"regressions": [{"test_id": "a"}, {"test_id": "b"}]}
    verdict = evaluate([], policy, regression_report=report)
    assert verdict["should_fail"] is False  # exactly at threshold


def test_human_summary_reports_pass_and_fail_distinctly():
    policy = CIPolicy()
    pass_summary = format_human_summary([_r("a", "PASS")], evaluate([_r("a", "PASS")], policy), "http://x")
    fail_summary = format_human_summary([_r("a", "FAIL")], evaluate([_r("a", "FAIL")], policy), "http://x")
    assert "Result: PASS" in pass_summary
    assert "Result: FAIL" in fail_summary
    assert "Result: PASS" not in fail_summary


def test_human_summary_lists_matching_test_ids_and_target():
    policy = CIPolicy()
    verdict = evaluate([_r("bad-test", "FAIL")], policy)
    summary = format_human_summary([_r("bad-test", "FAIL")], verdict, "http://ci-target:8000")
    assert "bad-test" in summary
    assert "http://ci-target:8000" in summary


# --- CLI entrypoint (HTTP mocked) ---


def test_cli_exits_zero_when_all_pass(monkeypatch, tmp_path):
    from scripts import sentinel_ci

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [_r("a", "PASS")]}

    monkeypatch.setattr(sentinel_ci.requests, "post", lambda *a, **kw: FakeResp())

    exit_code = sentinel_ci.main(["--target", "http://fake"])
    assert exit_code == 0


def test_cli_exits_nonzero_when_a_test_fails(monkeypatch):
    from scripts import sentinel_ci

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [_r("a", "FAIL")]}

    monkeypatch.setattr(sentinel_ci.requests, "post", lambda *a, **kw: FakeResp())

    exit_code = sentinel_ci.main(["--target", "http://fake"])
    assert exit_code == 1


def test_cli_writes_json_and_markdown_outputs(monkeypatch, tmp_path):
    from scripts import sentinel_ci

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [_r("a", "PASS")]}

    monkeypatch.setattr(sentinel_ci.requests, "post", lambda *a, **kw: FakeResp())

    json_out = tmp_path / "results.json"
    md_out = tmp_path / "summary.md"
    sentinel_ci.main(["--target", "http://fake", "--json-out", str(json_out), "--md-out", str(md_out)])

    assert json_out.exists()
    assert md_out.exists()
    import json as jsonlib

    data = jsonlib.loads(json_out.read_text())
    assert data["results"][0]["test_id"] == "a"
    assert "Result: PASS" in md_out.read_text()


def test_cli_respects_fail_on_severity_flag(monkeypatch):
    from scripts import sentinel_ci

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [_r("a", "FAIL", severity="low")]}

    monkeypatch.setattr(sentinel_ci.requests, "post", lambda *a, **kw: FakeResp())

    # low severity FAIL is excluded when only critical/high count.
    exit_code = sentinel_ci.main(["--target", "http://fake", "--fail-on-severity", "critical,high"])
    assert exit_code == 0


def test_cli_passes_category_filter_as_query_param(monkeypatch):
    from scripts import sentinel_ci

    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    def fake_post(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResp()

    monkeypatch.setattr(sentinel_ci.requests, "post", fake_post)

    sentinel_ci.main(["--target", "http://fake", "--category", "jailbreak,prompt_injection"])
    assert captured["params"] == {"category": "jailbreak,prompt_injection"}


# --- endpoint-level test-suite selection (D-047) ---


def test_security_tests_run_endpoint_filters_by_category():
    client = TestClient(app)
    resp = client.post("/v1/security-tests/run", params={"category": "jailbreak"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 0
    assert all(row["category"] == "jailbreak" for row in body)


def test_security_tests_run_endpoint_accepts_multiple_categories():
    client = TestClient(app)
    resp = client.post("/v1/security-tests/run", params={"category": "jailbreak,unsafe_output_behavior"})
    body = resp.json()
    categories = {row["category"] for row in body}
    assert categories == {"jailbreak", "unsafe_output_behavior"}


def test_security_tests_run_endpoint_runs_everything_without_category():
    client = TestClient(app)
    resp = client.post("/v1/security-tests/run")
    assert len(resp.json()) == len(all_tests())


def test_findings_sync_endpoint_also_respects_category_filter():
    client = TestClient(app)
    resp = client.post("/v1/findings/sync", params={"category": "jailbreak"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert all(r["category"] == "jailbreak" for r in results)


def test_cli_skips_regression_check_gracefully_when_no_baseline(monkeypatch, capsys):
    from scripts import sentinel_ci

    class FakePostResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [_r("a", "PASS")]}

    class FakeGetResp:
        status_code = 404
        text = "not found"

        def json(self):
            return {"detail": {"code": "baseline_not_found", "message": "No baseline exists yet."}}

    monkeypatch.setattr(sentinel_ci.requests, "post", lambda *a, **kw: FakePostResp())
    monkeypatch.setattr(sentinel_ci.requests, "get", lambda *a, **kw: FakeGetResp())

    exit_code = sentinel_ci.main(["--target", "http://fake", "--check-regression"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Regression check skipped" in captured.err
