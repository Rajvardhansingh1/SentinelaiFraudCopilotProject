from fastapi.testclient import TestClient

from frontend.data.sample_attacks import SAMPLE_ATTACKS
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse


class FakeProvider:
    def generate(self, messages):
        return LLMResponse("ack", 1, 1, 5, "fake-model", "fake")


def _client():
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()
    rate_limiter.reset()


def test_sample_attack_prompts_are_blocked_via_live_proxy():
    client = _client()
    for i, attack in enumerate(SAMPLE_ATTACKS):
        resp = client.post(
            "/v1/generate",
            json={
                "session_id": f"pg-attack-{i}",
                "operation": "playground",
                "messages": [{"role": "user", "content": attack["prompt"]}],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "injection_detected"
        assert body["guardrails"]["injection"]["matched_patterns"]


def test_benign_playground_prompt_is_allowed():
    client = _client()
    resp = client.post(
        "/v1/generate",
        json={
            "session_id": "pg-benign",
            "operation": "playground",
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["guardrails"]["injection"]["flagged"] is False
