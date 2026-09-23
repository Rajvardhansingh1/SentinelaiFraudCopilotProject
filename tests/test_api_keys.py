"""Phase 9 (D-058): project-scoped API keys for external submissions
(CI/SDK/service integrations) — distinct from a user's full-account JWT."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.api_keys import create_api_key, revoke_api_key, verify_api_key
from proxy.db.session import SessionLocal, init_db
from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestStatus as Status
from proxy.main import app
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))
OTHER_HEADERS, OTHER_PROJECT_ID = auth_headers_and_project(TestClient(app))


def _flip_test(status):
    return SecurityTest(
        id="apikey-flip", name="apikey-flip", category="jailbreak", description="d", severity=Severity.HIGH,
        attack_input="x", expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output={}, provider="sentinelai", model="injection-detector"),
        evaluate=lambda ev: (status, "d"),
    )


def test_verify_api_key_resolves_the_owning_project():
    db = SessionLocal()
    row, raw_key = create_api_key(db, PROJECT_ID, "ci-key")
    project = verify_api_key(db, raw_key)
    assert project is not None
    assert project.id == PROJECT_ID
    db.close()


def test_verify_api_key_rejects_unknown_key():
    db = SessionLocal()
    assert verify_api_key(db, "sk_live_not_a_real_key") is None
    db.close()


def test_verify_api_key_rejects_revoked_key():
    db = SessionLocal()
    row, raw_key = create_api_key(db, PROJECT_ID, "revoke-me")
    assert revoke_api_key(db, PROJECT_ID, row.id) is True
    assert verify_api_key(db, raw_key) is None
    db.close()


def test_revoke_rejects_a_key_from_a_different_project():
    db = SessionLocal()
    row, _ = create_api_key(db, PROJECT_ID, "cross-project")
    assert revoke_api_key(db, OTHER_PROJECT_ID, row.id) is False
    db.close()


def test_create_endpoint_returns_the_raw_key_once():
    client = TestClient(app)
    resp = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci"}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"].startswith("sk_live_")
    assert "key_hash" not in body


def test_list_endpoint_never_returns_the_raw_key():
    client = TestClient(app)
    client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci2"}, headers=AUTH_HEADERS)
    resp = client.get(f"/v1/projects/{PROJECT_ID}/api-keys", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    for row in resp.json():
        assert "key" not in row
        assert "key_hash" not in row
        assert row["key_prefix"].startswith("sk_live_")


def test_other_user_cannot_create_or_list_keys_for_a_project_they_do_not_own():
    client = TestClient(app)
    resp = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "x"}, headers=OTHER_HEADERS)
    assert resp.status_code == 404
    resp2 = client.get(f"/v1/projects/{PROJECT_ID}/api-keys", headers=OTHER_HEADERS)
    assert resp2.status_code == 404


def test_findings_sync_accepts_a_project_scoped_api_key(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    client = TestClient(app)
    created = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci3"}, headers=AUTH_HEADERS)
    raw_key = created.json()["key"]

    resp = client.post(
        "/v1/findings/sync",
        params={"project_id": PROJECT_ID, "source": "ci_cd"},
        headers={"Authorization": f"ApiKey {raw_key}"},
    )
    assert resp.status_code == 200


def test_findings_sync_rejects_an_api_key_for_a_different_project(monkeypatch):
    monkeypatch.setattr("proxy.main.all_tests", lambda: [_flip_test(Status.PASS)])
    client = TestClient(app)
    created = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci4"}, headers=AUTH_HEADERS)
    raw_key = created.json()["key"]

    resp = client.post(
        "/v1/findings/sync",
        params={"project_id": OTHER_PROJECT_ID, "source": "ci_cd"},
        headers={"Authorization": f"ApiKey {raw_key}"},
    )
    assert resp.status_code == 404


def test_revoked_api_key_is_rejected_by_findings_sync():
    client = TestClient(app)
    created = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci5"}, headers=AUTH_HEADERS)
    key_id = created.json()["id"]
    raw_key = created.json()["key"]
    client.delete(f"/v1/projects/{PROJECT_ID}/api-keys/{key_id}", headers=AUTH_HEADERS)

    resp = client.post(
        "/v1/findings/sync",
        params={"project_id": PROJECT_ID},
        headers={"Authorization": f"ApiKey {raw_key}"},
    )
    assert resp.status_code == 401


def test_an_api_key_cannot_be_used_on_endpoints_that_require_a_full_user_account():
    """An API key is deliberately narrower than a user's bearer token — it
    must not open up endpoints that were never given API-key support."""
    client = TestClient(app)
    created = client.post(f"/v1/projects/{PROJECT_ID}/api-keys", json={"name": "ci6"}, headers=AUTH_HEADERS)
    raw_key = created.json()["key"]

    resp = client.get(f"/v1/projects/{PROJECT_ID}/api-keys", headers={"Authorization": f"ApiKey {raw_key}"})
    assert resp.status_code == 401
