# Sentinel V3 Baseline — Phase 1 Inventory

Compiled: 2026-09-23, per spec_V3.md §67 Phase 1. Read-only inspection —
no application behavior changed to produce this document.

## Executive Summary

SentinelAI today is a **single-tenant, unauthenticated, local-first**
FastAPI security-testing platform: one proxy process, one SQLite database,
no user accounts, no workspace/project model, no SDK/CLI package. Fraud
Copilot (the original application layer) is paused (D-040). Every
capability spec_V3.md asks for in Phase 1's scope — auth, multi-project
isolation, SDK/CLI, managed inference — is either entirely absent or
present only as a single-tenant equivalent. This is not a V3 upgrade of an
existing multi-tenant product; it is a foundational build-out. See the Gap
Analysis section below.

## Repository Structure

- `proxy/` — SentinelAI core: guardrails (`main.py`), provider abstraction
  (`provider.py`), security engine (`engine/`), findings (`findings.py`),
  regression (`regression.py`), monitoring events (`events.py`), agent tool-policy (`agent_policy.py`, `agent_actions.py`).
- `gateway/` — separate stateless FastAPI service (D-049), same guardrails
  reused as a library.
- `agents/`, `frontend/` — Fraud Copilot (paused, D-040), kept on disk.
- `web/` — Next.js dashboard: Playground, Security Tests, Findings,
  Regression, Monitoring, Agent Security, Reports, (Eval) Dashboard.
- `deploy/render.yaml` — two Render web services (proxy, gateway), no auth
  layer, no per-tenant provisioning.
- `tests/` — pytest suite, no per-user/per-project authorization tests
  exist because there is no user/project concept yet.

## Architecture

```text
                    ┌──────────────────────────┐
                    │   Next.js UI (web/)       │
                    │ playground / review /     │
                    │ dashboard                 │
                    └──────────┬───────────────┘
                               │
                 ┌─────────────┴──────────────┐
                 │                            │
          Red-team prompt              Fraud Copilot
                 │                     LangGraph agents
                 │                            │
                 └─────────────┬──────────────┘
                               │ LLM calls only
                     ┌─────────▼─────────┐
                     │ SentinelAI Proxy  │
                     │ FastAPI           │
                     ├───────────────────┤
                     │ Injection         │
                     │ PII/secrets      │
                     │ Schema validation │
                     │ Rate limiting     │
                     │ LLM provider      │
                     │ Hallucination     │
                     │ Logging           │
                     └─────────┬─────────┘
                               │
                         Groq / Gemini
```

This is a single control plane with no execution-plane
split — the proxy IS both the API surface and the only "dashboard backend."
There is no separate control-plane/execution-plane distinction as
spec_V3.md §5 describes; `web/` calls `proxy/`'s and `gateway/`'s endpoints
directly, unauthenticated.

## Database / Storage

SQLite (`DATABASE_URL`), single file, no per-tenant partitioning. Tables
(from `proxy/db/models.py`):

- `call_logs` (`CallLog`) — every `/v1/generate` call: session_id,
  operation, provider, model, latency/tokens/cost, guardrails JSON,
  error_code, created_at. No `user_id`/`project_id` column.
- `findings` (`Finding`) — test_id, category, severity, title, description,
  affected_target, evidence JSON, reproduction JSON, provider, model,
  status, created_at, updated_at. No `project_id`.
- `test_run_results` (`TestRunResult`) — run_id, test_id, category,
  severity, status, provider, model, executed_at. No `project_id`.
- `agent_action_logs` (`AgentActionLog`) — agent_id, tool, action,
  data_source, decision, reason, execution_result, approved_by,
  created_at, updated_at.
- `security_events` (`SecurityEvent`) — event_type, severity, category,
  source, application, model, summary, details JSON, created_at.
- `baselines` (`Baseline`) — name, run_id, created_at.

Every table's rows are globally visible to whoever can reach the API —
there is no row-level isolation because there is no tenant/user/project
identity anywhere in the schema.

## Authentication

**None exists.** No signup, login, logout, session, password hashing, JWT,
or OAuth code anywhere in the repository (confirmed via
`grep -rniE "login|signup|sign_up|session|jwt|oauth|password|bcrypt|passlib" proxy/ gateway/ agents/ web/lib web/app --include="*.py" --include="*.ts" --include="*.tsx"`
— only false-positive matches on `session_id`, a per-request correlation
string unrelated to authentication, and `get_session()`/`session.py` which
are SQLAlchemy database-session utilities). Every endpoint in `proxy/main.py`
and `gateway/main.py` is open to any caller that can reach the port.

## Authorization

**None exists.** There is no user identity, so there is no concept of
"authorized project access" to test. `ALLOWED_ORIGINS` (CORS) restricts
which *browser origins* may call the API — it is not authorization, it does
not restrict *who* behind an allowed origin can act, and it does nothing
for server-to-server/API/CI callers.
