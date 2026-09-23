import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.dashboard import build_dashboard_summary
from proxy.db.models import Finding
from proxy.db.models import TestRunResult as RunResult
from proxy.db.session import SessionLocal, init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestResult as Result
from proxy.engine.models import TestStatus as Status
from proxy.findings import record_test_run, sync_findings
from proxy.main import app
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


def _db():
    init_db()
    return SessionLocal()


def _clear_tables():
    db = _db()
    db.query(Finding).delete()
    db.query(RunResult).delete()
    db.commit()
    db.close()


# setup, not just teardown: the DB engine (proxy/db/session.py) is a
# process-wide singleton even for sqlite:///:memory:, so rows other test
# modules leave behind are visible here too depending on collection order.
setup_function = _clear_tables
teardown_function = _clear_tables


def _result(test_id, status, category="prompt_injection", severity=Severity.HIGH):
    return Result(
        test_id=test_id,
        name=test_id,
        category=category,
        severity=severity,
        status=status,
        detail="d",
        evidence=RawExecution(raw_input="x", raw_output={"flagged": status == Status.PASS}, provider="sentinelai", model="injection-detector"),
        executed_at=datetime.now(timezone.utc),
        reproduction={"attack_input": "x"},
    )


def test_dashboard_is_all_zero_before_anything_has_run():
    db = _db()
    summary = build_dashboard_summary(db)
    db.close()
    assert summary["total_tests"] == 0
    assert summary["last_run_at"] is None
    assert summary["open_findings"] == 0
    assert summary["severity_distribution"] == {}
    assert summary["recent_activity"] == []
    assert summary["affected_models"] == []


def test_dashboard_counts_reflect_the_most_recent_run_only():
    db = _db()
    record_test_run(db, [_result("a", Status.PASS), _result("b", Status.FAIL), _result("c", Status.ERROR)])
    record_test_run(db, [_result("a", Status.PASS)])  # a second, smaller run
    summary = build_dashboard_summary(db)
    db.close()
    # Only the latest run's 1 result counts toward totals, not the cumulative 4.
    assert summary["total_tests"] == 1
    assert summary["passed"] == 1
    assert summary["failed"] == 0


def test_dashboard_open_findings_and_severity_distribution():
    db = _db()
    results = [_result("fail-crit", Status.FAIL, severity=Severity.CRITICAL), _result("fail-med", Status.FAIL, severity=Severity.MEDIUM)]
    sync_findings(db, results)
    summary = build_dashboard_summary(db)
    db.close()
    assert summary["open_findings"] == 2
    assert summary["severity_distribution"] == {"critical": 1, "medium": 1}


def test_dashboard_resolved_findings_excluded_from_severity_distribution():
    db = _db()
    [finding] = sync_findings(db, [_result("fail-1", Status.FAIL, severity=Severity.HIGH)])
    finding.status = "RESOLVED"
    db.commit()
    summary = build_dashboard_summary(db)
    db.close()
    assert summary["open_findings"] == 0
    assert summary["severity_distribution"] == {}


def test_dashboard_recent_activity_and_affected_models_reflect_real_rows():
    db = _db()
    record_test_run(db, [_result("a", Status.PASS)])
    summary = build_dashboard_summary(db)
    db.close()
    assert len(summary["recent_activity"]) == 1
    assert summary["recent_activity"][0]["test_id"] == "a"
    assert summary["affected_models"] == [{"provider": "sentinelai", "model": "injection-detector"}]


def test_dashboard_endpoint_empty_then_populated_after_sync(monkeypatch):
    fail_test = SecurityTest(
        id="dash-endpoint-fail",
        name="dash fail",
        category="jailbreak",
        description="d",
        severity=Severity.HIGH,
        attack_input="x",
        expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={"flagged": False}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (Status.FAIL, "not blocked"),
    )
    monkeypatch.setattr("proxy.main.all_tests", lambda: [fail_test])
    client = TestClient(app)

    empty = client.get("/v1/security-dashboard", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert empty.status_code == 200
    assert empty.json()["total_tests"] == 0

    client.post("/v1/findings/sync", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)

    populated = client.get("/v1/security-dashboard", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert populated.status_code == 200
    body = populated.json()
    assert body["total_tests"] == 1
    assert body["failed"] == 1
    assert body["open_findings"] == 1
    assert body["severity_distribution"] == {"high": 1}


def test_dashboard_response_never_includes_raw_attack_payload(monkeypatch):
    """Aggregate-only per Phase 6: no raw_input/raw_output anywhere in the
    dashboard payload, unlike the Findings detail endpoint."""
    fail_test = SecurityTest(
        id="dash-secret-check",
        name="secret check",
        category="jailbreak",
        description="d",
        severity=Severity.HIGH,
        attack_input="super secret attack payload xyz",
        expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input=t.attack_input, raw_output="super secret model output xyz", provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (Status.FAIL, "not blocked"),
    )
    monkeypatch.setattr("proxy.main.all_tests", lambda: [fail_test])
    client = TestClient(app)
    client.post("/v1/findings/sync", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)

    resp = client.get("/v1/security-dashboard", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert "super secret" not in resp.text
