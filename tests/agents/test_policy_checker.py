from unittest.mock import patch

from agents.policy_checker import check_policy, load_policy


def test_load_policy_parses_yaml():
    policy = load_policy()
    assert policy["spend_limits"]["default_max_total"] == 500.00
    assert "alcohol" in policy["category_restrictions"]["disallowed_categories"]
    assert policy["receipt_age"]["max_days_old"] == 90


def test_check_policy_short_circuits_when_extraction_failed():
    verdict, guardrails, error = check_policy("sess-1", None)
    assert verdict == {"triggered_rules": ["extraction_failed"], "compliant": False}
    assert guardrails is None
    assert error is None


def test_check_policy_calls_proxy_with_valid_fields():
    with patch("agents.policy_checker.call_proxy") as mock_call:
        mock_call.return_value = (200, {"output": {"triggered_rules": [], "compliant": True}, "guardrails": {}, "error": None})
        verdict, guardrails, error = check_policy("sess-2", {"vendor": "Acme", "date": "2026-01-01", "total": 50.0})
    assert verdict["compliant"] is True
    assert error is None


def test_check_policy_missing_date_adds_note_not_silent_pass():
    with patch("agents.policy_checker.call_proxy") as mock_call:
        mock_call.return_value = (200, {"output": {"triggered_rules": [], "compliant": True}, "guardrails": {}, "error": None})
        check_policy("sess-3", {"vendor": "Acme", "date": None, "total": 50.0})
        sent_messages = mock_call.call_args.kwargs["messages"]
        user_content = sent_messages[-1]["content"]
    assert "date is missing" in user_content
