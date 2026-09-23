"""Remediation intelligence per security-test category (Phase 5, D-057).

Static, rule-based guidance keyed by category — there is no LLM call here,
so every field is either a plain fact (what was observed, spec §23) or an
inference clearly labeled as such. Confidence is fixed per category because
the mapping from category -> guardrail component is itself a fixed fact
about this codebase, not a probabilistic judgment (spec §24: "do not
generate false certainty").

Recommendations only — spec §22: Sentinel never edits, patches, or deploys."""

from __future__ import annotations

from typing import TypedDict


class Remediation(TypedDict):
    observed: str
    analysis: str
    security_impact: str
    expected_fix: str
    why_it_addresses: str
    components_to_review: list[str]
    additional_controls: list[str]
    verification_guidance: str
    confidence: str  # HIGH CONFIDENCE | LIKELY | REQUIRES INVESTIGATION | INSUFFICIENT EVIDENCE


_REMEDIATION: dict[str, Remediation] = {
    "prompt_injection": {
        "observed": "The attack input reached the model without being flagged by the injection detector.",
        "analysis": "The detector's pattern set did not match this phrasing of an instruction-override attempt.",
        "security_impact": "An attacker can override intended behavior via crafted input, bypassing the guardrail meant to catch it.",
        "expected_fix": "Add or tighten the detector pattern that missed this input.",
        "why_it_addresses": "A matching pattern causes the request to be blocked before it reaches the model.",
        "components_to_review": ["proxy/redteam/attack_library.py", "proxy/middleware/injection_detector.py"],
        "additional_controls": ["Keep untrusted content out of the system role.", "Re-run the suite to confirm the block."],
        "verification_guidance": "Retest this finding after the pattern change; it must transition FAIL -> PASS with no other test regressing.",
        "confidence": "HIGH CONFIDENCE",
    },
    "jailbreak": {
        "observed": "A role-override or persona-switch attempt was not blocked by the detector.",
        "analysis": "The phrasing used to request a persona/role change fell outside the current pattern set.",
        "security_impact": "A successful jailbreak can unlock behavior the system prompt was meant to restrict.",
        "expected_fix": "Extend role-override / persona patterns for the missed phrasing.",
        "why_it_addresses": "Matching the phrasing causes the request to be blocked before reaching the model.",
        "components_to_review": ["proxy/redteam/attack_library.py", "proxy/middleware/injection_detector.py"],
        "additional_controls": ["Keep a hard-scoped system prompt so a partial bypass cannot unlock general behavior."],
        "verification_guidance": "Retest this finding after the pattern change; it must transition FAIL -> PASS.",
        "confidence": "HIGH CONFIDENCE",
    },
    "system_prompt_extraction": {
        "observed": "A request asking the model to reveal its system prompt was not blocked.",
        "analysis": "The extraction phrasing used fell outside the current pattern set.",
        "security_impact": "A leaked system prompt can expose internal instructions and make other attacks easier to craft.",
        "expected_fix": "Block the extraction phrasing in the detector.",
        "why_it_addresses": "Matching the phrasing causes the request to be blocked before reaching the model.",
        "components_to_review": ["proxy/redteam/attack_library.py"],
        "additional_controls": ["Never place secrets or credentials in system prompts — assume any system prompt can eventually leak."],
        "verification_guidance": "Retest this finding after the pattern change; it must transition FAIL -> PASS.",
        "confidence": "HIGH CONFIDENCE",
    },
    "sensitive_information_disclosure": {
        "observed": "Model output contained a sensitive-data pattern (PII, secret, or credential) that was not caught.",
        "analysis": "The PII/secret scanner's pattern or entity-type set did not match this instance.",
        "security_impact": "Sensitive data reaching a caller can violate privacy requirements and leak credentials.",
        "expected_fix": "Extend proxy/middleware/pii_scanner.py for the missed type and set the response policy to redact or block.",
        "why_it_addresses": "A matched type is redacted or blocked before the response reaches the caller.",
        "components_to_review": ["proxy/middleware/pii_scanner.py"],
        "additional_controls": ["Gateway deployments: set GATEWAY_RESPONSE_PII_ACTION to redact or block."],
        "verification_guidance": "Retest this finding after the scanner change; it must transition FAIL -> PASS.",
        "confidence": "HIGH CONFIDENCE",
    },
    "unsafe_output_behavior": {
        "observed": "Model output matched a category considered unsafe for this test but was not flagged.",
        "analysis": "No automated harmful-content classifier exists for this category yet — the finding is based on a static check, not model-based classification.",
        "security_impact": "Unsafe output reaching a caller can cause real harm depending on the application built on top of this guardrail.",
        "expected_fix": "Review the output manually and, if a real gap exists, wire a moderation check into the evaluator.",
        "why_it_addresses": "A working classifier would catch this category going forward.",
        "components_to_review": ["proxy/engine/plugins/unsafe_output_tests.py"],
        "additional_controls": [],
        "verification_guidance": "Manual review required before this can be retested automatically.",
        "confidence": "REQUIRES INVESTIGATION",
    },
    "agent_policy_bypass": {
        "observed": "An agent policy evaluation resolved to a decision other than the one the test expected.",
        "analysis": "The evaluator in proxy/agent_policy.py did not apply default-deny or canonical matching as expected for this input.",
        "security_impact": "An incorrect policy decision could allow an unauthorized tool action or block a legitimate one.",
        "expected_fix": "Fix the evaluator so the request resolves to the expected decision.",
        "why_it_addresses": "Correct evaluation logic produces the correct decision for this and equivalent inputs.",
        "components_to_review": ["proxy/agent_policy.py"],
        "additional_controls": ["Keep default-deny and exact canonical matching intact for any future change here."],
        "verification_guidance": "Retest this finding after the evaluator fix; it must transition FAIL -> PASS with no other agent-policy test regressing.",
        "confidence": "HIGH CONFIDENCE",
    },
}

_DEFAULT: Remediation = {
    "observed": "A security test recorded a FAIL result.",
    "analysis": "No category-specific guidance is registered for this test category.",
    "security_impact": "Unknown without further investigation — treat as a real gap until reviewed.",
    "expected_fix": "Reproduce with the recorded input, identify the guardrail that should have caught it, and fix it.",
    "why_it_addresses": "N/A — investigation needed before a specific fix can be recommended.",
    "components_to_review": [],
    "additional_controls": [],
    "verification_guidance": "Re-run the suite after any change; the finding must transition FAIL -> PASS.",
    "confidence": "INSUFFICIENT EVIDENCE",
}


def remediation_for(category: str) -> Remediation:
    return _REMEDIATION.get(category, _DEFAULT)


def remediation_summary(category: str) -> str:
    """Backward-compatible one-line form for places that show a single string
    (e.g. an existing markdown report line)."""
    return remediation_for(category)["expected_fix"]
