"""Phase 2 (D-055) + Phase 12 (D-059): dedicated auth tests — signup/login
validation, cross-project isolation, token handling, and the auth-endpoint
rate limiter. Not covered by tests/auth_helpers.py, which only exercises
the happy path other test files bootstrap through."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import jwt
from fastapi.testclient import TestClient

from proxy.auth import _EFFECTIVE_JWT_SECRET, issue_token
from proxy.db.session import init_db
from proxy.main import app
from proxy.middleware.rate_limiter import reset_auth_rate_limit

init_db()


def _client():
    reset_auth_rate_limit()
    return TestClient(app)


# --- signup validation ---


def test_signup_rejects_weak_password():
    resp = _client().post("/v1/auth/signup", json={"email": "weak@example.com", "password": "short"})
    assert resp.status_code == 422


def test_signup_rejects_invalid_email():
    resp = _client().post("/v1/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert resp.status_code == 422


def test_signup_rejects_duplicate_email():
    client = _client()
    body = {"email": "dupe@example.com", "password": "password123"}
    first = client.post("/v1/auth/signup", json=body)
    assert first.status_code == 200
    second = client.post("/v1/auth/signup", json=body)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "email_taken"


def test_signup_lowercases_email():
    client = _client()
    resp = client.post("/v1/auth/signup", json={"email": "MixedCase@Example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "mixedcase@example.com"


def test_signup_creates_a_workspace_and_returns_a_working_token():
    client = _client()
    resp = client.post("/v1/auth/signup", json={"email": "workspace-check@example.com", "password": "password123"})
    token = resp.json()["access_token"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "workspace-check@example.com"


# --- login ---


def test_login_wrong_password_and_nonexistent_user_give_the_same_error():
    client = _client()
    client.post("/v1/auth/signup", json={"email": "login-check@example.com", "password": "password123"})

    wrong_pw = client.post("/v1/auth/login", json={"email": "login-check@example.com", "password": "wrong-password"})
    no_user = client.post("/v1/auth/login", json={"email": "nobody-here@example.com", "password": "whatever123"})

    assert wrong_pw.status_code == 401
    assert no_user.status_code == 401
    assert wrong_pw.json()["detail"]["code"] == "invalid_credentials"
    assert no_user.json()["detail"]["code"] == "invalid_credentials"


def test_login_succeeds_with_correct_credentials():
    client = _client()
    client.post("/v1/auth/signup", json={"email": "login-ok@example.com", "password": "password123"})
    resp = client.post("/v1/auth/login", json={"email": "login-ok@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "login-ok@example.com"


# --- token handling ---


def test_missing_token_is_rejected():
    resp = _client().get("/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "not_authenticated"


def test_garbage_token_is_rejected():
    resp = _client().get("/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "invalid_token"


def test_expired_token_is_rejected():
    from datetime import datetime, timedelta, timezone

    expired = jwt.encode(
        {"sub": "1", "iat": datetime.now(timezone.utc) - timedelta(hours=2), "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        _EFFECTIVE_JWT_SECRET,
        algorithm="HS256",
    )
    resp = _client().get("/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "invalid_token"


def test_token_for_deleted_user_is_rejected():
    """A token can be structurally valid (right secret, not expired) but
    reference a user_id that no longer exists — must not silently succeed."""
    token = issue_token(user_id=999_999_999)
    resp = _client().get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "user_not_found"


# --- cross-project isolation (spec_V3.md §9) ---


def test_a_users_project_is_invisible_to_another_user():
    client = _client()
    a = client.post("/v1/auth/signup", json={"email": "user-a@example.com", "password": "password123"})
    a_headers = {"Authorization": f"Bearer {a.json()['access_token']}"}
    project = client.post("/v1/projects", json={"name": "A's project"}, headers=a_headers)
    project_id = project.json()["id"]

    b = client.post("/v1/auth/signup", json={"email": "user-b@example.com", "password": "password123"})
    b_headers = {"Authorization": f"Bearer {b.json()['access_token']}"}

    resp = client.get(f"/v1/projects/{project_id}", headers=b_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "project_not_found"


def test_findings_and_dashboard_never_cross_project_boundaries():
    client = _client()
    a = client.post("/v1/auth/signup", json={"email": "iso-a@example.com", "password": "password123"})
    a_headers = {"Authorization": f"Bearer {a.json()['access_token']}"}
    a_project = client.post("/v1/projects", json={"name": "A"}, headers=a_headers).json()["id"]

    b = client.post("/v1/auth/signup", json={"email": "iso-b@example.com", "password": "password123"})
    b_headers = {"Authorization": f"Bearer {b.json()['access_token']}"}

    # B cannot read A's dashboard/findings/calls by guessing A's project_id.
    assert client.get("/v1/security-dashboard", params={"project_id": a_project}, headers=b_headers).status_code == 404
    assert client.get("/v1/findings", params={"project_id": a_project}, headers=b_headers).status_code == 404
    assert client.get("/v1/calls", params={"project_id": a_project}, headers=b_headers).status_code == 404


# --- auth endpoint rate limiting (Phase 12, D-059) ---


def test_login_is_rate_limited_per_ip():
    client = _client()
    client.post("/v1/auth/signup", json={"email": "rl-check@example.com", "password": "password123"})
    last_status = None
    for _ in range(15):
        last_status = client.post("/v1/auth/login", json={"email": "rl-check@example.com", "password": "wrong"}).status_code
    assert last_status == 429


def test_signup_is_rate_limited_per_ip():
    client = _client()
    last_status = None
    for i in range(15):
        last_status = client.post(
            "/v1/auth/signup", json={"email": f"rl-signup-{i}@example.com", "password": "password123"}
        ).status_code
    assert last_status == 429
