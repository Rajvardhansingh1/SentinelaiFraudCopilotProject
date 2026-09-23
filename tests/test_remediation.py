"""Phase 5 (D-057/D-060): structured remediation intelligence — facts vs.
inference distinguished (spec §23), confidence never fabricated (§24),
real project context surfaced only when Sentinel actually has it (§20/§25)."""

from proxy.remediation import remediation_for

_REQUIRED_KEYS = {
    "observed", "analysis", "security_impact", "expected_fix", "why_it_addresses",
    "components_to_review", "additional_controls", "verification_guidance", "confidence",
    "project_context",
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


def test_no_project_given_means_no_project_context():
    assert remediation_for("prompt_injection") == remediation_for("prompt_injection", None)
    assert remediation_for("prompt_injection")["project_context"] == []


def test_project_context_only_restates_declared_fields_never_invents():
    project = {"name": "Support Bot", "target_type": "agent", "repo_url": None, "description": None}
    notes = remediation_for("prompt_injection", project)["project_context"]
    assert notes == ['Target: "Support Bot" (agent).']

    project_full = {"name": "Support Bot", "target_type": "agent", "repo_url": "https://github.com/x/y", "description": "Handles refunds."}
    notes_full = remediation_for("prompt_injection", project_full)["project_context"]
    assert notes_full == [
        'Target: "Support Bot" (agent).',
        "Repository: https://github.com/x/y",
        "Project notes: Handles refunds.",
    ]


def test_every_registered_category_has_a_non_default_confidence():
    from proxy.remediation import _REMEDIATION

    for category, rem in _REMEDIATION.items():
        assert rem["confidence"] in _VALID_CONFIDENCE, category
        assert rem["observed"], category
        assert rem["analysis"], category
