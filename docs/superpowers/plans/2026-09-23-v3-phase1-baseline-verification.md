# V3 Phase 1 — Baseline and Architecture Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/SENTINEL_V3_BASELINE.md`, an accurate inventory of every V3-relevant subsystem as it exists today, plus an explicit gap list against `spec_V3.md`'s requirements — with zero application-behavior changes, per spec_V3.md §67 Phase 1 ("Do not modify application behavior unless required to fix a clearly identified V3 blocker").

**Architecture:** Read-only inspection across the repo (`proxy/`, `gateway/`, `agents/`, `web/`, `tests/`, `deploy/`, `docs/`, `CLAUDE.md`, `state.md`, `decision.md`) and one existing DB (`proxy/db/models.py`). No new code, no schema changes, no new endpoints. Each task inspects one V3-required subsystem and writes its section into the baseline doc; the final task runs the full existing test suite unmodified to prove nothing broke and assembles the gap list.

**Tech Stack:** Existing stack only (Python/FastAPI/SQLAlchemy/SQLite, Next.js/TypeScript) — this phase adds no dependencies.

**Spec:** `spec_V3.md` (full V3 roadmap; this plan implements only §67 Phase 1) and `spec_V3.md` §4 (Existing Functionality Is Protected — the inventory this phase produces).

## Global Constraints

- Do not modify application behavior in this phase unless fixing a clearly identified V3 blocker (spec_V3.md §67 Phase 1) — none is anticipated; if one is found, stop and flag it rather than fixing it inline.
- Do not begin Phase 2 or any later phase (spec_V3.md §66, §72).
- Never place real credentials into docs, fixtures, or this plan (spec_V3.md §57).
- The existing test suite must still pass unmodified at the end of this phase (spec_V3.md §67 acceptance: "tests run").
- Follow CLAUDE.md's existing interpretation precedence (explicit instruction → original spec → decision.md → spec.md → tested implementation → other docs → general assumptions) if any conflict surfaces between spec_V3.md and the current SentinelAI-only-focus decision (D-040, project_1 CLAUDE.md).

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/SENTINEL_V3_BASELINE.md` | New. The single deliverable — one section per inspected subsystem, plus a final gap-analysis section. Built incrementally, one section appended per task. |

No other files are created or modified by this plan. This phase is additive-only (one new doc).

---

### Task 1: Repository, architecture, and database baseline

**Files:**
- Create: `docs/SENTINEL_V3_BASELINE.md`
- Read: `README.md`, `state.md`, `decision.md`, `docs/SECURITY_ENGINE.md`, `docs/GATEWAY.md`, `proxy/db/models.py`, `proxy/config.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `docs/SENTINEL_V3_BASELINE.md` exists with an `## Executive Summary`, `## Repository Structure`, `## Architecture`, and `## Database / Storage` section. Later tasks append further `##` sections to this same file — they must not overwrite it.

- [ ] **Step 1: Read the current project-memory files**

Read `README.md`, `state.md`, and `decision.md` in full. These already contain an accurate, dated summary of every phase built (D-040 through D-052) — do not re-derive this from scratch, cite it.

- [ ] **Step 2: Read the database schema**

Read `proxy/db/models.py` in full. List every table (`CallLog`, `Finding`, `TestRunResult`, `AgentActionLog`, `SecurityEvent`, `Baseline`) with its columns and purpose.

- [ ] **Step 3: Write the file**

Create `docs/SENTINEL_V3_BASELINE.md`:

```markdown
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
  regression (`regression.py`), monitoring events (`events.py`), reports
  (`reports.py`), agent tool-policy (`agent_policy.py`, `agent_actions.py`).
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

[Paste the ASCII diagram from README.md's "Architecture" section here
verbatim, then add:] This is a single control plane with no execution-plane
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
```

- [ ] **Step 4: Verify the file renders as valid Markdown**

Open `docs/SENTINEL_V3_BASELINE.md` and confirm every `##` heading is present and every code block is closed. No automated check applies to a doc file — visual confirmation is the verification for this step.

- [ ] **Step 5: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: start V3 Phase 1 baseline (architecture, repo structure, database)"
```

---

### Task 2: Authentication and authorization baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Authentication` and `## Authorization` sections)
- Read: `proxy/main.py`, `gateway/main.py`, every file under `proxy/` matching `*auth*`, `*session*`, `*login*` (expected: none found)

**Interfaces:**
- Consumes: `docs/SENTINEL_V3_BASELINE.md` from Task 1.
- Produces: `## Authentication` and `## Authorization` sections appended.

- [ ] **Step 1: Search for any existing auth code**

Run:

```bash
grep -rniE "login|signup|sign_up|session|jwt|oauth|password|bcrypt|passlib" proxy/ gateway/ agents/ web/lib web/app --include="*.py" --include="*.ts" --include="*.tsx" -l
```

Expected: no matches (or only false positives like "session_id" which is a per-call correlation string, not an auth session). Record the exact command output in the doc.

- [ ] **Step 2: Confirm no auth middleware runs**

Read `proxy/main.py`'s `app.add_middleware(...)` call (CORS only) and confirm there is no auth dependency on any route. Read `gateway/main.py` for the same.

- [ ] **Step 3: Append the sections**

```markdown
## Authentication

**None exists.** No signup, login, logout, session, password hashing, JWT,
or OAuth code anywhere in the repository (confirmed via
`grep -rniE "login|signup|session|jwt|oauth|password" proxy/ gateway/ agents/ web/` —
only false-positive matches on `session_id`, a per-request correlation
string unrelated to authentication). Every endpoint in `proxy/main.py` and
`gateway/main.py` is open to any caller that can reach the port.

## Authorization

**None exists.** There is no user identity, so there is no concept of
"authorized project access" to test. `ALLOWED_ORIGINS` (CORS) restricts
which *browser origins* may call the API — it is not authorization, it does
not restrict *who* behind an allowed origin can act, and it does nothing
for server-to-server/API/CI callers.
```

- [ ] **Step 4: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — authentication and authorization"
```

---

### Task 3: Project/workspace model baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Project / Workspace Model`)
- Read: `proxy/schemas.py`, `proxy/db/models.py` (re-confirm no `project_id`/`workspace_id`/`user_id` column exists anywhere)

**Interfaces:**
- Consumes: Task 1's DB section.
- Produces: `## Project / Workspace Model` section appended.

- [ ] **Step 1: Confirm no project/workspace concept exists in code**

```bash
grep -rniE "workspace|project_id|tenant" proxy/db/models.py proxy/schemas.py
```

Expected: no matches. `operation` (in `GenerateRequest`/`CallLog`) is a fixed enum (`extract|policy_check|report|playground`) — a call-purpose label, not a project identifier.

- [ ] **Step 2: Append the section**

```markdown
## Project / Workspace Model

**None exists.** SentinelAI is a single global instance: one proxy, one
database, no `User`/`Workspace`/`Project` table or foreign key anywhere in
`proxy/db/models.py`. The closest existing concept is `GenerateRequest.operation`
(`extract|policy_check|report|playground`), a fixed label describing the
*kind* of call, not an isolated tenant/project. All findings, test runs,
events, and baselines are global — every caller sees every row.
```

- [ ] **Step 3: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — project/workspace model"
```

---

### Task 4: Security engine, findings, remediation, dashboard baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Security Engine`, `## Findings`, `## Remediation`, `## Dashboard`)
- Read: `docs/SECURITY_ENGINE.md`, `docs/FINDINGS.md`, `docs/SECURITY_DASHBOARD.md`, `proxy/engine/models.py`, `proxy/remediation.py`

**Interfaces:**
- Consumes: nothing new (independent inspection).
- Produces: four sections appended.

- [ ] **Step 1: Read the existing docs for these subsystems**

Read `docs/SECURITY_ENGINE.md`, `docs/FINDINGS.md`, and `docs/SECURITY_DASHBOARD.md` in full — these already document the current implementation accurately; this task summarizes and maps them against spec_V3.md §15-18, §21, §26-27, not re-documents from scratch.

- [ ] **Step 2: Read the remediation module**

Read `proxy/remediation.py`. Confirm it is static per-category text (`REMEDIATION: dict[str, str]`), not project-aware or AI-generated.

- [ ] **Step 3: Append the sections**

```markdown
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
status, created_at/updated_at, remediation. **Missing against spec_V3.md
§17**: no `project` field (no project model exists at all — see Task 3), no
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
Task 3), no unified single-project overview page combining posture +
findings + recommendations + recent assessments in one view (spec_V3.md
§27) — today these are separate pages (Security dashboard, Findings,
Monitoring) rather than one project-scoped overview. No Integrations page
(spec_V3.md §56) — no SDK/CLI/credential concept exists to display (see
Task 6).
```

- [ ] **Step 4: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — security engine, findings, remediation, dashboard"
```

---

### Task 5: Provider abstraction and BYOK baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Provider Abstraction and BYOK`)
- Read: `docs/PROVIDERS.md`, `proxy/provider.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `## Provider Abstraction and BYOK` section appended.

- [ ] **Step 1: Read the existing provider doc and code**

Read `docs/PROVIDERS.md` in full and `proxy/provider.py`'s `PROVIDER_REGISTRY`, `build_provider`, `MissingCredentialsError`.

- [ ] **Step 2: Append the section**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — provider abstraction and BYOK"
```

---

### Task 6: SDK/CLI, API integration, and CI/CD baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## SDK / CLI`, `## API Integration`, `## CI/CD Integration`)
- Read: `docs/CI_CD.md`, `scripts/sentinel_ci.py`, `proxy/ci.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: three sections appended.

- [ ] **Step 1: Confirm no installable SDK/CLI package exists**

```bash
find . -maxdepth 1 -iname "setup.py" -o -maxdepth 1 -iname "pyproject.toml"
grep -n "console_scripts\|entry_points" requirements.txt 2>/dev/null
```

Expected: no `pyproject.toml`/`setup.py` at repo root defining an installable package or CLI entry point. `scripts/sentinel_ci.py` is run as `python -m scripts.sentinel_ci`, not an installed `sentinel` command.

- [ ] **Step 2: Read the existing CI doc**

Read `docs/CI_CD.md` in full.

- [ ] **Step 3: Append the sections**

```markdown
## SDK / CLI

**No installable package exists.** `scripts/sentinel_ci.py` is the closest
equivalent — an HTTP-calling script (`python -m scripts.sentinel_ci
--target <url>`), not a `pip install`-able SDK or a `sentinel` CLI binary.
It has no `sentinel init`/project-association workflow (spec_V3.md §34) —
it takes a bare `--target` URL per invocation with no persisted local
config, and no auth step (there is nothing to authenticate against — see
Task 2).

## API Integration

`proxy/main.py` and `gateway/main.py` are themselves the API — every
endpoint (`/v1/generate`, `/v1/security-tests/run`, `/v1/findings/*`,
`/v1/baselines`, `/v1/regression-report`, `/v1/events*`, `/v1/agents/*`,
`/v1/reports/*`, `/v1/gateway/chat`) is reachable by anyone who can reach
the port, satisfying none of spec_V3.md §36's authentication/authorization/
project-isolation/rate-limiting/audit-logging requirements except partial
input validation (Pydantic request models) and the proxy's own per-session
rate limiter (`check_and_increment`, session-scoped, not identity-scoped —
a caller can reset by changing `session_id`).

## CI/CD Integration

Strong match to spec_V3.md §37: `scripts/sentinel_ci.py` already supports
selecting a category/suite (`--category`), executing tests, machine-readable
(`--json-out`) and human-readable (`--md-out`, stdout) output, configurable
non-hardcoded pass/fail policy (`proxy/ci.py::CIPolicy`), and regression
detection (`--check-regression` against `/v1/regression-report`). Documented
in `docs/CI_CD.md` with a working `.github/workflows/security-tests.yml`.
**Gap**: "selecting project" (spec_V3.md §37) has no meaning yet — there is
one global target, not a project to select.
```

- [ ] **Step 4: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — SDK/CLI, API integration, CI/CD"
```

---

### Task 7: Reports, monitoring, local/cloud mode, and existing test coverage baseline

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Reports`, `## Monitoring`, `## Local-Only vs Cloud-Connected Mode`, `## Existing Test Coverage`)
- Read: `docs/REPORTS.md`, `docs/MONITORING.md`, `proxy/reports.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: four sections appended.

- [ ] **Step 1: Read the existing reports and monitoring docs**

Read `docs/REPORTS.md` and `docs/MONITORING.md` in full.

- [ ] **Step 2: Count existing tests**

```bash
.venv\Scripts\python -m pytest tests/ --collect-only -q | tail -5
```

Record the exact collected-test count in the doc (do not estimate).

- [ ] **Step 3: Append the sections**

```markdown
## Reports

`proxy/reports.py` builds executive and technical reports (spec_V3.md §40)
from stored data only, with `scrub()` removing configured provider keys and
PII before output — satisfies spec_V3.md §41's "no secrets in any report
format" for the JSON/Markdown formats it supports today. **Gap against
spec_V3.md §41**: no PDF or CSV format exists, only JSON and Markdown.
**Gap against spec_V3.md §42**: report scope is implicitly global
(`since`/`until` time-range only) — there is no "single target" or "single
project" scope option because no target/project model exists (see Task 3).

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

[Paste the exact `pytest --collect-only -q` tail output here, e.g. "318
tests collected"]. Coverage spans: guardrails (injection/PII), provider
abstraction/BYOK, security engine + all 5 attack categories, findings,
dashboard, regression, CI policy, agent tool-policy (including bypass
attempts), monitoring events, reports, gateway pipeline, and a UTC-timestamp
regression guard. **Gap against spec_V3.md §58-59**: zero tests exist for
signup/login/logout/session expiration, authorized-vs-unauthorized project
access, or cross-project access attempts — because none of those concepts
exist yet (Tasks 2-3). These become required only once Phase 2 introduces
auth/projects; they are not a Phase 1 defect.
```

- [ ] **Step 4: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md
git commit -m "docs: V3 Phase 1 baseline — reports, monitoring, mode, test coverage"
```

---

### Task 8: Gap analysis, run full suite, final acceptance check

**Files:**
- Modify: `docs/SENTINEL_V3_BASELINE.md` (append `## Gap Analysis Summary` and `## Phase 1 Acceptance`)
- Modify: `state.md` (append a dated note pointing at the new baseline doc, per CLAUDE.md §15 session handoff)

**Interfaces:**
- Consumes: every prior task's section (this task synthesizes, adds nothing new to inspect).
- Produces: the finished `docs/SENTINEL_V3_BASELINE.md`; an updated `state.md`.

- [ ] **Step 1: Run the full existing test suite unmodified**

```bash
.venv\Scripts\python -m pytest tests/ -q
```

Expected: same pass/skip count as before this plan started (no test was touched by Tasks 1-7 — they only created/appended to a doc). Record the exact final line (`N passed, M skipped, ...`) in the doc.

- [ ] **Step 2: Run the web checks unmodified**

```bash
cd web
npx tsc --noEmit -p tsconfig.json
npm run test
```

Expected: clean typecheck, same vitest pass count as before. Record the exact vitest summary line in the doc.

- [ ] **Step 3: Write the Gap Analysis Summary**

```markdown
## Gap Analysis Summary

Ranked by how much of spec_V3.md's Phase 2+ work depends on it:

1. **No authentication** (Task 2) — blocks all of spec_V3.md §7-11, §54-55,
   and every "authorized"/"unauthorized" acceptance criterion in §68.
   Everything else in V3 is gated behind this existing first.
2. **No project/workspace model** (Task 3) — blocks §8-11, §14 (target
   model needs a project to belong to), §26-27 (project-scoped dashboard),
   §29 (remediation center needs project filter), §40-42 (project-scoped
   reports), and the isolation tests §9/§59 require.
3. **No target model** (folded into Task 3's finding) — `GenerateRequest.operation`
   is not a target; spec_V3.md §14's target metadata (environment,
   connection method, status) has no home yet.
4. **No installable SDK/CLI or project-association credentials** (Task 6) —
   blocks §34-35 and the "Local SDK" execution-source leg of §33/§39.
5. **No scoped API credentials** (Task 6 / spec_V3.md §35-36) — every
   caller today is equally (un)privileged; there is no revocable,
   project-scoped token to build §36's API integration story on.
6. **Remediation is static, not project-aware** (Task 4) — spec_V3.md §20-25's
   core V3 value proposition (project-specific recommendations,
   confidence, fact/analysis/recommendation separation) does not exist yet;
   today's `remediation_for(category)` is a fixed lookup table.
7. **Finding schema is missing a few V3 fields** (Task 4) — `project`,
   explicit `impact`, `likely_root_cause`, `affected file/path`,
   `assessment/run ID` on the row itself. Additive columns, not a breaking
   change, once a project model exists to reference.
8. **No PDF/CSV report formats** (Task 7) — smaller gap, additive.

None of these gaps require touching working code in Phase 1 — spec_V3.md
§67 Phase 1 is explicitly inspection-only. They define the shape of Phase 2
onward and should inform, not preempt, that planning.

## Phase 1 Acceptance

Per spec_V3.md §67 Phase 1 acceptance criteria:

- [x] Existing functionality documented (this file).
- [x] Architecture understood (Architecture, Database sections above).
- [x] Tests run: `<paste the exact pytest summary line from Step 1>`;
      web: `<paste the exact vitest summary line from Step 2>`.
- [x] Known gaps identified (Gap Analysis Summary above).

No application behavior was changed to produce this baseline.
```

- [ ] **Step 4: Update state.md**

Add one dated line near the top of `state.md`'s "Current State" section: `**V3 Phase 1 baseline:** completed 2026-09-23, see docs/SENTINEL_V3_BASELINE.md — active phase is spec_V3.md Phase 1, NOT STARTED → COMPLETE, awaiting user approval to begin Phase 2.` Do not otherwise restructure `state.md`.

- [ ] **Step 5: Commit**

```bash
git add docs/SENTINEL_V3_BASELINE.md state.md
git commit -m "docs: complete V3 Phase 1 baseline — gap analysis and acceptance"
```

- [ ] **Step 6: Stop**

Per spec_V3.md §66/§72: do not begin Phase 2. Report the completed baseline and gap analysis to the user and wait for explicit approval before any further V3 work.

---

## Self-Review

**Spec coverage:** spec_V3.md §67 Phase 1 lists 14 inspection areas (repository, architecture, database, authentication, project model, dashboard, security engine, findings, remediation, reports, API, SDK/CLI, provider integrations, tests) — all 14 are covered across Tasks 1-7, plus Task 8 adds the required gap analysis and acceptance check. §4's inventory list (auth, dashboard, navigation, tests, model integrations, provider handling, BYOK, managed inference, findings, evidence, reports, project handling, API, SDK, CLI, database/storage, local execution, cloud functionality, integrations, existing tests) is covered by the same tasks — "evidence" is covered within Task 4's Findings section (`Finding.evidence`), "navigation" within Task 4's Dashboard section, "integrations" within Task 6.

**Placeholder scan:** every code block above is either an exact command to run or exact Markdown content to write; the two bracketed instructions (`[Paste the ASCII diagram...]`, `[Paste the exact pytest --collect-only...]`, `<paste the exact pytest summary line...>`) are explicit "copy this real output in" instructions, not unresolved TODOs — the source (README.md's Architecture section, the command's own stdout) is named exactly.

**Type consistency:** not applicable — this plan produces only Markdown, no functions/types are defined across tasks.
