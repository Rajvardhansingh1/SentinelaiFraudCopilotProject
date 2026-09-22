"""Remediation guidance per security-test category (Phase 5 requirement,
added with D-052). Static guidance text — advice, not a measurement."""

REMEDIATION: dict[str, str] = {
    "prompt_injection": (
        "Add or tighten the detector pattern that missed this input in proxy/redteam/attack_library.py, "
        "keep untrusted content out of the system role, and re-run the suite to confirm the block."
    ),
    "jailbreak": (
        "Extend role-override / persona patterns for the missed phrasing, and keep a hard-scoped system "
        "prompt so a partial bypass cannot unlock general behavior."
    ),
    "system_prompt_extraction": (
        "Block the extraction phrasing in the detector and never place secrets or credentials in system "
        "prompts — assume any system prompt can eventually leak."
    ),
    "sensitive_information_disclosure": (
        "Extend proxy/middleware/pii_scanner.py for the missed type and set the response policy to "
        "redact or block (gateway: GATEWAY_RESPONSE_PII_ACTION)."
    ),
    "unsafe_output_behavior": (
        "No automated harmful-content classifier exists yet — review outputs manually and wire a "
        "moderation check into proxy/engine/plugins/unsafe_output_tests.py::evaluate()."
    ),
    "agent_policy_bypass": (
        "Fix the evaluator in proxy/agent_policy.py so the request resolves to the expected decision; "
        "keep default-deny and exact canonical matching intact."
    ),
}

_DEFAULT = "Reproduce with the recorded input, fix the guardrail that should have caught it, and re-run the suite."


def remediation_for(category: str) -> str:
    return REMEDIATION.get(category, _DEFAULT)
