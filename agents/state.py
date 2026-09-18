from typing import TypedDict


class FraudCaseState(TypedDict, total=False):
    session_id: str
    image_path: str
    ocr_text: str | None
    extracted_fields: dict | None
    extraction_guardrails: dict | None
    forensics_result: dict | None
    policy_verdict: dict | None
    policy_guardrails: dict | None
    report_text: str | None
    report_guardrails: dict | None
    errors: list[dict]
