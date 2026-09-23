# Sentinel V3 Baseline — Phase 1 Inventory

Compiled: 2026-09-23, per spec_V3.md §67 Phase 1. Read-only inspection —
no application behavior changed to produce this document.

## Executive Summary

SentinelAI today is a **single-tenant, unauthenticated, local-first**
FastAPI security-testing platform: one proxy process, one SQLite database,
no user accounts, no workspace/project model, no SDK/CLI package. Fraud
Copilot (the original application layer) is paused (D-040). Every
V3 capability this baseline inspects — auth, multi-project
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

## Project / Workspace Model

**None exists.** SentinelAI is a single global instance: one proxy, one
database, no `User`/`Workspace`/`Project` table or foreign key anywhere in
`proxy/db/models.py`. The closest existing concept is `GenerateRequest.operation`
(`extract|policy_check|report|playground`), a fixed label describing the
*kind* of call, not an isolated tenant/project. All findings, test runs,
events, and baselines are global — every caller sees every row.

## Security Engine

Matches spec_V3.md §15's TEST DEFINITION → EXECUTION → EVALUATION → FINDING
→ EVIDENCE separation closely (`proxy/engine/models.py`: `SecurityTest`,
`RawExecution`, `TestResult`). Missing from spec_V3.md's chain: no
"REMEDIATION RECOMMENDATION" step in the engine itself — remediation is
generated separately, after the fact, from `Finding.category`
(see Remediation below). `TestStatus` already has all 5 states
(PASS/FAIL/ERROR/NOT_RUN/INCONCLUSIVE, spec_V3.md §16) — `NOT_RUN` is
defined but never actually assigned anywhere (every registered test always
executes when the suite runs one). Reproducibility exists via
`TestResult.reproduction` (test_id + provider/model), matching spec_V3.md
§15's requirement.

## Findings

`Finding` (`proxy/db/models.py`) already covers most of spec_V3.md §17's
field list: id, test_id (→ "test ID"), category, severity, title,
description, affected_target, evidence, reproduction, provider/model,
status, created_at/updated_at, plus remediation (computed at serialization
via `remediation_for()`, not a stored column). **Missing against spec_V3.md
§17**: no `project` field (no project model exists at all — see Project /
Workspace Model above), no
explicit `impact` field (folded into `description`), no `likely_root_cause`
field distinct from `description`, no `affected file/path` field, no
`assessment/run ID` field on the Finding row itself (it exists only
indirectly via the originating `TestRunResult.run_id`, not stored on
`Finding`). Status model (`OPEN`/`ACKNOWLEDGED`/`RESOLVED`/`RETEST_REQUIRED`)
differs from spec_V3.md §18's `OPEN`/`IN_PROGRESS`/`RESOLVED`/`ACCEPTED_RISK`
— overlapping concepts, different vocabulary, would need an explicit
decision to reconcile (CLAUDE.md's decision-log workflow, not a silent rename).

## Remediation

`proxy/remediation.py::remediation_for(category)` is a **static
category→text lookup**, not project-aware. It does not use spec_V3.md
§20's project architecture/framework/tool-definition context (none of that
context exists without a project model), does not distinguish
Observed/Analysis/Recommendation (spec_V3.md §23), and has no confidence
categorization (spec_V3.md §24). It satisfies "a finding has remediation
guidance" at the most basic level and nothing further in spec_V3.md
§21/§25.

## Dashboard

`web/app/{security,findings,regression,monitoring,agents,reports,dashboard}`
exist and are wired to real (non-fake) data per D-045's "no fake metrics"
rule, satisfying spec_V3.md §60 for what exists today. **Missing against
spec_V3.md §26**: no project switcher (no projects to switch between — see
Project / Workspace Model above), no unified single-project overview page combining posture +
findings + recommendations + recent assessments in one view (spec_V3.md
§27) — today these are separate pages (Security dashboard, Findings,
Monitoring) rather than one project-scoped overview. No Integrations page
(spec_V3.md §56) — no SDK/CLI/credential concept exists to display (see
SDK / CLI above).

## Provider Abstraction and BYOK

Matches spec_V3.md §12-13 well at the mechanism level: `PROVIDER_REGISTRY`
(`proxy/provider.py`) keeps the security engine provider-agnostic (spec_V3.md
§13), and `GenerateRequest.provider_config.api_key` already implements
per-request BYOK — server-side only, never logged, `MissingCredentialsError`
raised before any SDK/network call (satisfies spec_V3.md §12's BYOK
credential rules). **Gap against spec_V3.md §12**: "Sentinel-managed
inference" as a *user-facing choice* doesn't exist as a concept, because
there is no user/account to own a choice between BYOK and managed — today
there is only one mode: the server's own `.env` keys are the implicit
default, indistinguishable from a notional "managed" tier since there is no
tiering, billing, or per-user quota.

## SDK / CLI

**No installable package exists.** `scripts/sentinel_ci.py` is the closest
equivalent — an HTTP-calling script (`python -m scripts.sentinel_ci
--target <url>`), not a `pip install`-able SDK or a `sentinel` CLI binary.
It has no `sentinel init`/project-association workflow (spec_V3.md §34) —
it takes a bare `--target` URL per invocation with no persisted local
config, and no auth step (there is nothing to authenticate against — see
Authentication above).

## API Integration

`proxy/main.py` and `gateway/main.py` are themselves the API — every
endpoint (`/health`, `/quota`, `/v1/generate`, `/v1/security-tests/run`,
`/v1/findings`, `/v1/findings/{finding_id}`, `/v1/findings/sync`,
`/v1/baselines`, `/v1/regression-report`, `/v1/events`,
`/v1/events/config`, `/v1/events/retention/apply`, `/v1/agents`,
`/v1/agents/{agent_id}/evaluate`, `/v1/agent-actions`,
`/v1/agent-actions/{log_id}/approve`, `/v1/agent-actions/{log_id}/reject`,
`/v1/reports/executive`, `/v1/reports/technical`, `/v1/security-dashboard`,
`/v1/calls`, `/v1/gateway/chat`) is reachable by anyone who can reach
the port, satisfying none of spec_V3.md §36's authentication/authorization/
project-isolation/rate-limiting/audit-logging requirements except partial
input validation (Pydantic request models), the proxy's own per-session
rate limiter (`check_and_increment`, session-scoped, not identity-scoped —
a caller can reset by changing `session_id`), and a partial audit trail via
`call_logs`/`agent_action_logs` (the latter including an `approved_by`
field) — though full compliance with §44's audit-trail requirements was not
separately inspected here.

## CI/CD Integration

Strong match to spec_V3.md §37: `scripts/sentinel_ci.py` already supports
selecting a category/suite (`--category`), executing tests, machine-readable
(`--json-out`) and human-readable (`--md-out`, stdout) output, configurable
non-hardcoded pass/fail policy (`proxy/ci.py::CIPolicy`), and regression
detection (`--check-regression` against `/v1/regression-report`). Documented
in `docs/CI_CD.md` with a working `.github/workflows/security-tests.yml`.
**Gap**: "selecting project" (spec_V3.md §37) has no meaning yet — there is
one global target, not a project to select.

## Reports

`proxy/reports.py` builds executive and technical reports (spec_V3.md §40)
from stored data only, with `scrub()` removing configured provider keys and
PII before output — satisfies spec_V3.md §41's "no secrets in any report
format" for the JSON/Markdown formats it supports today. **Gap against
spec_V3.md §41**: no PDF or CSV format exists, only JSON and Markdown.
**Gap against spec_V3.md §42**: report scope is implicitly global
(`since`/`until` time-range only) — there is no "single target" or "single
project" scope option because no target/project model exists (see Project /
Workspace Model above).

## Monitoring

`SecurityEvent` (spec_V3.md §43's EVENT) is already a model distinct from
`TestRunResult` (TEST RESULT) and `Finding` (FINDING) — the three-way
distinction spec_V3.md §43 asks for already exists and is enforced (an
attack attempt never auto-creates a Finding; D-050). Filtering by time,
severity, application, model, category, event type exists
(`GET /v1/events`). No "trends" visualization exists yet (spec_V3.md §11
mentions trends only loosely; not a hard Phase 1 requirement).

## Local-Only vs Cloud-Connected Mode

**Not applicable in current form.** There is no "cloud" deployment of
SentinelAI as a multi-tenant service to be local-only *instead of* — the
existing local run and the existing Render deployment config
(`deploy/render.yaml`) are the same single-tenant software running in two
places, not two distinct modes a user chooses between with different sync
behavior (spec_V3.md §38-39 presume a multi-tenant cloud product with a
toggle against local execution, which does not exist yet).

## Existing Test Coverage

321 tests collected in 3.56s. Coverage spans: guardrails (injection/PII), provider
abstraction/BYOK, security engine + all 5 attack categories, findings,
dashboard, regression, CI policy, agent tool-policy (including bypass
attempts), monitoring events, reports, gateway pipeline, and a UTC-timestamp
regression guard. **Gap against spec_V3.md §58-59**: zero tests exist for
signup/login/logout/session expiration, authorized-vs-unauthorized project
access, or cross-project access attempts — because none of those concepts
exist yet (see Authentication and Project / Workspace Model above). These become required only once Phase 2 introduces
auth/projects; they are not a Phase 1 defect.

## Gap Analysis Summary

Ranked by how much of spec_V3.md's Phase 2+ work depends on it:

1. **No authentication** (see Authentication above) — blocks all of
   spec_V3.md §7-11, §54-55, and every "authorized"/"unauthorized"
   acceptance criterion in §68. Everything else in V3 is gated behind this
   existing first.
2. **No project/workspace model** (see Project / Workspace Model above) —
   blocks §8-11, §14 (target model needs a project to belong to), §26-27
   (project-scoped dashboard), §29 (remediation center needs project
   filter), §40-42 (project-scoped reports), and the isolation tests
   §9/§59 require.
3. **No control-plane/execution-plane split** (see Architecture above) —
   the proxy is a single control plane with no separate
   control-plane/execution-plane distinction as spec_V3.md §5 describes;
   `web/` calls `proxy/`'s and `gateway/`'s endpoints directly,
   unauthenticated. This blocks spec_V3.md §5-6 directly, and is the most
   directly Phase-2-relevant gap on this list — Phase 2 of spec_V3.md is
   itself titled "Control Plane and Multi-Project Verification."
4. **No target model** (folded into the Project / Workspace Model finding
   above) — `GenerateRequest.operation` is not a target; spec_V3.md §14's
   target metadata (environment, connection method, status) has no home
   yet.
5. **Finding status vocabulary mismatch** (see Findings above) — current
   status model (`OPEN`/`ACKNOWLEDGED`/`RESOLVED`/`RETEST_REQUIRED`)
   differs from spec_V3.md §18's `OPEN`/`IN_PROGRESS`/`RESOLVED`/
   `ACCEPTED_RISK` — overlapping concepts, different vocabulary, would
   need an explicit decision to reconcile.
6. **No installable SDK/CLI or project-association credentials** (see
   SDK / CLI above) — blocks §34-35 and the "Local SDK" execution-source
   leg of §33/§39.
7. **No scoped API credentials** (see SDK / CLI above / spec_V3.md
   §35-36) — every caller today is equally (un)privileged; there is no
   revocable, project-scoped token to build §36's API integration story on.
8. **Remediation is static, not project-aware** (see Remediation above) —
   spec_V3.md §20-25's core V3 value proposition (project-specific
   recommendations, confidence, fact/analysis/recommendation separation)
   does not exist yet; today's `remediation_for(category)` is a fixed
   lookup table.
9. **Finding schema is missing a few V3 fields** (see Findings above) —
   `project`, explicit `impact`, `likely_root_cause`, `affected file/path`,
   `assessment/run ID` on the row itself. Additive columns, not a breaking
   change, once a project model exists to reference.
10. **No local-only vs cloud-connected mode** (see Local-Only vs
    Cloud-Connected Mode above) — not applicable in the current
    single-tenant form; spec_V3.md §38-39 presume a multi-tenant product
    with a toggle against local execution that doesn't exist yet.
11. **No managed-inference choice** (see Provider Abstraction and BYOK
    above) — "Sentinel-managed inference" as a user-facing choice doesn't
    exist, since there is no user/account to own a choice between BYOK and
    managed inference.
12. **No unified project overview page or Integrations page** (see
    Dashboard above) — no project switcher, no single-project overview
    page combining posture + findings + recommendations (spec_V3.md §27),
    and no Integrations page (spec_V3.md §56).
13. **No PDF/CSV report formats** (see Reports above) — smaller gap,
    additive.

None of these gaps require touching working code in Phase 1 — spec_V3.md
§67 Phase 1 is explicitly inspection-only. They define the shape of Phase 2
onward and should inform, not preempt, that planning.

## Phase 1 Acceptance

Per spec_V3.md §67 Phase 1 acceptance criteria:

- [x] Existing functionality documented (this file).
- [x] Architecture understood (Architecture, Database sections above).
- [x] Tests run: `318 passed, 3 skipped`;
      web: `Test Files 3 passed (3), Tests 18 passed (18)`.
- [x] Known gaps identified (Gap Analysis Summary above).

No application behavior was changed to produce this baseline.
