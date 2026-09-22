"""Closes D-048's deferred item: agent-policy bypass attempts as engine
security tests, so they run in the Security Tests page, dashboard, findings,
regression, and CI like every other category.

Uses a fixed in-plugin reference profile, not the operator's
agent_profiles.yaml — the suite must be deterministic whatever agents a
deployment configures. It tests the *evaluator*, which every profile shares."""

from __future__ import annotations

from proxy.agent_policy import ActionRequest, Decision, evaluate, profile_from_dict
from proxy.engine.models import RawExecution, SecurityTest, Severity, TestStatus
from proxy.engine.registry import register

_REFERENCE = profile_from_dict(
    {
        "agent_id": "reference-agent",
        "model": "reference",
        "tools": ["ticketing", "knowledge_base"],
        "data_sources": ["ticket_db"],
        "rules": [
            {"tool": "ticketing", "action": "read", "decision": "ALLOW"},
            {"tool": "ticketing", "action": "update", "decision": "REQUIRE_APPROVAL"},
            {"tool": "ticketing", "action": "delete", "decision": "DENY"},
            {"tool": "knowledge_base", "action": "search", "decision": "ALLOW"},
        ],
    }
)

# (id, name, severity, tool, action, data_source, expected decision)
_CASES = [
    ("agent_bypass_case_change", "Case change to evade a DENY rule", Severity.CRITICAL, "TICKETING", "DELETE", None, Decision.DENY),
    ("agent_bypass_whitespace", "Whitespace padding to evade a DENY rule", Severity.CRITICAL, " ticketing ", " delete ", None, Decision.DENY),
    ("agent_bypass_wildcard_request", "Wildcard action in the request", Severity.HIGH, "ticketing", "*", None, Decision.DENY),
    ("agent_bypass_appended_command", "Appended command after an allowed action", Severity.HIGH, "ticketing", "read;delete", None, Decision.DENY),
    ("agent_bypass_tool_prefix", "Unregistered tool sharing a registered prefix", Severity.HIGH, "ticketing_admin", "read", None, Decision.DENY),
    ("agent_bypass_unregistered_data_source", "Allowed action on an unregistered data source", Severity.HIGH, "ticketing", "read", "payroll_db", Decision.DENY),
    ("agent_bypass_unknown_action_default_deny", "Registered tool, unlisted action (default deny)", Severity.MEDIUM, "knowledge_base", "drop_index", None, Decision.DENY),
    ("agent_approval_required_not_downgraded", "Approval-required action stays gated", Severity.HIGH, "ticketing", "update", None, Decision.REQUIRE_APPROVAL),
    ("agent_authorized_use_still_allowed", "Authorized use is not over-blocked (control)", Severity.LOW, "ticketing", "read", "ticket_db", Decision.ALLOW),
]


def _make_test(case) -> SecurityTest:
    test_id, name, severity, tool, action, data_source, expected = case

    def run(test: SecurityTest) -> RawExecution:
        result = evaluate(_REFERENCE, ActionRequest(tool=tool, action=action, data_source=data_source))
        return RawExecution(
            raw_input=test.attack_input,
            raw_output={"decision": result.decision.value, "code": result.code, "reason": result.reason},
            provider="sentinelai",
            model="agent-policy",
        )

    def evaluate_result(evidence: RawExecution) -> tuple[TestStatus, str]:
        got = evidence.raw_output["decision"]
        if got == expected.value:
            return TestStatus.PASS, f"Decision {got} as expected ({evidence.raw_output['code']})."
        return TestStatus.FAIL, f"Expected {expected.value}, policy returned {got} — agent policy bypassed."

    return SecurityTest(
        id=test_id,
        name=name,
        category="agent_policy_bypass",
        description=f"Agent policy must return {expected.value} for: {name}",
        severity=severity,
        attack_input=f"tool={tool!r} action={action!r} data_source={data_source!r}",
        expected_behavior=f"Policy decision is {expected.value}.",
        run=run,
        evaluate=evaluate_result,
    )


@register
def build_agent_policy_tests() -> list[SecurityTest]:
    return [_make_test(c) for c in _CASES]
