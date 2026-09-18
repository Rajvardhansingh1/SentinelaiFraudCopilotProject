import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from unittest.mock import patch

from fastapi.testclient import TestClient

from agents.api import app


def _client():
    return TestClient(app)


def test_analyze_receipt_returns_well_formed_response():
    fake_state = {
        "extracted_fields": {"vendor": "Acme", "total": 42.5},
        "forensics_result": {"tamper_likelihood": "low"},
        "policy_verdict": {"compliant": True, "triggered_rules": []},
        "report_text": "Report",
        "report_guardrails": {"hallucination": {"score": 0.1}},
        "errors": [],
    }
    fake_graph = type("G", (), {"invoke": staticmethod(lambda state: fake_state)})()

    with patch("agents.api._get_graph", return_value=fake_graph):
        client = _client()
        resp = client.post(
            "/v1/analyze-receipt",
            data={"session_id": "sess-1"},
            files={"image": ("receipt.jpg", b"fake-bytes", "image/jpeg")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted_fields"]["vendor"] == "Acme"
    assert body["report_text"] == "Report"
    assert body["errors"] == []


def test_analyze_receipt_never_uses_client_filename_for_server_path():
    """Security: server must generate its own random filename (uuid), never trust
    the client-supplied `image.filename` when building the on-disk path."""
    seen_paths = []

    def fake_invoke(state):
        seen_paths.append(state["image_path"])
        return {"extracted_fields": None, "forensics_result": None, "policy_verdict": None,
                "report_text": None, "report_guardrails": None, "errors": []}

    fake_graph = type("G", (), {"invoke": staticmethod(fake_invoke)})()

    malicious_name = "../../../../etc/passwd.jpg"
    with patch("agents.api._get_graph", return_value=fake_graph):
        client = _client()
        resp = client.post(
            "/v1/analyze-receipt",
            data={"session_id": "sess-1"},
            files={"image": (malicious_name, b"fake-bytes", "image/jpeg")},
        )

    assert resp.status_code == 200
    assert len(seen_paths) == 1
    assert "passwd" not in seen_paths[0]
    assert ".." not in seen_paths[0]


def test_analyze_receipt_rejects_bad_file_type():
    client = _client()
    resp = client.post(
        "/v1/analyze-receipt",
        data={"session_id": "sess-1"},
        files={"image": ("virus.exe", b"x", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_file_type"


def test_review_decision_write_and_query():
    client = _client()
    resp = client.post(
        "/v1/review-decisions",
        json={
            "session_id": "sess-1",
            "receipt_ref": "receipt.jpg",
            "system_verdict": "compliant",
            "confidence": 0.9,
            "hallucination_pct": 0.1,
            "human_decision": "approved",
            "reviewer_notes": "looks fine",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is not None
    assert body["human_decision"] == "approved"


def test_list_calls_returns_rows():
    client = _client()
    resp = client.get("/v1/calls?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
