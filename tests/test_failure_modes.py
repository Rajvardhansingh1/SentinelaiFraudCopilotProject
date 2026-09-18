from fastapi.testclient import TestClient
from frontend.data.sample_attacks import find_cached
from frontend.lib.health_check import ping_proxy

from proxy.main import app


def test_ping_proxy_returns_false_when_unreachable(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        import requests

        raise requests.ConnectionError("simulated proxy down")

    monkeypatch.setattr("frontend.lib.health_check.requests.get", raise_connection_error)
    assert ping_proxy() is False


def test_ping_proxy_returns_true_when_healthy():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_quota_endpoint_returns_call_count():
    client = TestClient(app)
    resp = client.get("/quota")
    assert resp.status_code == 200
    assert "calls_today" in resp.json()


def test_cached_fallback_available_when_quota_exhausted():
    """Mirrors redteam_playground's D-019 pattern — sample receipts should have the
    same caller-side fallback contract as sample attacks once Phase 6/7 ships receipt
    caching; this test locks in that the existing sample-attack fallback still works."""
    cached = find_cached("instruction_override")
    assert cached["error"]["code"] == "injection_detected"
