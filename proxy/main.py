import logging
import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from proxy.config import settings
from proxy.db.models import CallLog
from proxy.db.session import get_session, init_db
from proxy.eval.hallucination_scorer import score_grounded
from proxy.middleware.injection_detector import check_injection
from proxy.middleware.pii_scanner import check_pii
from proxy.middleware.rate_limiter import check_and_increment
from proxy.middleware.schema_validator import SchemaValidationFailed, validate_structured_output
from proxy.provider import Provider, ProviderError, get_provider
from proxy.schemas import (
    ErrorDetail,
    GenerateRequest,
    GenerateResponse,
    Guardrails,
    PIIResult,
    Usage,
)

MAX_INPUT_CHARS = 50_000

_is_prod = settings.env == "production"

app = FastAPI(
    title="SentinelAI",
    # Never expose interactive API docs / raw OpenAPI schema in production — reduces
    # attacker recon surface (endpoint shapes, models) without hiding anything genuinely
    # secret (there's nothing secret in the schema itself, this is defense in depth).
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak a raw traceback/internal detail to the client — log it server-side,
    # return the same structured envelope every other error path already uses.
    logging.getLogger("proxy").exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"output": None, "guardrails": None, "usage": None, "error": {"code": "internal_error", "message": "An internal error occurred."}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/quota")
def quota():
    """D-020 footnote extended: 'N' is our own call count, not a real provider-side
    quota (no Groq/Gemini usage API integration exists). Display-only signal."""
    db = get_session()
    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        calls_today = db.query(CallLog).filter(CallLog.created_at >= today_start).count()
        return {"calls_today": calls_today}
    finally:
        db.close()


def _log(db, req: GenerateRequest, usage: Usage, guardrails: Guardrails, error_code: str | None) -> None:
    db.add(
        CallLog(
            session_id=req.session_id,
            operation=req.operation,
            provider=usage.provider,
            model=usage.model,
            latency_ms=usage.latency_ms,
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            cost_estimate_usd=usage.cost_estimate_usd,
            guardrails=guardrails.model_dump(),
            error_code=error_code,
        )
    )
    db.commit()


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, provider: Provider = Depends(get_provider)):
    db = get_session()
    try:
        inbound_text = "\n".join(m.content for m in req.messages)
        # S2/S3 scan untrusted content only — the system prompt is caller-authored and
        # trusted (D-002/D-001), so it must never be run through the injection/PII
        # detectors meant for OCR text and free-form user input. A caller's own
        # anti-jailbreak system prompt can otherwise self-trip the detector on every call.
        untrusted_text = "\n".join(m.content for m in req.messages if m.role != "system")

        if len(inbound_text) > MAX_INPUT_CHARS:
            empty_usage = Usage(provider="none", model="none")
            guardrails = Guardrails()
            _log(db, req, empty_usage, guardrails, "input_too_large")
            return JSONResponse(
                status_code=413,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="input_too_large", message=f"Input exceeds {MAX_INPUT_CHARS} character limit."),
                ).model_dump(),
            )

        injection = check_injection(untrusted_text)
        pii_req = check_pii(untrusted_text)
        guardrails = Guardrails(injection=injection, pii=pii_req)
        empty_usage = Usage(provider="none", model="none")

        if injection.flagged:
            _log(db, req, empty_usage, guardrails, "injection_detected")
            return JSONResponse(
                status_code=400,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="injection_detected", message="Inbound content matched a known attack pattern."),
                ).model_dump(),
            )

        if not check_and_increment(req.session_id):
            _log(db, req, empty_usage, guardrails, "rate_limit_exceeded")
            return JSONResponse(
                status_code=429,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="rate_limit_exceeded", message="Per-session call limit reached."),
                ).model_dump(),
            )

        start = time.monotonic()
        try:
            llm_resp = provider.generate(req.messages)
        except ProviderError as exc:
            _log(db, req, empty_usage, guardrails, "provider_failed")
            return JSONResponse(
                status_code=502,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="provider_failed", message=str(exc)),
                ).model_dump(),
            )
        latency_ms = int((time.monotonic() - start) * 1000)

        pii_resp = check_pii(llm_resp.text)
        guardrails.pii = PIIResult(
            found=pii_req.found or pii_resp.found,
            redacted=False,
            types=list(set(pii_req.types) | set(pii_resp.types)),
        )

        usage = Usage(
            provider=llm_resp.provider,
            model=llm_resp.model,
            tokens_in=llm_resp.tokens_in,
            tokens_out=llm_resp.tokens_out,
            latency_ms=latency_ms,
        )

        if req.grounding_context:
            guardrails.hallucination = score_grounded(llm_resp.text, req.grounding_context)

        output: object = llm_resp.text
        if req.schema_name:
            try:
                validated, retried = validate_structured_output(req.schema_name, lambda: llm_resp.text)
                guardrails.schema_valid = True
                guardrails.retried = retried
                output = validated.model_dump()
            except SchemaValidationFailed:
                guardrails.schema_valid = False
                _log(db, req, usage, guardrails, "schema_validation_failed")
                return JSONResponse(
                    status_code=422,
                    content=GenerateResponse(
                        output=None,
                        guardrails=guardrails,
                        usage=usage,
                        error=ErrorDetail(code="schema_validation_failed", message="Structured output failed validation after retry."),
                    ).model_dump(),
                )

        _log(db, req, usage, guardrails, None)
        return GenerateResponse(output=output, guardrails=guardrails, usage=usage, error=None)
    finally:
        db.close()
