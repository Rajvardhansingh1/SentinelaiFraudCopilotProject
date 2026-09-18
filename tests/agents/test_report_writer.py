from unittest.mock import patch

from agents.report_writer import build_evidence_bundle, write_report
from fastapi.testclient import TestClient

from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse


def test_write_report_success():
    with patch("agents.report_writer.call_proxy") as mock_call:
        mock_call.return_value = (200, {"output": "The vendor is Acme.", "guardrails": {"hallucination": {"score": 0.0}}, "error": None})
        report_text, guardrails, error = write_report("sess-1", {"vendor": "Acme"}, None, None)
    assert report_text == "The vendor is Acme."
    assert error is None


def test_write_report_sends_evidence_as_grounding_context():
    with patch("agents.report_writer.call_proxy") as mock_call:
        mock_call.return_value = (200, {"output": "report", "guardrails": {}, "error": None})
        write_report("sess-2", {"vendor": "Acme"}, {"tamper_likelihood": "low"}, {"compliant": True})
        sent_grounding = mock_call.call_args.kwargs["grounding_context"]
    assert "Acme" in sent_grounding
    assert "low" in sent_grounding


class FakeProvider:
    def __init__(self, text):
        self.text = text

    def generate(self, messages):
        return LLMResponse(self.text, 1, 1, 5, "fake-model", "fake")


def teardown_function():
    app.dependency_overrides.clear()
    rate_limiter.reset()


def test_report_grounded_scoring_flags_invented_content():
    """Uses the real score_grounded (D-017), not mocked, via the live proxy."""
    evidence = build_evidence_bundle({"vendor": "Acme", "total": 42.50}, None, None)
    app.dependency_overrides[get_provider] = lambda: FakeProvider("A spaceship delivered the invoice from Mars.")
    client = TestClient(app)
    resp = client.post(
        "/v1/generate",
        json={
            "session_id": "sess-report-invented",
            "operation": "report",
            "messages": [{"role": "user", "content": "write it"}],
            "grounding_context": evidence,
        },
    )
    assert resp.json()["guardrails"]["hallucination"]["score"] > 0.5


def test_report_grounded_scoring_low_when_faithful():
    evidence = build_evidence_bundle({"vendor": "Acme", "total": 42.50}, None, None)
    app.dependency_overrides[get_provider] = lambda: FakeProvider("Acme total 42.5")
    client = TestClient(app)
    resp = client.post(
        "/v1/generate",
        json={
            "session_id": "sess-report-faithful",
            "operation": "report",
            "messages": [{"role": "user", "content": "write it"}],
            "grounding_context": evidence,
        },
    )
    assert resp.json()["guardrails"]["hallucination"]["score"] == 0.0
