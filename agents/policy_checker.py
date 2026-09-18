import json
from pathlib import Path

import yaml

from agents.proxy_client import ProxyCallFailed, call_proxy

DEFAULT_POLICY_PATH = Path(__file__).parent / "policies" / "expense_policy.yaml"

POLICY_SYSTEM_PROMPT_TEMPLATE = (
    "Check the extracted receipt fields against this expense policy (YAML):\n\n{policy_yaml}\n\n"
    'Respond with JSON matching this shape exactly: {{"triggered_rules": [str], "compliant": bool}}.'
)

_policy_cache: dict | None = None


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict:
    global _policy_cache
    if _policy_cache is None:
        with open(path) as f:
            _policy_cache = yaml.safe_load(f)
    return _policy_cache


def check_policy(session_id: str, extracted_fields: dict | None) -> tuple[dict | None, dict | None, dict | None]:
    """Returns (policy_verdict, guardrails, error)."""
    if extracted_fields is None:
        return {"triggered_rules": ["extraction_failed"], "compliant": False}, None, None

    policy = load_policy()

    if extracted_fields.get("date") is None:
        # D-022: missing date means age can't be computed — say so explicitly, don't assume compliant.
        note = "date is missing; receipt age cannot be verified against the policy."
    else:
        note = ""

    try:
        status_code, body = call_proxy(
            session_id=session_id,
            operation="policy_check",
            messages=[
                {"role": "system", "content": POLICY_SYSTEM_PROMPT_TEMPLATE.format(policy_yaml=yaml.dump(policy))},
                {"role": "user", "content": json.dumps(extracted_fields) + ("\n" + note if note else "")},
            ],
            schema_name="policy_verdict",
        )
    except ProxyCallFailed as exc:
        return None, None, {"node": "policy_checker", "code": "proxy_unreachable", "message": str(exc)}

    if status_code != 200:
        error = body.get("error") or {"code": "unknown", "message": "policy check failed"}
        return None, body.get("guardrails"), {"node": "policy_checker", "code": error["code"], "message": error["message"]}

    return body["output"], body["guardrails"], None
