"""Phase 10 (D-049): SentinelAI Runtime Gateway pipeline.

    request -> inspection -> request policy -> provider routing -> response
            -> response inspection -> response policy -> final decision

Stateless: no DB, no rate-limit counters, no session state — every call is
decided from the request, the server-side policy, and the provider response
alone. Reuses SentinelAI's inspectors (injection detector, PII/secret
scanner) and provider layer as a library; does not import proxy.main, its
database, or the dashboard.

Audit events carry metadata only (decisions, pattern/type names, lengths,
sha256) — never raw content unless `store_raw_content` is explicitly on, and
even then secrets are redacted before anything is logged."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Literal

from proxy.middleware.injection_detector import check_injection
from proxy.middleware.pii_scanner import check_pii, redact_pii
from proxy.provider import Provider, ProviderError
from proxy.schemas import Message

audit_logger = logging.getLogger("sentinelai.gateway.audit")

PIIAction = Literal["allow", "redact", "block"]
Decision = Literal["ALLOW", "BLOCK", "ERROR"]


@dataclass(frozen=True)
class GatewayPolicy:
    block_on_injection: bool = True
    request_pii_action: PIIAction = "redact"
    response_pii_action: PIIAction = "redact"
    store_raw_content: bool = False


@dataclass
class GatewayResult:
    request_id: str
    decision: Decision
    status_code: int
    output: str | None
    reason: str
    provider: str | None = None
    model: str | None = None
    request_inspection: dict = field(default_factory=dict)
    response_inspection: dict = field(default_factory=dict)
    request_modified: bool = False
    response_modified: bool = False


def _fingerprint(text: str) -> dict:
    return {"length": len(text), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def _safe_raw(text: str) -> str:
    # Even when raw storage is on, never let a secret reach the audit log.
    redacted, _ = redact_pii(text)
    return redacted


def _audit(request_id: str, stage: str, policy: GatewayPolicy, raw: str | None = None, **fields) -> None:
    event = {"request_id": request_id, "stage": stage, **fields}
    if raw is not None:
        event["content"] = _fingerprint(raw)
        if policy.store_raw_content:
            event["content"]["raw"] = _safe_raw(raw)
    audit_logger.info(json.dumps(event, default=str))


def run_pipeline(
    messages: list[Message],
    route: str | None,
    policy: GatewayPolicy,
    provider_for: Callable[[str | None], Provider],
    application: str | None = None,
    event_sink: Callable[..., None] | None = None,
) -> GatewayResult:
    """`event_sink` (D-050) receives metadata-only monitoring events; None
    (the default) keeps the gateway fully stateless."""
    request_id = str(uuid.uuid4())

    def emit(event_type: str, severity: str, category: str, summary: str, **details) -> None:
        if event_sink is not None:
            event_sink(event_type=event_type, severity=severity, category=category, source="gateway",
                       application=application, summary=summary, details={"request_id": request_id, **details})
    # Same trust boundary as D-033: the caller's system prompt is trusted, everything else is inspected.
    untrusted = "\n".join(m.content for m in messages if m.role != "system")
    _audit(request_id, "request_received", policy, raw=untrusted, application=application, route=route)

    # --- request inspection + policy ---
    injection = check_injection(untrusted)
    pii = check_pii(untrusted)
    req_inspection = {
        "injection": {"flagged": injection.flagged, "matched_patterns": injection.matched_patterns},
        "pii": {"found": pii.found, "types": pii.types},
    }
    _audit(request_id, "request_inspected", policy, **req_inspection)

    def blocked(reason: str, stage: str, **extra) -> GatewayResult:
        _audit(request_id, "final_decision", policy, decision="BLOCK", stage_blocked=stage, reason=reason)
        return GatewayResult(request_id, "BLOCK", 403, None, reason, request_inspection=req_inspection, **extra)

    if injection.flagged:
        emit("attack_attempt", "high", "prompt_injection",
             f"Matched: {', '.join(injection.matched_patterns)}.",
             matched_patterns=injection.matched_patterns, blocked=policy.block_on_injection)
    if pii.found:
        emit("request_blocked" if policy.request_pii_action == "block" else "policy_violation", "medium",
             "sensitive_data_inbound", f"Request contained: {', '.join(pii.types)}.",
             types=pii.types, action=policy.request_pii_action)

    if injection.flagged and policy.block_on_injection:
        return blocked("Request matched a known attack pattern.", "request")
    if pii.found and policy.request_pii_action == "block":
        return blocked("Request contained PII/secrets and policy is 'block'.", "request")

    outbound = messages
    request_modified = False
    if pii.found and policy.request_pii_action == "redact":
        outbound = [m if m.role == "system" else Message(role=m.role, content=redact_pii(m.content)[0]) for m in messages]
        request_modified = True
    _audit(request_id, "request_policy", policy, action="redact" if request_modified else "allow")

    # --- provider routing ---
    try:
        provider = provider_for(route)
        llm = provider.generate(outbound)
    except (ProviderError, KeyError) as exc:
        reason = f"Unknown route '{route}'." if isinstance(exc, KeyError) else "Provider call failed."
        _audit(request_id, "final_decision", policy, decision="ERROR", reason=reason)
        return GatewayResult(request_id, "ERROR", 502 if not isinstance(exc, KeyError) else 400, None, reason,
                             request_inspection=req_inspection, request_modified=request_modified)
    _audit(request_id, "provider_called", policy, provider=llm.provider, model=llm.model,
           tokens_in=llm.tokens_in, tokens_out=llm.tokens_out, latency_ms=llm.latency_ms)

    # --- response inspection + policy ---
    resp_pii = check_pii(llm.text)
    resp_inspection = {"pii": {"found": resp_pii.found, "types": resp_pii.types}}
    _audit(request_id, "response_inspected", policy, raw=llm.text, **resp_inspection)
    if resp_pii.found:
        emit("request_blocked" if policy.response_pii_action == "block" else "policy_violation",
             "high" if "api_key" in resp_pii.types else "medium", "sensitive_information_disclosure",
             f"Response contained: {', '.join(resp_pii.types)}.",
             types=resp_pii.types, action=policy.response_pii_action, provider=llm.provider, model=llm.model)

    if resp_pii.found and policy.response_pii_action == "block":
        return blocked("Response contained PII/secrets and policy is 'block'.", "response",
                       provider=llm.provider, model=llm.model, response_inspection=resp_inspection,
                       request_modified=request_modified)

    output = llm.text
    response_modified = False
    if resp_pii.found and policy.response_pii_action == "redact":
        output = redact_pii(llm.text)[0]
        response_modified = True

    _audit(request_id, "final_decision", policy, decision="ALLOW",
           request_modified=request_modified, response_modified=response_modified)
    return GatewayResult(request_id, "ALLOW", 200, output, "Allowed.", llm.provider, llm.model,
                         req_inspection, resp_inspection, request_modified, response_modified)
