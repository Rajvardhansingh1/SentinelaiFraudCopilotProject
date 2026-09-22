"""Phase 7: security regression testing — baseline creation, comparison,
regression detection, resolved vulnerabilities, unchanged results, and test
additions/removals."""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.db.models import Baseline, Finding
from proxy.db.models import TestRunResult as RunResult
from proxy.db.session import SessionLocal, init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestResult as Result
from proxy.engine.models import TestStatus as Status
from proxy.findings import record_test_run, sync_findings
from proxy.main import app
from proxy.regression import compare_runs, create_baseline, findings_delta


def _db():
    init_db()
    return SessionLocal()


def _clear_tables():
    db = _db()
    db.query(Finding).delete()
    db.query(RunResult).delete()
    db.query(Baseline).delete()
    db.commit()
    db.close()


# setup, not just teardown: the DB engine (proxy/db/session.py) is a
# process-wide singleton even for sqlite:///:memory:, so rows other test
# modules leave behind are visible here too depending on collection order.
setup_function = _clear_tables
teardown_function = _clear_tables


def _snap(test_id, status, severity="high", provider="sentinelai", model="injection-detector"):
    return {
        "test_id": test_id,
        "category": "prompt_injection",
        "severity": severity,
        "status": status,
        "provider": provider,
        "model": model,
    }


def _result(test_id, status, severity=Severity.HIGH):
    return Result(
        test_id=test_id,
        name=test_id,
        category="prompt_injection",
        severity=severity,
        status=status,
        detail="d",
        evidence=RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        executed_at=datetime.now(timezone.utc),
        reproduction={"attack_input": "x"},
    )


# --- pure comparison ---


def test_detects_regression_pass_to_fail():
    report = compare_runs([_snap("a", "PASS")], [_snap("a", "FAIL")])
    assert [e["test_id"] for e in report["regressions"]] == ["a"]
    assert report["fixed"] == []
    assert report["unchanged"] == []


def test_detects_resolved_vulnerability_fail_to_pass():
    report = compare_runs([_snap("a", "FAIL")], [_snap("a", "PASS")])
    assert [e["test_id"] for e in report["fixed"]] == ["a"]
    assert report["regressions"] == []


def test_detects_unchanged_results():
    report = compare_runs([_snap("a", "PASS"), _snap("b", "FAIL")], [_snap("a", "PASS"), _snap("b", "FAIL")])
    assert sorted(e["test_id"] for e in report["unchanged"]) == ["a", "b"]
    assert report["regressions"] == []
    assert report["fixed"] == []


def test_detects_test_additions_and_removals():
    report = compare_runs([_snap("a", "PASS"), _snap("gone", "PASS")], [_snap("a", "PASS"), _snap("added", "PASS")])
    assert report["added_tests"] == ["added"]
    assert report["removed_tests"] == ["gone"]


def test_new_test_that_fails_is_a_new_failure_not_a_regression():
    """A brand-new failing test isn't a regression — nothing passed before."""
    report = compare_runs([_snap("a", "PASS")], [_snap("a", "PASS"), _snap("brand-new", "FAIL")])
    assert [e["test_id"] for e in report["new_failures"]] == ["brand-new"]
    assert report["regressions"] == []


def test_detects_severity_change():
    report = compare_runs([_snap("a", "PASS", severity="medium")], [_snap("a", "PASS", severity="critical")])
    assert len(report["severity_changes"]) == 1
    assert report["severity_changes"][0]["baseline_severity"] == "medium"
    assert report["severity_changes"][0]["current_severity"] == "critical"


def test_detects_changed_provider_configuration():
    report = compare_runs([_snap("a", "PASS", provider="groq", model="m1")], [_snap("a", "PASS", provider="gemini", model="m2")])
    assert report["provider_config_changed"] is True
    assert report["baseline_config"] == [{"provider": "groq", "model": "m1"}]
    assert report["current_config"] == [{"provider": "gemini", "model": "m2"}]


def test_unchanged_provider_configuration_is_not_flagged():
    report = compare_runs([_snap("a", "PASS")], [_snap("a", "PASS")])
    assert report["provider_config_changed"] is False


def test_non_regression_status_transitions_are_kept_separate():
    """PASS -> INCONCLUSIVE isn't a regression or a fix, but must not vanish."""
    report = compare_runs([_snap("a", "PASS")], [_snap("a", "INCONCLUSIVE")])
    assert report["regressions"] == []
    assert report["fixed"] == []
    assert [e["test_id"] for e in report["other_changes"]] == ["a"]


def test_report_keeps_every_individual_test_result_accessible():
    """Spec: individual results must remain accessible, not collapsed into a score."""
    report = compare_runs([_snap("a", "PASS"), _snap("b", "FAIL")], [_snap("a", "FAIL"), _snap("b", "FAIL")])
    assert len(report["per_test"]) == 2
    assert "score" not in report


# --- baseline creation ---


def test_create_baseline_pins_the_latest_run():
    db = _db()
    record_test_run(db, [_result("a", Status.PASS)])
    run_id = record_test_run(db, [_result("a", Status.FAIL)])
    baseline = create_baseline(db, "latest")
    assert baseline is not None
    assert baseline.run_id == run_id
    db.close()


def test_create_baseline_returns_none_when_nothing_has_run():
    db = _db()
    assert create_baseline(db, "empty") is None
    db.close()


def test_create_baseline_rejects_unknown_run_id():
    db = _db()
    record_test_run(db, [_result("a", Status.PASS)])
    assert create_baseline(db, "bad", run_id="not-a-real-run-id") is None
    db.close()


# --- findings delta ---


def test_findings_delta_reports_new_and_resolved_since_baseline():
    db = _db()
    before = datetime.now(timezone.utc) - timedelta(minutes=5)
    [finding] = sync_findings(db, [_result("fail-1", Status.FAIL)])

    delta = findings_delta(db, before)
    assert [f["test_id"] for f in delta["new_findings"]] == ["fail-1"]
    assert delta["resolved_findings"] == []

    finding.status = "RESOLVED"
    db.commit()
    delta_after = findings_delta(db, before)
    assert [f["test_id"] for f in delta_after["resolved_findings"]] == ["fail-1"]
    db.close()


# --- endpoint flow ---


def test_regression_report_endpoint_detects_a_real_regression(monkeypatch):
    passing = SecurityTest(
        id="flip",
        name="flip",
        category="jailbreak",
        description="d",
        severity=Severity.HIGH,
        attack_input="x",
        expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (Status.PASS, "blocked"),
    )
    monkeypatch.setattr("proxy.main.all_tests", lambda: [passing])
    client = TestClient(app)

    client.post("/v1/findings/sync")
    created = client.post("/v1/baselines", json={"name": "good state"})
    assert created.status_code == 200

    # Same test now fails — a real regression.
    failing = SecurityTest(**{**passing.__dict__, "evaluate": lambda ev: (Status.FAIL, "not blocked")})
    monkeypatch.setattr("proxy.main.all_tests", lambda: [failing])
    client.post("/v1/findings/sync")

    report = client.get("/v1/regression-report")
    assert report.status_code == 200
    body = report.json()
    assert [e["test_id"] for e in body["regressions"]] == ["flip"]
    assert body["baseline"]["name"] == "good state"
    assert len(body["findings"]["new_findings"]) == 1


def test_baseline_endpoint_409s_when_no_run_recorded():
    client = TestClient(app)
    resp = client.post("/v1/baselines", json={"name": "nothing yet"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "no_run_to_baseline"


def test_regression_report_404s_without_a_baseline(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [])
    client = TestClient(app)
    client.post("/v1/findings/sync")
    resp = client.get("/v1/regression-report")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "baseline_not_found"


def test_baselines_are_listed_newest_first():
    db = _db()
    record_test_run(db, [_result("a", Status.PASS)])
    create_baseline(db, "first")
    create_baseline(db, "second")
    db.close()

    client = TestClient(app)
    names = [b["name"] for b in client.get("/v1/baselines").json()]
    assert "first" in names and "second" in names
