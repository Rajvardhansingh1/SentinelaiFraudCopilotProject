import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.db.models import ReviewDecision
from agents.db.session import get_session, init_db
from proxy.config import settings
from proxy.db.models import CallLog
from proxy.db.session import get_session as get_proxy_session
from proxy.db.session import init_db as init_proxy_db

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}

_is_prod = settings.env == "production"

app = FastAPI(
    title="Fraud Copilot API",
    # Same security posture as proxy/main.py (D-035): no docs/schema exposure in prod.
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
init_db()
init_proxy_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger("agents.api").exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An internal error occurred."}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


_graph = None


def _get_graph():
    # Same lazy-singleton pattern as frontend/lib/pipeline_client.py::_get_graph().
    global _graph
    if _graph is None:
        from agents.graph import build_graph

        _graph = build_graph()
    return _graph


@app.post("/v1/analyze-receipt")
async def analyze_receipt(session_id: str = Form(...), image: UploadFile = File(...)):
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "unsupported_file_type", "message": "Only png/jpg/jpeg images are supported."}},
        )

    # Security: never build the server-side path from the client-supplied filename
    # (path traversal risk) — same precaution as frontend/components/review_screen.py.
    tmp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(await image.read())

    try:
        graph = _get_graph()
        try:
            state = graph.invoke({"session_id": session_id, "image_path": str(tmp_path), "errors": []})
        except Exception as exc:
            state = {
                "extracted_fields": None,
                "forensics_result": None,
                "policy_verdict": None,
                "report_text": None,
                "report_guardrails": None,
                "errors": [{"node": "pipeline", "code": "pipeline_failed", "message": str(exc)}],
            }
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "extracted_fields": state.get("extracted_fields"),
        # Surfaces a proxy-side injection catch during OCR-text extraction (e.g. an
        # attack embedded in the scanned receipt text) to the frontend — same
        # detector as /v1/generate, previously computed but dropped from this response.
        "extraction_guardrails": state.get("extraction_guardrails"),
        "forensics_result": state.get("forensics_result"),
        "policy_verdict": state.get("policy_verdict"),
        "report_text": state.get("report_text"),
        "report_guardrails": state.get("report_guardrails"),
        "errors": state.get("errors", []),
    }


class ReviewDecisionIn(BaseModel):
    session_id: str
    receipt_ref: str
    system_verdict: str
    confidence: float
    hallucination_pct: float
    human_decision: str
    reviewer_notes: str | None = None


@app.post("/v1/review-decisions")
def create_review_decision(body: ReviewDecisionIn):
    db = get_session()
    try:
        row = ReviewDecision(**body.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "id": row.id,
            "session_id": row.session_id,
            "receipt_ref": row.receipt_ref,
            "system_verdict": row.system_verdict,
            "confidence": row.confidence,
            "hallucination_pct": row.hallucination_pct,
            "human_decision": row.human_decision,
            "reviewer_notes": row.reviewer_notes,
            "decided_at": row.decided_at,
        }
    finally:
        db.close()


@app.get("/v1/calls")
def list_calls(limit: int = 100):
    db = get_proxy_session()
    try:
        rows = db.query(CallLog).order_by(CallLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "operation": r.operation,
                "provider": r.provider,
                "model": r.model,
                "latency_ms": r.latency_ms,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "cost_estimate_usd": r.cost_estimate_usd,
                "guardrails": r.guardrails,
                "error_code": r.error_code,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    finally:
        db.close()
