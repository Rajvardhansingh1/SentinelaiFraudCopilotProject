import logging
import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

import proxy.engine.plugins  # noqa: F401 — import registers every built-in security test
from proxy.agent_actions import (
    ActionRequestIn,
    ApprovalError,
    ApprovalIn,
    action_log_to_dict,
    evaluate_and_record,
    resolve_approval,
)
from proxy.agent_policy import (
    OUT_OF_BOUNDS_CODES,
    ActionRequest,
    Decision,
    canon,
    load_profiles,
    profile_to_dict,
)
from proxy.auth import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    decode_token,
    get_current_user,
    hash_password,
    issue_token,
    verify_password,
)
from proxy.config import settings
from proxy.db.models import AgentActionLog, Baseline, CallLog, Finding, Project, TestRunResult, User, Workspace
from proxy.db.session import get_session, init_db
from proxy.engine.registry import all_tests
from proxy.engine.runner import run_suite
from proxy.dashboard import build_dashboard_summary
from proxy.eval.hallucination_scorer import score_grounded
from proxy.events import (
    ATTACK_ATTEMPT,
    FINDING_OPENED,
    POLICY_VIOLATION,
    REGRESSION_DETECTED,
    REQUEST_BLOCKED,
    SUSPICIOUS_TOOL_ACTIVITY,
    event_to_dict,
    events_config,
    purge_expired,
    query_events,
    record_event,
)
from proxy.findings import FindingPatch, finding_to_dict, record_test_run, sync_findings
from proxy.projects import ProjectCreate, create_workspace_for_user, owned_project, project_to_dict, require_project
from proxy.regression import (
    BaselineCreate,
    baseline_to_dict,
    build_regression_report,
    compare_runs,
    create_baseline,
    latest_run_id,
    run_snapshot,
)
from proxy.middleware.injection_detector import check_injection
from proxy.middleware.pii_scanner import check_pii
from proxy.middleware.rate_limiter import check_and_increment
from proxy.middleware.schema_validator import SchemaValidationFailed, validate_structured_output
from proxy.provider import MissingCredentialsError, Provider, ProviderError, build_provider, get_provider
from proxy.reports import build_executive_report, build_technical_report, executive_markdown, technical_csv, technical_markdown
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

if _is_prod and not settings.jwt_secret:
    # Phase 2 (D-055): a missing JWT_SECRET in production would issue tokens
    # signed with a per-process random secret — every restart invalidates
    # every session, and worse, a multi-instance deployment would have each
    # instance signing/verifying with a *different* secret. Hard stop, not a
    # silent fallback (CLAUDE.md: never a silent, insecure default).
    raise RuntimeError("JWT_SECRET must be set in production. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")

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
_startup_db = get_session()
try:
    purge_expired(_startup_db)  # D-050: apply retention on boot, not only on demand
finally:
    _startup_db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# Phase 2 (D-055): every route requires a valid bearer token except this
# allowlist. A single choke point, not a per-route opt-in — a new endpoint
# is authenticated by default, not accidentally left open.
_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/v1/auth/signup", "/v1/auth/login"}


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"detail": {"code": "not_authenticated", "message": "Missing bearer token."}})
    try:
        decode_token(auth_header[7:])
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


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


@app.post("/v1/auth/signup", response_model=AuthResponse)
def signup(body: SignupRequest):
    db = get_session()
    try:
        if db.query(User).filter(User.email == body.email).first() is not None:
            raise HTTPException(status_code=409, detail={"code": "email_taken", "message": "An account with this email already exists."})
        user = User(email=body.email, password_hash=hash_password(body.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        create_workspace_for_user(db, user.id)
        return AuthResponse(access_token=issue_token(user.id), user_id=user.id, email=user.email)
    finally:
        db.close()


@app.post("/v1/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    db = get_session()
    try:
        user = db.query(User).filter(User.email == body.email.lower()).first()
        # Same error for "no such user" and "wrong password" — never confirm
        # whether an email is registered to an unauthenticated caller.
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail={"code": "invalid_credentials", "message": "Incorrect email or password."})
        return AuthResponse(access_token=issue_token(user.id), user_id=user.id, email=user.email)
    finally:
        db.close()


@app.get("/v1/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@app.post("/v1/projects")
def create_project(body: ProjectCreate, user: User = Depends(get_current_user)):
    db = get_session()
    try:
        workspace = db.query(Workspace).filter(Workspace.owner_user_id == user.id).first()
        if workspace is None:  # defensive — signup always creates one, but never assume
            workspace = create_workspace_for_user(db, user.id)
        project = Project(workspace_id=workspace.id, name=body.name, target_type=body.target_type)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project_to_dict(project)
    finally:
        db.close()


@app.get("/v1/projects")
def list_projects(user: User = Depends(get_current_user)):
    db = get_session()
    try:
        workspace = db.query(Workspace).filter(Workspace.owner_user_id == user.id).first()
        if workspace is None:
            return []
        projects = db.query(Project).filter(Project.workspace_id == workspace.id).order_by(Project.created_at.desc()).all()
        return [project_to_dict(p) for p in projects]
    finally:
        db.close()


@app.get("/v1/projects/{project_id}")
def get_project(project: Project = Depends(require_project)):
    return project_to_dict(project)


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


def _select_tests(category: str | None):
    """Phase 8 (D-047): 'selecting a test suite' — a comma-separated list of
    categories, or every registered test when omitted."""
    tests = all_tests()
    if not category:
        return tests
    wanted = {c.strip() for c in category.split(",") if c.strip()}
    return [t for t in tests if t.category in wanted]


@app.post("/v1/security-tests/run")
def run_security_tests(category: str | None = None):
    """Phase 4 (D-043): runs every registered proxy/engine/plugins/* test
    (pattern-detector and PII-scanner based, all local — no LLM/network calls,
    safe to run synchronously per request) and returns each TestResult.
    FastAPI's default encoder serializes the dataclasses/Enum/datetime here.
    Phase 8 (D-047): optional `category` filter selects a test suite."""
    return run_suite(_select_tests(category))


@app.post("/v1/findings/sync")
def sync_security_findings(category: str | None = None, project: Project = Depends(require_project)):
    """Phase 5 (D-044): runs the full engine suite and opens a Finding for any
    FAIL result that doesn't already have an open one for the same test_id.
    Phase 6 (D-045): also logs every result (any status) to TestRunResult so
    the dashboard has real history to show — the only place that happens.
    Phase 8 (D-047): optional `category` filter selects a test suite.
    Phase 2 (D-055): requires `?project_id=`, scopes everything written to it."""
    results = run_suite(_select_tests(category))
    db = get_session()
    try:
        created = sync_findings(db, results, project_id=project.id)
        run_id = record_test_run(db, results, project_id=project.id)

        # Phase 11 (D-050): monitoring events — observations, not new findings.
        for f in created:
            record_event(db, event_type=FINDING_OPENED, severity=f.severity, category=f.category,
                         source="findings", model=f.model, summary=f"Finding #{f.id} opened: {f.test_id}.",
                         details={"finding_id": f.id, "test_id": f.test_id}, project_id=project.id)
        # Phase 7 (D-055 follow-up): baselines are project-scoped — only this
        # project's newest baseline is eligible for regression comparison.
        baseline = (
            db.query(Baseline)
            .filter(Baseline.project_id == project.id)
            .order_by(Baseline.created_at.desc())
            .first()
        )
        if baseline is not None and baseline.run_id != run_id:
            diff = compare_runs(run_snapshot(db, baseline.run_id), run_snapshot(db, run_id))
            for r in diff["regressions"]:
                record_event(db, event_type=REGRESSION_DETECTED, severity=r["current_severity"],
                             category=r["category"], source="regression",
                             summary=f"{r['test_id']} regressed PASS -> FAIL vs baseline '{baseline.name}'.",
                             details={"test_id": r["test_id"], "baseline_id": baseline.id, "run_id": run_id},
                             project_id=project.id)
        return {
            "results": results,
            "findings_created": [finding_to_dict(f) for f in created],
        }
    finally:
        db.close()


def _agent_profiles():
    # Read per call: small file, and lets config changes apply without a restart.
    return load_profiles(settings.agent_profiles_path)


@app.get("/v1/agents")
def list_agents():
    """Phase 9 (D-048): agent profiles from server-side config only."""
    return [profile_to_dict(p) for p in _agent_profiles().values()]


@app.post("/v1/agents/{agent_id}/evaluate")
def evaluate_agent_action(agent_id: str, body: ActionRequestIn, project_id: int | None = None, user: User = Depends(get_current_user)):
    """Decides ALLOW / DENY / REQUIRE_APPROVAL for one requested tool action
    and records it. Never executes the tool. `project_id` is optional
    (agent profiles are global config, not yet tied 1:1 to a project) — when
    given, it must belong to the caller and tags the resulting log/event."""
    profile = _agent_profiles().get(canon(agent_id))
    if profile is None:
        raise HTTPException(status_code=404, detail={"code": "agent_not_found", "message": "No such agent profile."})
    db = get_session()
    try:
        if project_id is not None:
            owned_project(db, project_id, user)
        decision, row = evaluate_and_record(
            db, profile, ActionRequest(tool=body.tool, action=body.action, data_source=body.data_source), project_id=project_id
        )
        # D-050: a normal denial is a policy violation; reaching outside the
        # agent's declared tools/data sources is suspicious. ALLOW / pending are not events.
        if decision.decision == Decision.DENY:
            suspicious = decision.code in OUT_OF_BOUNDS_CODES
            record_event(db, event_type=SUSPICIOUS_TOOL_ACTIVITY if suspicious else POLICY_VIOLATION,
                         severity="high" if suspicious else "medium", category="agent_policy", source="agent_policy",
                         application=profile.agent_id, model=profile.model,
                         summary=f"{row.tool}.{row.action} denied ({decision.code}).",
                         details={"action_log_id": row.id, "code": decision.code, "tool": row.tool, "action": row.action},
                         project_id=project_id)
        return action_log_to_dict(row)
    finally:
        db.close()


@app.get("/v1/agent-actions")
def list_agent_actions(agent_id: str | None = None, limit: int = 100, project_id: int | None = None, user: User = Depends(get_current_user)):
    db = get_session()
    try:
        if project_id is not None:
            owned_project(db, project_id, user)
        query = db.query(AgentActionLog).order_by(AgentActionLog.created_at.desc())
        if agent_id:
            query = query.filter(AgentActionLog.agent_id == canon(agent_id))
        if project_id is not None:
            query = query.filter(AgentActionLog.project_id == project_id)
        return [action_log_to_dict(r) for r in query.limit(limit).all()]
    finally:
        db.close()


def _resolve(log_id: int, body: ApprovalIn, approve: bool):
    db = get_session()
    try:
        return action_log_to_dict(resolve_approval(db, log_id, body.approver, approve))
    except ApprovalError as exc:
        row = db.query(AgentActionLog).filter(AgentActionLog.id == log_id).first()
        # D-050: self-approval, or trying to approve a DENY into an ALLOW, is suspicious.
        if row is not None and (exc.code == "self_approval_forbidden" or (exc.code == "not_pending" and row.decision == "DENY")):
            record_event(db, event_type=SUSPICIOUS_TOOL_ACTIVITY, severity="high", category="agent_policy",
                         source="agent_policy", application=row.agent_id,
                         summary=f"Approval bypass attempt on action #{row.id} ({exc.code}).",
                         details={"action_log_id": row.id, "code": exc.code}, project_id=row.project_id)
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})
    finally:
        db.close()


@app.post("/v1/agent-actions/{log_id}/approve")
def approve_agent_action(log_id: int, body: ApprovalIn):
    return _resolve(log_id, body, approve=True)


@app.post("/v1/agent-actions/{log_id}/reject")
def reject_agent_action(log_id: int, body: ApprovalIn):
    return _resolve(log_id, body, approve=False)


@app.post("/v1/baselines")
def create_security_baseline(body: BaselineCreate, project: Project = Depends(require_project)):
    """Phase 7 (D-046, project-scoped per D-055): pins a baseline to a
    recorded run in this project (the latest one unless `run_id` is given).
    409 if there is no run to baseline — never creates an empty baseline
    that would silently compare against nothing."""
    db = get_session()
    try:
        baseline = create_baseline(db, body.name, body.run_id, project_id=project.id)
        if baseline is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "no_run_to_baseline",
                    "message": "No recorded test run to baseline. Run POST /v1/findings/sync first.",
                },
            )
        return baseline_to_dict(baseline)
    finally:
        db.close()


@app.get("/v1/baselines")
def list_baselines(project: Project = Depends(require_project)):
    db = get_session()
    try:
        rows = (
            db.query(Baseline)
            .filter(Baseline.project_id == project.id)
            .order_by(Baseline.created_at.desc())
            .all()
        )
        return [baseline_to_dict(b) for b in rows]
    finally:
        db.close()


@app.get("/v1/regression-report")
def regression_report(baseline_id: int | None = None, run_id: str | None = None, project: Project = Depends(require_project)):
    """Compares a run against a baseline, both scoped to this project (D-055).
    Defaults to the newest baseline vs the newest recorded run. Returns
    counts *and* full per-test detail — no single 'security score' is
    produced (spec: a score must not be the sole source of truth)."""
    db = get_session()
    try:
        baseline_query = db.query(Baseline).filter(Baseline.project_id == project.id)
        if baseline_id is not None:
            baseline = baseline_query.filter(Baseline.id == baseline_id).first()
        else:
            baseline = baseline_query.order_by(Baseline.created_at.desc()).first()
        if baseline is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "baseline_not_found", "message": "No baseline exists yet. Create one first."},
            )

        if run_id is not None:
            # A caller-supplied run_id must belong to this project too — otherwise
            # a run_id guessed/leaked from another project could pull its data in.
            owned_run = (
                db.query(TestRunResult)
                .filter(TestRunResult.run_id == run_id, TestRunResult.project_id == project.id)
                .first()
            )
            target_run_id = run_id if owned_run is not None else None
        else:
            target_run_id = latest_run_id(db, project_id=project.id)
        if target_run_id is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "no_run_to_compare", "message": "No recorded test run to compare against."},
            )
        return build_regression_report(db, baseline, target_run_id)
    finally:
        db.close()


@app.get("/v1/events")
def list_events(
    since: datetime | None = None,
    until: datetime | None = None,
    severity: str | None = None,
    min_severity: str | None = None,
    application: str | None = None,
    model: str | None = None,
    category: str | None = None,
    event_type: str | None = None,
    limit: int = 200,
    project: Project = Depends(require_project),
):
    """Phase 11 (D-050, project-scoped per D-055): security events, filterable
    by time / severity / application / model / category / event type
    (comma-separated where plural makes sense). Events are observations — see
    /v1/findings for vulnerabilities."""
    db = get_session()
    try:
        rows = query_events(db, since=since, until=until, severity=severity, min_severity=min_severity,
                            application=application, model=model, category=category, event_type=event_type,
                            limit=min(max(limit, 1), 1000), project_id=project.id)
        return [event_to_dict(e) for e in rows]
    finally:
        db.close()


@app.get("/v1/events/config")
def get_events_config():
    return events_config()


@app.post("/v1/events/retention/apply")
def apply_event_retention():
    """Deletes events older than EVENTS_RETENTION_DAYS (0 = keep forever).
    Only SecurityEvent rows — findings/test history are never touched."""
    db = get_session()
    try:
        return {"deleted": purge_expired(db), "retention_days": settings.events_retention_days}
    finally:
        db.close()


@app.get("/v1/reports/executive")
def get_executive_report(since: datetime | None = None, until: datetime | None = None, format: str = "json", project: Project = Depends(require_project)):
    """Phase 10 (project-scoped per D-055): `format` is json (default) or md."""
    db = get_session()
    try:
        report = build_executive_report(db, since, until, project_id=project.id)
        if format == "md":
            return PlainTextResponse(executive_markdown(report))
        return report
    finally:
        db.close()


@app.get("/v1/reports/technical")
def get_technical_report(since: datetime | None = None, until: datetime | None = None, format: str = "json", project: Project = Depends(require_project)):
    """Phase 10 (project-scoped per D-055): `format` is json (default), md, or csv."""
    db = get_session()
    try:
        report = build_technical_report(db, since, until, project_id=project.id)
        if format == "md":
            return PlainTextResponse(technical_markdown(report))
        if format == "csv":
            return PlainTextResponse(technical_csv(report), media_type="text/csv")
        return report
    finally:
        db.close()


@app.get("/v1/security-dashboard")
def security_dashboard(project: Project = Depends(require_project)):
    """Phase 6 (D-045): aggregate-only summary (no raw attack payloads/model
    output) from what's actually been persisted via /v1/findings/sync. Empty
    dict fields / zero counts if nothing has run yet — never fabricated.
    Phase 2 (D-055): requires `?project_id=`, scoped to that project only."""
    db = get_session()
    try:
        return build_dashboard_summary(db, project_id=project.id)
    finally:
        db.close()


@app.get("/v1/findings")
def list_findings(status: str | None = None, project: Project = Depends(require_project)):
    """Phase 2 (D-055): requires `?project_id=` — a request for Project A's
    findings can never return Project B's (spec_V3.md §9)."""
    db = get_session()
    try:
        query = db.query(Finding).filter(Finding.project_id == project.id).order_by(Finding.created_at.desc())
        if status:
            query = query.filter(Finding.status == status)
        return [finding_to_dict(f) for f in query.all()]
    finally:
        db.close()


def _owned_finding(db, finding_id: int, user: User) -> Finding:
    """Shared ownership check for the two finding_id-in-path endpoints below
    (get/patch) — a finding's project must belong to a workspace this user
    owns. 404, not 403, on mismatch — never confirm a finding ID exists to
    someone who doesn't own its project."""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if finding is None or finding.project_id is None:
        raise HTTPException(status_code=404, detail={"code": "finding_not_found", "message": "No such finding."})
    try:
        owned_project(db, finding.project_id, user)  # raises 404 if not owned
    except HTTPException:
        raise HTTPException(status_code=404, detail={"code": "finding_not_found", "message": "No such finding."})
    return finding


@app.get("/v1/findings/{finding_id}")
def get_finding(finding_id: int, user: User = Depends(get_current_user)):
    db = get_session()
    try:
        return finding_to_dict(_owned_finding(db, finding_id, user))
    finally:
        db.close()


@app.patch("/v1/findings/{finding_id}")
def update_finding_status(finding_id: int, body: FindingPatch, user: User = Depends(get_current_user)):
    """Status-only update. The row is never deleted on resolution — evidence
    and reproduction stay intact regardless of status (spec requirement)."""
    db = get_session()
    try:
        finding = _owned_finding(db, finding_id, user)
        finding.status = body.status
        db.commit()
        db.refresh(finding)
        return finding_to_dict(finding)
    finally:
        db.close()


@app.get("/v1/calls")
def list_calls(limit: int = 100, project: Project = Depends(require_project)):
    # Moved here from agents/api.py (Fraud Copilot's now-paused service) so the
    # dashboard's call log doesn't depend on a Fraud Copilot backend being up.
    # Phase 2 (D-055): requires `?project_id=`, scoped to that project only.
    db = get_session()
    try:
        rows = (
            db.query(CallLog)
            .filter(CallLog.project_id == project.id)
            .order_by(CallLog.created_at.desc())
            .limit(limit)
            .all()
        )
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


def _log(db, req: GenerateRequest, usage: Usage, guardrails: Guardrails, error_code: str | None) -> None:
    db.add(
        CallLog(
            project_id=req.project_id,
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
def generate(req: GenerateRequest, provider: Provider = Depends(get_provider), user: User = Depends(get_current_user)):
    db = get_session()
    try:
        # Phase 2 (D-055): project_id arrives in the JSON body (not a query
        # param), so ownership is checked directly rather than via the
        # require_project FastAPI-dependency form.
        owned_project(db, req.project_id, user)
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
            record_event(db, event_type=REQUEST_BLOCKED, severity="low", category="input_size", source="proxy",
                         application=req.operation, summary=f"Input over {MAX_INPUT_CHARS} chars rejected.",
                         details={"length": len(inbound_text)}, project_id=req.project_id)
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

        if pii_req.found:
            record_event(db, event_type=POLICY_VIOLATION, severity="medium", category="sensitive_data_inbound",
                         source="proxy", application=req.operation,
                         summary=f"Inbound content contained: {', '.join(pii_req.types)}.",
                         details={"types": pii_req.types}, project_id=req.project_id)

        if injection.flagged:
            _log(db, req, empty_usage, guardrails, "injection_detected")
            record_event(db, event_type=ATTACK_ATTEMPT, severity="high", category="prompt_injection", source="proxy",
                         application=req.operation,
                         summary=f"Blocked; matched: {', '.join(injection.matched_patterns)}.",
                         details={"matched_patterns": injection.matched_patterns, "blocked": True}, project_id=req.project_id)
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
            record_event(db, event_type=REQUEST_BLOCKED, severity="low", category="rate_limit", source="proxy",
                         application=req.operation, summary="Per-session call limit reached.", project_id=req.project_id)
            return JSONResponse(
                status_code=429,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="rate_limit_exceeded", message="Per-session call limit reached."),
                ).model_dump(),
            )

        # D-041: an explicit provider_config picks one named, non-fallback
        # provider (BYOK-capable). No config means the existing default
        # (Groq-primary/Gemini-fallback, server keys) — unchanged behavior.
        active_provider = provider
        if req.provider_config and req.provider_config.provider:
            active_provider = build_provider(req.provider_config.provider, req.provider_config.api_key)

        start = time.monotonic()
        try:
            llm_resp = active_provider.generate(req.messages)
        except MissingCredentialsError as exc:
            _log(db, req, empty_usage, guardrails, "provider_credentials_missing")
            return JSONResponse(
                status_code=400,
                content=GenerateResponse(
                    output=None,
                    guardrails=guardrails,
                    usage=empty_usage,
                    error=ErrorDetail(code="provider_credentials_missing", message=str(exc)),
                ).model_dump(),
            )
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
        if pii_resp.found:
            record_event(db, event_type=POLICY_VIOLATION,
                         severity="high" if "api_key" in pii_resp.types else "medium",
                         category="sensitive_information_disclosure", source="proxy",
                         application=req.operation, model=llm_resp.model,
                         summary=f"Model output contained: {', '.join(pii_resp.types)}.",
                         details={"types": pii_resp.types, "provider": llm_resp.provider}, project_id=req.project_id)
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
