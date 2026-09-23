"""Phase 12: executive + technical reports — built only from stored data,
no fabricated metrics, no secrets."""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from proxy.db.models import AgentActionLog, Baseline, Finding, SecurityEvent
from proxy.db.models import TestRunResult as RunResult
from proxy.db.session import SessionLocal, init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestStatus as Status
from proxy.findings import sync_findings
from proxy.main import app
from proxy.reports import build_executive_report, build_technical_report, executive_markdown, scrub, technical_markdown
from tests.auth_helpers import auth_headers_and_project

SECRET = "sk-ABCDEFGHIJKLMNOPQRST"  # matches pii_scanner's api_key regex (alnum only after sk-)

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


def _sync(client=None, **params):
    params.setdefault("project_id", PROJECT_ID)
    return (client or TestClient(app)).post("/v1/findings/sync", params=params, headers=AUTH_HEADERS)


def _clear():
    init_db()
    db = SessionLocal()
    for model in (SecurityEvent, Finding, RunResult, Baseline, AgentActionLog):
        db.query(model).delete()
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def _isolate():
    _clear()
    yield
    app.dependency_overrides.clear()
    _clear()


def _flip_test(status, test_id="flip", category="jailbreak"):
    return SecurityTest(
        id=test_id, name=test_id, category=category, description="d", severity=Severity.HIGH,
        attack_input="x", expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (status, "d"),
    )


# --- no fabricated metrics on an empty period ---


def test_executive_report_on_empty_db_is_explicitly_empty():
    db = SessionLocal()
    report = build_executive_report(db)
    db.close()
    assert report["latest_run"] is None
    assert report["scope"]["tests_in_latest_run"] == 0
    assert report["key_findings"] == []
    assert "No recorded test runs" in " ".join(report["limitations"])


def test_technical_report_on_empty_db_is_explicitly_empty():
    db = SessionLocal()
    report = build_technical_report(db)
    db.close()
    assert report["test_cases"] == []
    assert report["notes"] == ["No recorded test runs in this period."]


# --- built only from real data ---


def test_executive_report_reflects_real_test_run(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS), _flip_test(Status.FAIL, "flip2")])
    _sync()
    db = SessionLocal()
    report = build_executive_report(db)
    db.close()
    assert report["latest_run"]["status_counts"] == {"PASS": 1, "FAIL": 1}
    assert report["scope"]["tests_in_latest_run"] == 2
    assert len(report["key_findings"]) == 1
    assert report["key_findings"][0]["remediation"]


def test_technical_report_test_cases_carry_attack_input_when_definition_is_registered():
    """proxy/reports.py looks test_ids up in the *real* engine registry (not
    a per-request override) — using an actually-registered test here."""
    from proxy.engine.registry import all_tests

    real_test_id = all_tests()[0].id
    _sync()
    db = SessionLocal()
    report = build_technical_report(db)
    db.close()
    case = next(c for c in report["test_cases"] if c["test_id"] == real_test_id)
    assert case["attack_input"]
    assert case["reproduction"]["definition_available"] is True
    assert "run_id" in case["reproduction"]
    assert case["remediation"]


def test_technical_report_handles_a_run_row_whose_definition_no_longer_exists(monkeypatch):
    """A test_id from a historical run that's since been removed from the
    registry must not crash the report — attack_input/expected are None,
    definition_available is False, so the report says so honestly."""
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.FAIL)])
    _sync()
    db = SessionLocal()
    report = build_technical_report(db)
    db.close()
    [case] = report["test_cases"]
    assert case["attack_input"] is None
    assert case["reproduction"]["definition_available"] is False
    assert case["result"] == "FAIL"
    [finding] = report["findings"]
    assert finding["evidence"]["raw_input"] == "x"
    assert finding["remediation"]


def test_severity_distribution_only_counts_open_findings():
    from proxy.engine.runner import run_suite

    db = SessionLocal()
    [finding] = sync_findings(db, run_suite([_flip_test(Status.FAIL)]))
    finding.status = "RESOLVED"
    db.commit()
    report = build_executive_report(db)
    db.close()
    assert report["severity_distribution"] == {}


def test_major_changes_reflects_a_real_regression(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    _sync(client)
    client.post("/v1/baselines", json={"name": "good"}, params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.FAIL)])
    _sync(client)

    db = SessionLocal()
    report = build_executive_report(db)
    db.close()
    assert report["major_changes"]["baseline"] == "good"
    assert report["major_changes"]["regressions"] == ["flip"]


def test_period_filters_narrow_the_report(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    _sync()

    future = datetime.now(timezone.utc) + timedelta(days=1)
    db = SessionLocal()
    report = build_executive_report(db, since=future)
    db.close()
    assert report["latest_run"] is None


# --- limitations are honest, never overclaim ---


def test_limitations_flag_inconclusive_and_error_results(monkeypatch):
    monkeypatch.setattr(
        "proxy.main.all_tests",
        lambda: [_flip_test(Status.INCONCLUSIVE, "inc"), _flip_test(Status.ERROR, "err")],
    )
    _sync()
    db = SessionLocal()
    report = build_executive_report(db)
    db.close()
    text = " ".join(report["limitations"])
    assert "INCONCLUSIVE" in text
    assert "ERROR" in text


def test_limitations_always_present_even_with_all_pass(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    _sync()
    db = SessionLocal()
    report = build_executive_report(db)
    db.close()
    assert any("do not prove" in x for x in report["limitations"])


# --- no secrets in a report ---


def test_scrub_redacts_the_configured_provider_key(monkeypatch):
    monkeypatch.setattr("proxy.reports.settings.groq_api_key", "sk-configured-secret-value-999")
    assert scrub("error calling provider: sk-configured-secret-value-999") == "error calling provider: [REDACTED_CONFIGURED_KEY]"


def test_scrub_redacts_pii_patterns_in_nested_structures():
    data = {"evidence": {"raw_output": f"contact me at jane.doe@example.com, key {SECRET}"}}
    scrubbed = scrub(data)
    assert "jane.doe@example.com" not in scrubbed["evidence"]["raw_output"]
    assert SECRET not in scrubbed["evidence"]["raw_output"]


def test_scrub_leaves_run_id_keys_untouched():
    assert scrub({"run_id": "a1b2c3d4-1111-2222-3333-444455556666"})["run_id"] == "a1b2c3d4-1111-2222-3333-444455556666"


def test_report_containing_a_configured_key_in_evidence_is_scrubbed(monkeypatch):
    key = "sk-configured-secret-value-999"
    monkeypatch.setattr("proxy.reports.settings.groq_api_key", key)

    def run(t):
        return RawExecution(raw_input=f"leak: {key}", raw_output={"text": f"also here: {key}"}, provider="sentinelai", model="m")

    leaking_test = SecurityTest(
        id="leak", name="leak", category="jailbreak", description="d", severity=Severity.HIGH,
        attack_input=f"probe with {key}", expected_behavior="n/a", run=run,
        evaluate=lambda ev: (Status.FAIL, f"failed with {key} present"),
    )
    monkeypatch.setattr("proxy.main.all_tests", lambda: [leaking_test])
    _sync()

    db = SessionLocal()
    exec_report = build_executive_report(db)
    tech_report = build_technical_report(db)
    db.close()
    assert key not in str(exec_report)
    assert key not in str(tech_report)
    assert key not in executive_markdown(exec_report)
    assert key not in technical_markdown(tech_report)


# --- endpoints ---


def test_executive_endpoint_json():
    resp = TestClient(app).get("/v1/reports/executive", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "executive"


def test_technical_endpoint_markdown_is_plain_text():
    resp = TestClient(app).get("/v1/reports/technical", params={"format": "md", "project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text.startswith("# SentinelAI Security Report — Technical")


def test_executive_endpoint_markdown_no_secrets(monkeypatch):
    key = SECRET
    monkeypatch.setattr(
        "proxy.main.all_tests",
        lambda: [SecurityTest(
            id="leak2", name="leak2", category="jailbreak", description="d", severity=Severity.HIGH,
            attack_input="x", expected_behavior="n/a",
            run=lambda t: RawExecution(raw_input="x", raw_output=None, provider="sentinelai", model="m"),
            evaluate=lambda ev: (Status.FAIL, f"leaked {key}"),
        )],
    )
    _sync()
    resp = TestClient(app).get("/v1/reports/executive", params={"format": "md", "project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    assert key not in resp.text
