"""Phase 3 (D-056): execution_source tracking on TestRunResult — where a
test run was triggered from (dashboard, CI/CD, SDK, etc)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.db.models import TestRunResult
from proxy.db.session import SessionLocal, init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestStatus as Status
from proxy.findings import record_test_run
from proxy.main import app
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


def _flip_test(status):
    return SecurityTest(
        id="src-flip", name="src-flip", category="jailbreak", description="d", severity=Severity.HIGH,
        attack_input="x", expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (status, "d"),
    )


def test_record_test_run_defaults_to_dashboard():
    db = SessionLocal()
    from proxy.engine.models import TestResult
    from datetime import datetime, timezone

    result = TestResult(
        test_id="a", name="a", category="c", severity=Severity.LOW, status=Status.PASS, detail="d",
        evidence=RawExecution(raw_input="x", raw_output={}, provider="p", model="m"),
        executed_at=datetime.now(timezone.utc), reproduction={},
    )
    run_id = record_test_run(db, [result])
    row = db.query(TestRunResult).filter(TestRunResult.run_id == run_id).first()
    assert row.execution_source == "dashboard"
    db.close()


def test_record_test_run_rejects_unrecognized_source_falls_back_to_dashboard():
    db = SessionLocal()
    from proxy.engine.models import TestResult
    from datetime import datetime, timezone

    result = TestResult(
        test_id="a", name="a", category="c", severity=Severity.LOW, status=Status.PASS, detail="d",
        evidence=RawExecution(raw_input="x", raw_output={}, provider="p", model="m"),
        executed_at=datetime.now(timezone.utc), reproduction={},
    )
    run_id = record_test_run(db, [result], execution_source="not_a_real_source")
    row = db.query(TestRunResult).filter(TestRunResult.run_id == run_id).first()
    assert row.execution_source == "dashboard"
    db.close()


def test_findings_sync_endpoint_records_the_given_source(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    client = TestClient(app)
    resp = client.post(
        "/v1/findings/sync",
        params={"project_id": PROJECT_ID, "source": "ci_cd"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200

    db = SessionLocal()
    row = (
        db.query(TestRunResult)
        .filter(TestRunResult.project_id == PROJECT_ID, TestRunResult.test_id == "src-flip")
        .order_by(TestRunResult.id.desc())
        .first()
    )
    assert row.execution_source == "ci_cd"
    db.close()


def test_findings_sync_endpoint_defaults_source_to_dashboard(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    client = TestClient(app)
    resp = client.post("/v1/findings/sync", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert resp.status_code == 200

    db = SessionLocal()
    row = (
        db.query(TestRunResult)
        .filter(TestRunResult.project_id == PROJECT_ID, TestRunResult.test_id == "src-flip")
        .order_by(TestRunResult.id.desc())
        .first()
    )
    assert row.execution_source == "dashboard"
    db.close()
