"""Phase 5 (D-060): real project context (repo_url/description) surfaced in
remediation, never invented (spec_V3.md §20/§25)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.db.session import init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestStatus as Status
from proxy.main import app
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


def _flip_test(status):
    return SecurityTest(
        id="ctx-flip", name="ctx-flip", category="jailbreak", description="d", severity=Severity.HIGH,
        attack_input="x", expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (status, "d"),
    )


def test_project_create_accepts_repo_url_and_description():
    client = TestClient(app)
    resp = client.post(
        "/v1/projects",
        json={"name": "Ctx Project", "target_type": "agent", "repo_url": "https://github.com/x/y", "description": "A support bot."},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["repo_url"] == "https://github.com/x/y"
    assert body["description"] == "A support bot."


def test_project_patch_updates_context():
    client = TestClient(app)
    resp = client.patch(
        f"/v1/projects/{PROJECT_ID}",
        json={"repo_url": "https://github.com/a/b", "description": "Updated notes."},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["repo_url"] == "https://github.com/a/b"
    assert resp.json()["description"] == "Updated notes."

    fetched = client.get(f"/v1/projects/{PROJECT_ID}", headers=AUTH_HEADERS)
    assert fetched.json()["repo_url"] == "https://github.com/a/b"


def test_finding_remediation_carries_project_context(monkeypatch):
    client = TestClient(app)
    client.patch(
        f"/v1/projects/{PROJECT_ID}",
        json={"repo_url": "https://github.com/c/d", "description": "Checkout flow."},
        headers=AUTH_HEADERS,
    )
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.FAIL)])
    sync = client.post("/v1/findings/sync", params={"project_id": PROJECT_ID}, headers=AUTH_HEADERS)
    finding = sync.json()["findings_created"][0]
    assert "https://github.com/c/d" in " ".join(finding["remediation"]["project_context"])
    assert "Checkout flow." in " ".join(finding["remediation"]["project_context"])


def test_finding_remediation_has_no_project_context_when_undeclared():
    client = TestClient(app)
    other_headers, other_project = auth_headers_and_project(client)
    resp = client.post(
        "/v1/findings/sync", params={"project_id": other_project}, headers=other_headers
    )
    assert resp.status_code == 200
