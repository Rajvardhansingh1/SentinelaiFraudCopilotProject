"""Shared test-builder helpers so each attack-category plugin doesn't repeat
the same run/evaluate wiring (used by prompt-injection, jailbreak, and
system-prompt-extraction plugins — all three are "does the injection
detector flag this input" tests, just different attack phrasing)."""

from __future__ import annotations

from proxy.engine.models import RawExecution, SecurityTest, Severity, TestStatus
from proxy.middleware.injection_detector import check_injection


def injection_pattern_test(
    *,
    id: str,
    name: str,
    category: str,
    description: str,
    severity: Severity,
    attack_input: str,
    expected_behavior: str = "Request is flagged and blocked by the injection detector.",
) -> SecurityTest:
    def run(test: SecurityTest) -> RawExecution:
        result = check_injection(test.attack_input)
        return RawExecution(
            raw_input=test.attack_input,
            raw_output={"flagged": result.flagged, "matched_patterns": result.matched_patterns},
            provider="sentinelai",
            model="injection-detector",
        )

    def evaluate(evidence: RawExecution) -> tuple[TestStatus, str]:
        if evidence.raw_output["flagged"]:
            return TestStatus.PASS, f"Blocked as expected; matched: {evidence.raw_output['matched_patterns']}"
        return TestStatus.FAIL, "Guardrail did not flag a known attack prompt — detector regression."

    return SecurityTest(
        id=id,
        name=name,
        category=category,
        description=description,
        severity=severity,
        attack_input=attack_input,
        expected_behavior=expected_behavior,
        run=run,
        evaluate=evaluate,
    )
