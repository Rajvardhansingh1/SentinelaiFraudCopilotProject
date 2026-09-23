"""Phase 2 (D-055): shared test helper for the now-global auth requirement.
Every endpoint except /health, /docs, /v1/auth/signup, /v1/auth/login now
needs a bearer token; project-scoped endpoints also need a project_id.
One signup + one project, reused by every test file that needs a caller."""

import itertools

from fastapi.testclient import TestClient

_counter = itertools.count()


def auth_headers_and_project(client: TestClient) -> tuple[dict, int]:
    """Signs up a fresh, uniquely-emailed user and one project. Returns
    ({"Authorization": "Bearer ..."}, project_id)."""
    email = f"test-{next(_counter)}-{id(client)}@example.com"
    resp = client.post("/v1/auth/signup", json={"email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    project_resp = client.post("/v1/projects", json={"name": "Test Project"}, headers=headers)
    assert project_resp.status_code == 200, project_resp.text
    return headers, project_resp.json()["id"]
