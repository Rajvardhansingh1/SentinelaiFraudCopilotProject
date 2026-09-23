from typing import Any, Literal

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ProviderConfig(BaseModel):
    """BYOK / explicit-provider selection (D-041). `provider` names a key in
    proxy.provider.PROVIDER_REGISTRY. `api_key` is caller-supplied, used only
    server-side for this one call — never logged, never echoed back."""

    provider: Literal["groq", "gemini"] | None = None
    api_key: str | None = None


class GenerateRequest(BaseModel):
    session_id: str
    operation: Literal["extract", "policy_check", "report", "playground"]
    messages: list[Message]
    schema_name: str | None = None
    grounding_context: str | None = None
    project_id: int  # Phase 2 (D-055): every generate() call is scoped to one project
    provider_config: ProviderConfig | None = None


class InjectionResult(BaseModel):
    flagged: bool = False
    matched_patterns: list[str] = []


class PIIResult(BaseModel):
    found: bool = False
    redacted: bool = False
    types: list[str] = []


class HallucinationResult(BaseModel):
    score: float = 0.0
    mode: Literal["grounded", "ungrounded"] = "ungrounded"


class Guardrails(BaseModel):
    injection: InjectionResult = InjectionResult()
    pii: PIIResult = PIIResult()
    schema_valid: bool = True
    retried: bool = False
    hallucination: HallucinationResult | None = None


class Usage(BaseModel):
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost_estimate_usd: float = 0.0


class ErrorDetail(BaseModel):
    code: str
    message: str


class GenerateResponse(BaseModel):
    output: Any = None
    guardrails: Guardrails
    usage: Usage
    error: ErrorDetail | None = None


# --- structured output schemas selectable via `schema_name` ---


class ReceiptFields(BaseModel):
    vendor: str | None = None
    date: str | None = None
    line_items: list[str] = []
    total: float | None = None


class PolicyVerdict(BaseModel):
    triggered_rules: list[str] = []
    compliant: bool


SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "receipt_fields": ReceiptFields,
    "policy_verdict": PolicyVerdict,
}
