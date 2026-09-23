import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from frontend.components.redteam_playground import QUOTA_BANNER, handle_response
from frontend.data.sample_attacks import SAMPLE_ATTACKS
from proxy.config import settings
from proxy.db.session import init_db
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse
from tests.auth_helpers import auth_headers_and_project

init_db()
AUTH_HEADERS, PROJECT_ID = auth_headers_and_project(TestClient(app))


class FakeProvider:
    def generate(self, messages):
        return LLMResponse("ack", 1, 1, 5, "fake-model", "fake")


def teardown_function():
    app.dependency_overrides.clear()
    rate_limiter.reset()


def test_proxy_returns_429_after_limit_exhausted():
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    client = TestClient(app)
    session = "pg-quota"
    for _ in range(settings.rate_limit_per_session):
        ok = client.post(
            "/v1/generate",
            json={"session_id": session, "operation": "playground", "messages": [{"role": "user", "content": "hi"}],
                  "project_id": PROJECT_ID},
            headers=AUTH_HEADERS,
        )
        assert ok.status_code == 200
    blocked = client.post(
        "/v1/generate",
        json={"session_id": session, "operation": "playground", "messages": [{"role": "user", "content": "hi"}],
              "project_id": PROJECT_ID},
        headers=AUTH_HEADERS,
    )
    assert blocked.status_code == 429


def test_handle_response_falls_back_to_cached_sample_on_429():
    attack = SAMPLE_ATTACKS[0]
    result = handle_response(429, {}, attack["id"])
    assert result["banner"] == QUOTA_BANNER
    assert result["display"] == attack["cached_response"]


def test_handle_response_falls_back_to_generic_for_free_text_on_429():
    result = handle_response(429, {}, None)
    assert result["banner"] == QUOTA_BANNER
    assert result["display"]["error"]["code"] == "rate_limit_exceeded"
