from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """SQLite drops tzinfo, so rows came back naive and the web read them as
    *local* time (D-051). Store naive UTC, always return tz-aware UTC — every
    serialized timestamp then carries +00:00. Naive input is treated as UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


class User(Base):
    """Phase 2 (D-055): account. Password is bcrypt-hashed (proxy/auth.py) —
    never stored or logged in plaintext, never returned by any endpoint."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))


class Workspace(Base):
    """Phase 2 (D-055): one per user, auto-created on signup. Spec_V3.md's
    User→Workspace→Project hierarchy without building cross-user workspace
    sharing, which nothing in Phase 2 asks for (YAGNI — add a membership
    table later if/when multi-user workspaces are actually needed)."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))


class Project(Base):
    """Phase 2 (D-055): an AI system under assessment. `target_type` matches
    spec_V3.md §10's onboarding choices."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    target_type: Mapped[str] = mapped_column(String, default="model")  # model|application|agent|api|service
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    operation: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    guardrails: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))


class Finding(Base):
    """Phase 5 (D-044): a persisted security finding, generated from a FAIL
    proxy/engine TestResult. Rows are never deleted on resolution (spec:
    "Do not delete historical security evidence when a finding is resolved")
    — only `status`/`updated_at` change."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    test_id: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    affected_target: Mapped[str] = mapped_column(String)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    reproduction: Mapped[dict] = mapped_column(JSON, default=dict)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class TestRunResult(Base):
    """Phase 6 (D-045): one row per security-test outcome, every time
    `POST /v1/findings/sync` runs the suite — unlike `Finding` (FAIL only),
    this logs every status so the dashboard has real history/counts to show,
    not just current failures. `run_id` groups all rows from one sync call
    (used for "most recent run" totals and, later, Phase 7 baseline comparison)."""

    __tablename__ = "test_run_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    test_id: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    executed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AgentActionLog(Base):
    """Phase 9 (D-048): one row per agent action request evaluated by the
    policy layer — agent, tool, requested action, policy decision, and the
    policy-layer outcome. SentinelAI never executes the tool, so
    `execution_result` is one of: blocked / allowed_not_executed /
    pending_approval / approved_not_executed / rejected."""

    __tablename__ = "agent_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    tool: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    data_source: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    execution_result: Mapped[str] = mapped_column(String)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class SecurityEvent(Base):
    """Phase 11 (D-050): a security *observation* — attack attempt, blocked
    request, policy violation, finding opened, regression, suspicious tool
    activity. Deliberately separate from `Finding`: no status workflow, not a
    vulnerability. Metadata only — never raw prompt/response text."""

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String)
    application: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Baseline(Base):
    """Phase 7 (D-046): a named security baseline pinned to one
    TestRunResult.run_id. Later runs are compared against it. The baseline
    stores only the pointer — the underlying per-test rows stay in
    test_run_results, so individual results remain accessible."""

    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc))
