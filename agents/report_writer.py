import json

from agents.proxy_client import ProxyCallFailed, call_proxy

REPORT_SYSTEM_PROMPT = (
    "You are an audit report writer. Write a short, human-readable summary of the "
    "expense claim using only the evidence provided below. Do not state anything "
    "not present in the evidence."
)


def build_evidence_bundle(
    extracted_fields: dict | None,
    forensics_result: dict | None,
    policy_verdict: dict | None,
) -> str:
    return json.dumps(
        {
            "extracted_fields": extracted_fields,
            "forensics_result": forensics_result,
            "policy_verdict": policy_verdict,
        }
    )


def write_report(
    session_id: str,
    extracted_fields: dict | None,
    forensics_result: dict | None,
    policy_verdict: dict | None,
) -> tuple[str | None, dict | None, dict | None]:
    """Returns (report_text, guardrails, error). D-023: free text, no schema_name."""
    evidence_bundle = build_evidence_bundle(extracted_fields, forensics_result, policy_verdict)

    try:
        status_code, body = call_proxy(
            session_id=session_id,
            operation="report",
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Evidence:\n{evidence_bundle}\n\nWrite the audit report using only the evidence above.",
                },
            ],
            grounding_context=evidence_bundle,
        )
    except ProxyCallFailed as exc:
        return None, None, {"node": "report_writer", "code": "proxy_unreachable", "message": str(exc)}

    if status_code != 200:
        error = body.get("error") or {"code": "unknown", "message": "report call failed"}
        return None, body.get("guardrails"), {"node": "report_writer", "code": error["code"], "message": error["message"]}

    return body["output"], body["guardrails"], None
