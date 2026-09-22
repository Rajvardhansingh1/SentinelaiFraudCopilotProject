"""Phase 9: agent security policy layer — authorized tool use, unauthorized
tool use, denied action, approval-required action, policy bypass attempts."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from proxy.agent_policy import (
    ActionRequest,
    Decision,
    load_profiles,
    profile_from_dict,
)
from proxy.agent_policy import evaluate as evaluate_policy
from proxy.db.models import AgentActionLog
from proxy.db.session import SessionLocal, init_db
from proxy.main import app

PROFILE_DATA = {
    "agent_id": "support-assistant",
    "model": "m",
    "tools": ["knowledge_base", "ticketing", "email"],
    "data_sources": ["public_docs", "ticket_db"],
    "rules": [
        {"tool": "knowledge_base", "action": "search", "decision": "ALLOW"},
        {"tool": "ticketing", "action": "read", "decision": "ALLOW"},
        {"tool": "ticketing", "action": "update", "decision": "REQUIRE_APPROVAL"},
        {"tool": "ticketing", "action": "delete", "decision": "DENY"},
        {"tool": "email", "action": "*", "decision": "REQUIRE_APPROVAL"},
    ],
}
PROFILE = profile_from_dict(PROFILE_DATA)


def _decide(tool, action, data_source=None):
    return evaluate_policy(PROFILE, ActionRequest(tool=tool, action=action, data_source=data_source)).decision


def _clear():
    init_db()
    db = SessionLocal()
    db.query(AgentActionLog).delete()
    db.commit()
    db.close()


setup_function = _clear
teardown_function = _clear


# --- pure policy evaluation ---


def test_authorized_tool_use_is_allowed():
    assert _decide("knowledge_base", "search") == Decision.ALLOW
    assert _decide("ticketing", "read", data_source="ticket_db") == Decision.ALLOW


def test_unauthorized_tool_is_denied():
    assert _decide("shell", "exec") == Decision.DENY


def test_explicitly_denied_action_is_denied():
    assert _decide("ticketing", "delete") == Decision.DENY


def test_approval_required_action():
    assert _decide("ticketing", "update") == Decision.REQUIRE_APPROVAL


def test_wildcard_rule_covers_any_action_on_that_tool():
    assert _decide("email", "send") == Decision.REQUIRE_APPROVAL


def test_registered_tool_with_no_matching_rule_is_default_denied():
    assert _decide("knowledge_base", "delete_index") == Decision.DENY


def test_unregistered_data_source_is_denied():
    assert _decide("ticketing", "read", data_source="payroll_db") == Decision.DENY


def test_deny_beats_allow_when_both_match():
    profile = profile_from_dict(
        {
            **PROFILE_DATA,
            "rules": [
                {"tool": "ticketing", "action": "*", "decision": "ALLOW"},
                {"tool": "ticketing", "action": "delete", "decision": "DENY"},
            ],
        }
    )
    decision = evaluate_policy(profile, ActionRequest(tool="ticketing", action="delete")).decision
    assert decision == Decision.DENY


def test_require_approval_beats_allow_when_both_match():
    profile = profile_from_dict(
        {
            **PROFILE_DATA,
            "rules": [
                {"tool": "email", "action": "*", "decision": "ALLOW"},
                {"tool": "email", "action": "send", "decision": "REQUIRE_APPROVAL"},
            ],
        }
    )
    decision = evaluate_policy(profile, ActionRequest(tool="email", action="send")).decision
    assert decision == Decision.REQUIRE_APPROVAL


# --- policy bypass attempts ---


@pytest.mark.parametrize(
    "tool,action",
    [
        ("TICKETING", "DELETE"),  # case change
        ("  ticketing ", " delete  "),  # whitespace padding
    ],
)
def test_case_and_whitespace_tricks_do_not_evade_a_deny_rule(tool, action):
    assert _decide(tool, action) == Decision.DENY


@pytest.mark.parametrize(
    "tool,action",
    [
        ("ticketing", "*"),  # wildcard in request to match an ALLOW
        ("*", "read"),  # wildcard tool
        ("ticketing", "read;delete"),  # appended command
        ("ticketing", "read delete"),
        ("knowledge_base_admin", "search"),  # prefix of a registered tool
        ("knowledge_base/../shell", "search"),  # path-style smuggling
        ("", "read"),
        ("ticketing", ""),
    ],
)
def test_malformed_or_smuggled_requests_are_denied(tool, action):
    assert _decide(tool, action) == Decision.DENY


def test_request_cannot_carry_its_own_approval():
    """Approval is never read from the request — an agent-supplied field
    claiming approval is simply not part of the request model."""
    client = TestClient(app)
    resp = client.post(
        "/v1/agents/support-assistant/evaluate",
        json={"tool": "ticketing", "action": "update", "approved": True, "decision": "ALLOW"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "REQUIRE_APPROVAL"
    assert resp.json()["execution_result"] == "pending_approval"


# --- config loading ---


def test_load_profiles_reads_server_side_yaml(tmp_path):
    path = tmp_path / "profiles.yaml"
    path.write_text(
        "agents:\n  - agent_id: Bot-A\n    model: m\n    tools: [Search]\n    data_sources: []\n"
        "    rules:\n      - {tool: Search, action: Query, decision: ALLOW}\n"
    )
    profiles = load_profiles(path)
    assert set(profiles) == {"bot-a"}  # canonicalized
    assert evaluate_policy(profiles["bot-a"], ActionRequest(tool="search", action="query")).decision == Decision.ALLOW


def test_missing_profiles_file_means_no_agents_not_a_crash(tmp_path):
    assert load_profiles(tmp_path / "nope.yaml") == {}


# --- endpoints: tracking + approval flow ---


def test_evaluate_endpoint_records_agent_tool_action_decision_and_result():
    client = TestClient(app)
    resp = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "delete"})
    assert resp.status_code == 200
    row = resp.json()
    assert row["agent_id"] == "support-assistant"
    assert row["tool"] == "ticketing"
    assert row["action"] == "delete"
    assert row["decision"] == "DENY"
    assert row["execution_result"] == "blocked"

    listed = client.get("/v1/agent-actions", params={"agent_id": "support-assistant"}).json()
    assert any(r["id"] == row["id"] for r in listed)


def test_allowed_action_is_recorded_but_never_executed():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "knowledge_base", "action": "search"}).json()
    assert row["decision"] == "ALLOW"
    assert row["execution_result"] == "allowed_not_executed"


def test_unknown_agent_returns_404():
    client = TestClient(app)
    resp = client.post("/v1/agents/ghost-agent/evaluate", json={"tool": "x", "action": "y"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "agent_not_found"


def test_list_agents_exposes_config_profiles():
    client = TestClient(app)
    agents = client.get("/v1/agents").json()
    assert any(a["agent_id"] == "support-assistant" for a in agents)


def test_approval_flow_approve_by_human():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "update"}).json()
    assert row["execution_result"] == "pending_approval"

    approved = client.post(f"/v1/agent-actions/{row['id']}/approve", json={"approver": "alice@example.com"})
    assert approved.status_code == 200
    assert approved.json()["execution_result"] == "approved_not_executed"
    assert approved.json()["approved_by"] == "alice@example.com"


def test_approval_flow_reject_by_human():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "email", "action": "send"}).json()
    rejected = client.post(f"/v1/agent-actions/{row['id']}/reject", json={"approver": "bob"})
    assert rejected.status_code == 200
    assert rejected.json()["execution_result"] == "rejected"


def test_agent_cannot_self_approve():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "update"}).json()
    resp = client.post(f"/v1/agent-actions/{row['id']}/approve", json={"approver": "  Support-Assistant "})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "self_approval_forbidden"


def test_denied_action_cannot_be_approved_after_the_fact():
    """Bypass attempt: 'approving' a DENY must not flip it to allowed."""
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "delete"}).json()
    resp = client.post(f"/v1/agent-actions/{row['id']}/approve", json={"approver": "alice"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "not_pending"


def test_already_resolved_action_cannot_be_re_resolved():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "update"}).json()
    client.post(f"/v1/agent-actions/{row['id']}/reject", json={"approver": "bob"})
    resp = client.post(f"/v1/agent-actions/{row['id']}/approve", json={"approver": "alice"})
    assert resp.status_code == 409


def test_blank_approver_is_rejected():
    client = TestClient(app)
    row = client.post("/v1/agents/support-assistant/evaluate", json={"tool": "ticketing", "action": "update"}).json()
    resp = client.post(f"/v1/agent-actions/{row['id']}/approve", json={"approver": "   "})
    assert resp.status_code == 422


# --- engine plugin (closes D-048 deferred item) ---


def _plugin_results():
    import proxy.engine.plugins  # noqa: F401
    from proxy.engine.registry import all_tests
    from proxy.engine.runner import run_suite

    return run_suite([t for t in all_tests() if t.category == "agent_policy_bypass"])


def test_agent_policy_bypass_plugin_registered_and_passing():
    from proxy.engine.models import TestStatus

    results = _plugin_results()
    assert len(results) >= 9
    failing = [(r.test_id, r.detail) for r in results if r.status != TestStatus.PASS]
    assert not failing, failing


def test_agent_policy_bypass_plugin_fails_if_the_evaluator_is_broken(monkeypatch):
    """Mutation check: a permissive evaluator must turn these tests FAIL,
    proving they actually guard the policy rather than always passing."""
    from proxy.agent_policy import PolicyDecision
    from proxy.engine.models import TestStatus

    monkeypatch.setattr(
        "proxy.engine.plugins.agent_policy_tests.evaluate",
        lambda profile, request: PolicyDecision(Decision.ALLOW, "broken", "rule_allow"),
    )
    results = {r.test_id: r.status for r in _plugin_results()}
    assert results["agent_bypass_case_change"] == TestStatus.FAIL
    assert results["agent_bypass_wildcard_request"] == TestStatus.FAIL
    assert results["agent_authorized_use_still_allowed"] == TestStatus.PASS
