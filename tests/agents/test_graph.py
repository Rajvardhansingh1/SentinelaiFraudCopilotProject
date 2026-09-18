from unittest.mock import patch

from agents.forensics import ForensicsResult
from agents.graph import build_graph


def _fake_extract(session_id, ocr_text):
    return (
        {"vendor": "Acme", "date": "2026-01-01", "line_items": [], "total": 42.5},
        {"schema_valid": True},
        None,
    )


def _fake_forensics(image_path):
    return ForensicsResult(ela_score=0.05, exif_consistent=True, exif_flags=[], tamper_likelihood="low")


def _fake_policy_ok(session_id, fields):
    return {"triggered_rules": [], "compliant": True}, {}, None


def _fake_policy_rate_limited(session_id, fields):
    return None, None, {"node": "policy_checker", "code": "rate_limit_exceeded", "message": "quota"}


def _fake_report(session_id, fields, forensics, policy):
    return "Report text", {"hallucination": {"score": 0.0}}, None


def test_full_pipeline_populates_all_fields_in_order():
    with (
        patch("agents.graph.run_ocr", lambda image_path: "vendor: Acme, total: 42.50"),
        patch("agents.graph.extract_fields", _fake_extract),
        patch("agents.graph.run_forensics", _fake_forensics),
        patch("agents.graph.check_policy", _fake_policy_ok),
        patch("agents.graph.write_report", _fake_report),
    ):
        graph = build_graph()
        result = graph.invoke({"session_id": "sess-1", "image_path": "fake.jpg", "errors": []})

    assert result["extracted_fields"]["vendor"] == "Acme"
    assert result["forensics_result"]["tamper_likelihood"] == "low"
    assert result["policy_verdict"]["compliant"] is True
    assert result["report_text"] == "Report text"
    assert result["errors"] == []


def test_pipeline_completes_with_partial_state_on_rate_limit():
    with (
        patch("agents.graph.run_ocr", lambda image_path: "vendor: Acme, total: 42.50"),
        patch("agents.graph.extract_fields", _fake_extract),
        patch("agents.graph.run_forensics", _fake_forensics),
        patch("agents.graph.check_policy", _fake_policy_rate_limited),
        patch("agents.graph.write_report", _fake_report),
    ):
        graph = build_graph()
        result = graph.invoke({"session_id": "sess-2", "image_path": "fake.jpg", "errors": []})

    assert result["policy_verdict"] is None
    assert any(e["code"] == "rate_limit_exceeded" for e in result["errors"])
    assert result["report_text"] == "Report text"
