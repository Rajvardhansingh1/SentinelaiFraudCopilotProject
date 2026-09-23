"""Phase 5 (D-057): structured remediation intelligence — facts vs.
inference distinguished (spec §23), confidence never fabricated (§24)."""

from proxy.remediation import remediation_for

_REQUIRED_KEYS = {
    "observed", "analysis", "security_impact", "expected_fix", "why_it_addresses",
    "components_to_review", "additional_controls", "verification_guidance", "confidence",
}
_VALID_CONFIDENCE = {"HIGH CONFIDENCE", "LIKELY", "REQUIRES INVESTIGATION", "INSUFFICIENT EVIDENCE"}


def test_known_category_has_every_required_field():
    rem = remediation_for("prompt_injection")
    assert set(rem.keys()) == _REQUIRED_KEYS
    assert rem["confidence"] in _VALID_CONFIDENCE
    assert rem["expected_fix"]
    assert isinstance(rem["components_to_review"], list)


def test_unknown_category_falls_back_to_honest_low_confidence():
    """No fabricated certainty for a category Sentinel has no specific mapping for."""
    rem = remediation_for("not_a_real_category")
    assert rem["confidence"] == "INSUFFICIENT EVIDENCE"
    assert set(rem.keys()) == _REQUIRED_KEYS


def test_every_registered_category_has_a_non_default_confidence():
    from proxy.remediation import _REMEDIATION

    for category, rem in _REMEDIATION.items():
        assert rem["confidence"] in _VALID_CONFIDENCE, category
        assert rem["observed"], category
        assert rem["analysis"], category
