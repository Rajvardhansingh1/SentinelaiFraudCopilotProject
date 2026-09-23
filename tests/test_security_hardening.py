import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.db.session import init_db
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


def teardown_function():
    app.dependency_overrides.clear()
    rate_limiter.reset()


def test_docs_disabled_in_dev_config_is_still_enabled_by_default():
    # env defaults to "development" unless overridden — docs stay on for local dev.
    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_unhandled_exception_returns_structured_error_not_traceback():
    class ExplodingProvider:
        def generate(self, messages):
            raise RuntimeError("boom, should never leak this text to the client")

    app.dependency_overrides[get_provider] = lambda: ExplodingProvider()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/generate",
        json={
            "session_id": "sess-explode", "operation": "playground",
            "messages": [{"role": "user", "content": "hi"}], "project_id": PROJECT_ID,
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert "boom" not in resp.text
