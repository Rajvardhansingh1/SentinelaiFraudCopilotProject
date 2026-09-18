from frontend.components.review_screen import compute_display


def _state(**overrides):
    base = {
        "extracted_fields": {"vendor": "Acme", "total": 42.5},
        "forensics_result": {"tamper_likelihood": "low"},
        "policy_verdict": {"compliant": True, "triggered_rules": []},
        "report_text": "Report",
        "report_guardrails": {"hallucination": {"score": 0.2}},
        "errors": [],
    }
    base.update(overrides)
    return base


def test_compute_display_compliant_case():
    display = compute_display(_state())
    assert display["verdict"] == "compliant"
    assert display["confidence"] == 0.8
    assert display["hallucination_pct"] == 0.2


def test_compute_display_non_compliant_case():
    display = compute_display(_state(policy_verdict={"compliant": False, "triggered_rules": ["spend_limit"]}))
    assert display["verdict"] == "non_compliant"


def test_compute_display_handles_missing_hallucination():
    display = compute_display(_state(report_guardrails={}))
    assert display["confidence"] == 1.0
    assert display["hallucination_pct"] == 0.0


def test_compute_display_surfaces_errors():
    display = compute_display(_state(errors=[{"node": "extractor", "code": "ocr_failed", "message": "x"}]))
    assert len(display["errors"]) == 1
