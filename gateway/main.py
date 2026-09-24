"""Phase 10 (D-049): SentinelAI Runtime Gateway — a separate FastAPI service
(default port 8002), independent of proxy/main.py's app, database, and
dashboard. Run: python -m uvicorn gateway.main:app --port 8002

Application -> Gateway -> Model. Provider keys stay server-side (settings);
the gateway never accepts, returns, or logs a credential."""

from __future__ import annotations

import hmac
import logging
import secrets
from typing import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gateway.pipeline import GatewayPolicy, run_pipeline
from proxy.config import settings
from proxy.provider import Provider, build_provider, get_provider
from proxy.schemas import Message

_is_prod = settings.env == "production"

# Bug fix: the gateway had zero authentication — anyone who could reach it could
# spend provider budget / bypass the app that's supposed to front it. This is
# a server-to-server service (Application -> Gateway -> Model, no browser login,
# no User/Project model here), so it gets a shared-secret bearer key rather than
# the proxy's per-user JWT — a genuinely different trust model, not a downgrade.
# Same hard-stop pattern as proxy/main.py's JWT_SECRET check: never a silent,
# insecure default in production.
if _is_prod and not settings.gateway_api_key:
    raise RuntimeError("GATEWAY_API_KEY must be set in production. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")

_EFFECTIVE_GATEWAY_KEY = settings.gateway_api_key or secrets.token_hex(32)
_GATEWAY_PUBLIC_PATHS = {"/health"}

app = FastAPI(
    title="SentinelAI Runtime Gateway",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def require_gateway_key(request: Request, call_next):
    """Every route needs `Authorization: Bearer <GATEWAY_API_KEY>` except /health."""
    if request.method == "OPTIONS" or request.url.path in _GATEWAY_PUBLIC_PATHS:
        return await call_next(request)
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, _EFFECTIVE_GATEWAY_KEY):
        return JSONResponse(status_code=401, content={"decision": "ERROR", "reason": "Missing or invalid gateway credential."})
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log type + path only — an exception message can echo request content.
    logging.getLogger("sentinelai.gateway").error("Unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"decision": "ERROR", "reason": "An internal error occurred."})


class GatewayRequest(BaseModel):
    messages: list[Message]
    route: str | None = None  # named provider (proxy.provider.PROVIDER_REGISTRY); None = default fallback chain
    application: str | None = None  # caller label for audit events


def get_policy() -> GatewayPolicy:
    return GatewayPolicy(
        block_on_injection=settings.gateway_block_on_injection,
        request_pii_action=settings.gateway_request_pii_action,
        response_pii_action=settings.gateway_response_pii_action,
        store_raw_content=settings.gateway_store_raw_content,
    )


def _route(name: str | None) -> Provider:
    return build_provider(name) if name else get_provider()


def get_router() -> Callable[[str | None], Provider]:
    return _route


def get_event_sink() -> Callable[..., None] | None:
    """D-050: off unless GATEWAY_RECORD_EVENTS=true — the gateway stays stateless by default."""
    if not settings.gateway_record_events:
        return None
    from proxy.events import record_event_standalone  # lazy: no DB import unless enabled

    return record_event_standalone


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/gateway/chat")
def gateway_chat(
    body: GatewayRequest,
    policy: GatewayPolicy = Depends(get_policy),
    router: Callable[[str | None], Provider] = Depends(get_router),
    event_sink: Callable[..., None] | None = Depends(get_event_sink),
):
    result = run_pipeline(body.messages, body.route, policy, router, application=body.application, event_sink=event_sink)
    return JSONResponse(
        status_code=result.status_code,
        content={
            "request_id": result.request_id,
            "decision": result.decision,
            "reason": result.reason,
            "output": result.output,
            "provider": result.provider,
            "model": result.model,
            "request_inspection": result.request_inspection,
            "response_inspection": result.response_inspection,
            "request_modified": result.request_modified,
            "response_modified": result.response_modified,
        },
    )
