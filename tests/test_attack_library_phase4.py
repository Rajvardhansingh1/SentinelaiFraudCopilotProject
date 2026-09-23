"""Phase 4: attack library expansion. Regression tests for the 4 new
categories added on top of the Phase 3 engine (prompt_injection was already
covered by tests/test_security_engine.py)."""

import proxy.engine.plugins  # noqa: F401 — registers every built-in plugin
from proxy.engine.models import Severity
from proxy.engine.models import TestStatus as Status
from proxy.engine.registry import all_tests
from proxy.engine.runner import run_suite

EXPECTED_CATEGORIES = {
    "prompt_injection",
    "jailbreak",
    "system_prompt_extraction",
    "sensitive_information_disclosure",
    "unsafe_output_behavior",
}


def _by_category(category: str):
    return [t for t in all_tests() if t.category == category]


def test_all_five_categories_are_registered():
    categories = {t.category for t in all_tests()}
    assert EXPECTED_CATEGORIES.issubset(categories)


def test_jailbreak_tests_pass_against_real_detector():
    tests = _by_category("jailbreak")
    assert len(tests) >= 3
    results = run_suite(tests)
    assert all(r.status == Status.PASS for r in results), [
        (r.test_id, r.status, r.detail) for r in results if r.status != Status.PASS
    ]


def test_system_prompt_extraction_tests_pass_against_real_detector():
    tests = _by_category("system_prompt_extraction")
    assert len(tests) >= 4
    results = run_suite(tests)
    assert all(r.status == Status.PASS for r in results), [
        (r.test_id, r.status, r.detail) for r in results if r.status != Status.PASS
    ]


def test_sensitive_disclosure_tests_pass_against_real_scanner():
    tests = _by_category("sensitive_information_disclosure")
    assert len(tests) >= 4
    results = run_suite(tests)
    assert all(r.status == Status.PASS for r in results), [
        (r.test_id, r.status, r.detail) for r in results if r.status != Status.PASS
    ]
    # The scanner's own `types` evidence must be specific, not just "found".
    api_key_result = next(r for r in results if r.test_id == "pii_api_key_leak")
    assert "api_key" in api_key_result.evidence.raw_output["types"]


def test_unsafe_output_tests_are_honestly_inconclusive_not_fabricated():
    """No harmful-content classifier exists — these must never silently
    report PASS/FAIL, per phase_dev_upgrade.md's explicit warning not to
    claim security that wasn't measured."""
    tests = _by_category("unsafe_output_behavior")
    assert len(tests) >= 2
    results = run_suite(tests)
    assert all(r.status == Status.INCONCLUSIVE for r in results)
    assert all("classifier" in r.detail.lower() for r in results)


def test_status_states_are_not_collapsed_to_a_boolean():
    """A full run across every category must surface more than one distinct
    TestStatus value — proves PASS/INCONCLUSIVE aren't being flattened."""
    results = run_suite(all_tests())
    statuses = {r.status for r in results}
    assert Status.PASS in statuses
    assert Status.INCONCLUSIVE in statuses


def test_no_duplicate_test_ids_across_all_plugins():
    ids = [t.id for t in all_tests()]
    assert len(ids) == len(set(ids)), "duplicate SecurityTest id across plugins"


def test_every_test_has_a_documented_severity():
    for test in all_tests():
        assert isinstance(test.severity, Severity)


def test_security_tests_run_endpoint_returns_all_five_statuses_serialized():
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    from fastapi.testclient import TestClient

    from proxy.main import app
    from tests.auth_helpers import auth_headers_and_project

    client = TestClient(app)
    headers, _ = auth_headers_and_project(client)
    resp = client.post("/v1/security-tests/run", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == len(all_tests())
    statuses = {row["status"] for row in body}
    assert "PASS" in statuses
    assert "INCONCLUSIVE" in statuses
    row = body[0]
    for key in ("test_id", "name", "category", "severity", "status", "detail", "evidence", "executed_at", "reproduction"):
        assert key in row
