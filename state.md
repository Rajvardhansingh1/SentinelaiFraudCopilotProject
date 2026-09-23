# Project State — SentinelAI + Fraud Copilot

This file is the current project memory. It should describe where a fresh agent must continue, not the entire historical story.

## Current State

**spec_V3.md Phases 1-3, 5, 8, 9, 12, 13:** DONE as of 2026-09-24 (D-055 through D-059), merged to `main`. Phases 4, 7, 10, 11's backend acceptance criteria are also satisfied (see below) — only Phase 6's dedicated "remediation center" UI page and Phase 7's before/after comparison UI remain unbuilt as of this note. User asked to "complete everything in spec_V3.md."

**Project:** SentinelAI + Fraud Copilot
**State date:** 2026-09-24
**Overall status:** All 7 original spec.md phases + Phase 8 done and REAL-verified. Fraud Copilot paused (D-040). SentinelAI platform: `phase_dev_upgrade.md` Phases 0-12 all DONE. spec_V3.md:
- Phase 1 (baseline docs) DONE.
- Phase 2 (auth + projects, D-055/D-056/D-059) DONE — stateless JWT auth, User→Workspace→Project model, global auth middleware, **every** subsystem project-scoped (generate, findings, dashboard, calls, baselines, regression, events, reports, agent actions), cross-project isolation covered by `tests/test_auth.py`, auth-endpoint rate limiting.
- Phase 3 (target/execution model, D-056) DONE — `Project.target_type` + `TestRunResult.execution_source`.
- Phase 4 (centralized execution/result sync) DONE — satisfied by Phase 2/3's auth+scoping+execution_source together; no separate work needed.
- Phase 5 (remediation intelligence, D-057) DONE — structured Observed/Analysis/Recommendation/Confidence object per finding, `proxy/remediation.py`.
- Phase 6 (finding/remediation UX) PARTIAL — finding detail page renders full structured remediation; no dedicated "remediation center" list page yet.
- Phase 7 (retesting/regression) PARTIAL — regression engine is fully project-scoped and API-key-accessible; no dedicated before/after comparison UI page yet (data is available via `/v1/regression-report`).
- Phase 8 (SDK/CLI/CI) DONE — `scripts/sentinel_ci.py` supports a persistent project-scoped API key (`--api-key`/`--project-id`) alongside the original one-off bootstrap.
- Phase 9 (API/service integrations, D-058) DONE — `ProjectAPIKey`, `Authorization: ApiKey`, scoped to `/v1/findings/sync` + `/v1/regression-report`.
- Phase 10 (reporting) DONE — project-scoped executive/technical reports in JSON/Markdown/CSV.
- Phase 11 (monitoring) DONE — events fully project-scoped.
- Phase 12 (hardening, D-059) DONE — auth-endpoint rate limiting added (was a real gap: zero limiting on signup/login before this); CORS/secret-handling/error-handling/report-scrubbing reviewed, no other gaps found requiring code changes.
- Phase 13 (final validation) DONE — `web/tests/e2e/full-journey.spec.ts`, a real Playwright test against a live proxy covering signup → create project → run assessment → findings → recommended solutions → generate report, passing.

**Current phase:** Frontend auth (login/signup/project-switcher) is built and live-verified end to end via Playwright against a real proxy. Web playground and all `web/lib/api.ts` calls send the bearer token + active `project_id`. Remaining open items: Phase 6's remediation-center list page, Phase 7's before/after comparison UI, and actual production deployment (Render/Supabase/Vercel accounts — code+config ready, no real credentials available to this session).
**Current spec:** See phase breakdown above. Nothing in spec_V3.md's 13 phases is unstarted; the two PARTIAL items are UI polish on top of fully-working, tested backends.
**Next executable step (updated after D-056 through D-059):** All work committed directly to `main` (no long-lived branch this round). Full backend suite: 360 passed, 3 skipped, 0 failed. Frontend: `tsc` clean, production build succeeds, 18 vitest unit tests pass, 4 Playwright e2e specs pass (1 skipped — paused Fraud Copilot review). If continuing: build the Phase 6 remediation-center page and Phase 7 before/after comparison page (both are UI-only; backend data already exists), or move to real deployment (create Supabase project, set Render secrets, deploy Vercel).

**Earlier next executable step (D-054, PII scanner CI-crash fix):** D-054: fixed a real, pre-existing production bug found while diagnosing a crashed GitHub Actions CI run — `check_pii()` was flagging ordinary location/date/nationality/URL mentions as PII (a fresh Presidio install correctly initializes and returns `LOCATION`-type entities for things like "France", which were never filtered), and `redact_pii()` was claiming `redacted=True` without actually stripping Presidio-only-detected spans (no regex pattern for e.g. a person's name). Both fixed in `proxy/middleware/pii_scanner.py`, 7 new deterministic tests in `tests/test_pii_scanner.py`. Verified against both the long-lived local venv and a freshly-installed venv matching CI's exact conditions — 325 passed/3 skipped, no regressions. Landed first on `main` since it unblocked CI everywhere; this branch and `worktree-v3-phase1-baseline` have both since merged it in.

**Next executable step (updated after D-053, Supabase migration):** D-053: production `DATABASE_URL` moves to Supabase Postgres (shared across `proxy`/`gateway`), connection string as a Render secret (`sync: false`), never committed, never touched by the CLI (already true, D-047). Real bug fixed: `proxy/db/session.py` was passing a SQLite-only `check_same_thread` connect arg unconditionally — would have crashed on `psycopg2`. Fixed + tested (`tests/test_db_backend_portability.py`). `psycopg2-binary` added to requirements.txt. `docs/SUPABASE.md` has setup/rollback. Local dev/tests still default to SQLite — no behavior change there. This is code+config+docs only — actually creating the Supabase project and pasting the real connection string into Render is the user's own next action (no real credentials available to this session). 320 passed/3 skipped (was 318, +2 new tests), no regressions. On a separate branch (`worktree-v3-phase1-baseline`) the V3 Phase 1 baseline doc work is done and its CI/merge is in flight independently — see that branch's own history, not this one's.

**Next executable step (updated after Phase 12 + cleanup):** Phases 2-12 of `phase_dev_upgrade.md` are DONE — the full document is implemented. D-051 fixed the naive-UTC timestamp display bug at the DB type layer (`UTCDateTime`, 8 columns). D-052 closed every open follow-up from Phases 8-11 (gateway in `deploy/render.yaml`, agent-security UI at `web/app/agents`, agent-policy-bypass engine plugin) and added Phase 12's executive/technical reports (`proxy/reports.py`, `GET /v1/reports/{executive,technical}`, `web/app/reports`) plus the `remediation` field on findings that Phase 5 originally asked for and had been missing. 318 passed/3 skipped (Python, stable across 3 runs), 18 vitest, `tsc` clean. Live-verified end to end: playground presets still blocked, benign prompt still answered by Groq, full sync→baseline→report cycle produced correct output with zero secret leakage. **No more phases left in phase_dev_upgrade.md** — remaining work is genuinely open-ended: real deployment (Render/Vercel accounts still needed), OD-018 (ELA, irrelevant while Fraud Copilot paused), or user-directed new scope.

**Earlier next-step note (Phase 11, kept for history):** Phases 2-11 DONE. Phase 11 (D-050): `SecurityEvent` table + `proxy/events.py`, emitters in proxy/findings-sync/regression/agent flows, optional gateway sink (off by default), `GET /v1/events` filters, retention + config controls, `web/app/monitoring`. 294 passed/3 skipped (Python), 18 vitest, `tsc` clean; playground presets re-verified live. Start Phase 12 next — reporting: executive report (scope, period, key findings, severity distribution, major changes, remediation status) + technical report (test cases, attack inputs, results, evidence, model/provider, timestamps, reproducibility, remediation), generated only from stored data, secrets never included. Open follow-ups: naive-UTC timestamp display offset across web pages (D-050), gateway block in `deploy/render.yaml`, agent-security UI + engine plugin (D-048).

**Earlier next-step note (Phase 10, kept for history):** Phases 2-10 DONE. Phase 10 (D-049): `gateway/` separate FastAPI service (port 8002) — stateless request/response inspection, `GATEWAY_*` server-side policy, provider routing, metadata-only audit events. Also fixed a Phase 2 UI regression (playground showed "Not blocked" for a 400 credentials error) and added `tests/test_playground_regression_guard.py` pinning the web presets + system prompt against the live detector. 268 passed/3 skipped (Python), 18 passed (vitest), `tsc` clean, live-verified presets + gateway against real Groq. Start Phase 11 next — continuous monitoring: security event model separate from findings (attack attempts, blocked requests, policy violations, new findings, regressions, suspicious tool activity), filtering by time/severity/application/model/category/event type, retention/config controls. Open follow-ups: `deploy/render.yaml` needs a gateway service block; agent-security UI + engine plugin (D-048).

**Earlier next-step note (Phase 9, kept for history):** Phases 2-9 DONE. Phase 9 (D-048): `proxy/agent_policy.py` (pure default-deny evaluator), `proxy/agent_actions.py` (recording + human approval), `proxy/agent_profiles.yaml` (server-side profiles), `AgentActionLog` table, 5 endpoints (`/v1/agents`, `/v1/agents/{id}/evaluate`, `/v1/agent-actions`, `.../approve`, `.../reject`). 242 passed/3 skipped. Deferred by design: agent-security UI page and an engine plugin so bypass cases show in dashboard/CI. Start Phase 10 next — Runtime Gateway as a separate subsystem (request inspection → policy → provider routing → response inspection → response policy → final decision), stateless where practical, no raw sensitive content stored unless configured, never log secrets. Phase 10 adds a new runtime service/architecture — per CLAUDE.md "User-Controlled Changes", confirm the gateway's deployment shape with the user before building.

**Previous next-step note (Phase 8, kept for history):** `phase_dev_upgrade.md` Phases 2-8 are DONE (D-041 provider/BYOK, D-042 engine framework, D-043 attack library + Security Tests UI, D-044 Findings, D-045 dashboard, D-046 regression testing, D-047 CI/CD). New since Phase 7: `proxy/ci.py` (pure failure-policy evaluation), `scripts/sentinel_ci.py` (HTTP-only CLI, no API keys needed), `category` query param on `/v1/security-tests/run` and `/v1/findings/sync`, `.github/workflows/security-tests.yml`. Also fixed a latent cross-file test-isolation bug (shared in-memory DB engine leaking rows between test modules by collection order — 3 test files now clear tables in both setup and teardown). 210 passed/3 skipped (Python), 13 passed (web vitest), `tsc --noEmit` clean, plus a real end-to-end CLI smoke run against a live local uvicorn instance. Start Phase 9 next — agent security subsystem: model an AI agent as Agent/Model/Tools/Permissions/Data sources/Actions, an explicit ALLOW/DENY/REQUIRE_APPROVAL policy layer, tracking (agent, tool, requested action, policy decision, execution result). Build the policy/evaluation layer only — no actual destructive actions as part of testing. Deployment (Render/Vercel accounts, production `ALLOWED_ORIGINS`) remains open but is secondary to the SentinelAI expansion work now. OD-018 (ELA signal weak on flat renders) still open but irrelevant while Fraud Copilot is paused.

## Phase Status

| Phase | Status | Current state |
|---|---|---|
| 0. Project Foundation | DONE | Repo structure, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `proxy/config.py`, `proxy/main.py`, `tests/test_foundation.py` passing (venv-verified) |
| 1. Core SentinelAI Proxy | DONE | `POST /v1/generate` live (D-015 contract): injection detector (8 attack patterns), Presidio+regex PII scanner (D-016), schema validator w/ 1 retry, in-memory per-session rate limiter, Groq+Gemini fallback provider (D-006), SQLite call logging, oversized-input/malformed-request rejection. |
| 2. Evaluation Layer | DONE | `proxy/eval/hallucination_scorer.py` (grounded + ungrounded, D-017 lexical-overlap MVP), `proxy/eval/grounding.py` (`InMemoryTFIDFStore`, D-018), grounded scoring wired into `/v1/generate`, DB persistence verified across reopened connections. Full test gate satisfied. 43 tests passing total. |
| 3. Red-Team Playground | DONE | `frontend/app.py` + `components/redteam_playground.py` live Streamlit playground per `PHASE3_PLAN.md`, D-019 cached-fallback pattern implemented client-side. Full test gate satisfied. 51 tests passing total. |
| 4. Fraud Copilot Agents | DONE | `agents/{state.py, proxy_client.py, extractor.py, forensics.py, policy_checker.py, report_writer.py, graph.py}` + `agents/policies/expense_policy.yaml`. D-021-D-024 resolved OD-006/012/013/014. LangGraph pipeline live, full test gate satisfied. 68 tests passing total. |
| 5. Synthetic Dataset | DONE | `data/{vendor_pool.py, generate_synthetic_data.py, labels.csv, holdout_injection_prompts.json}`, 45 genuine + 45 tampered + 1 adversarial receipt generated, `scripts/run_eval_suite.py` computing all 7 spec metrics. Full test gate satisfied. 87 tests passing, 1 skipped (smoke test needs a live proxy). Surfaced OD-017 (Forensics ELA thresholds need retuning against real image scale). |
| 6. Review UI + Dashboard | DONE | `frontend/{app.py, components/{review_screen,eval_dashboard}.py, lib/{pipeline_client,dashboard_data}.py, db/{models,session}.py}`. D-026/027/028 resolved OD-007/009/015. Full test gate satisfied. 102 tests passing, 1 skipped. |
| 7. Deployment + Hardening | DONE (code) | `deploy/render.yaml`, `deploy/huggingface_space/README.md`, `.github/workflows/ci.yml`, `frontend/lib/health_check.py` + cold-start UI, `GET /quota`, `ChromaStore` made default grounding backend (D-029). D-030 resolves OD-008. 109 tests passing, 3 skipped (need a live deployment/LLM keys — not run in this session). **Not yet actually deployed anywhere.** |

## Current Architecture State

### Platform layer
Planned:
- FastAPI proxy
- Injection detector
- PII/secret scanner
- Schema validator
- Rate limiter
- Hallucination/evaluation modules
- Chroma grounding
- logs DB

Implementation status: **not started**

### Application layer
Planned:
- Extractor
- Forensics
- Policy Checker
- Report Writer
- LangGraph graph
- YAML policy

Implementation status: **not started**

### Frontend
Planned:
- Red-team playground
- Review screen
- Evaluation dashboard

Implementation status: **not started**

## Active Constraints

- No direct agent → LLM provider calls.
- No real company/client data.
- Human approval required.
- Do not claim unmeasured metrics.
- Keep SentinelAI domain-agnostic.
- Keep documentation synchronized with implementation.
- Use synthetic receipts/invoices for evaluation.

## Known Open Decisions

See `decision.md` for authoritative detail.

1. Exact SentinelAI HTTP contract.
2. Injection classifier design.
3. PII/secret response handling.
4. Hallucination scoring implementation.
5. Exact rate-limit default.
6. Missing-field representation.
7. Confidence calculation.
8. Deployment provider.
9. Streamlit dashboard persistence/refresh behavior.

## Known Risks

- Free-tier LLM quotas can interrupt live demos.
- Hallucination scoring can become expensive or slow.
- OCR quality varies with receipt format.
- ELA is a signal, not proof of tampering.
- Public playground is an adversarial input surface.
- PII scanning itself can create sensitive logs if not handled carefully.
- Streamlit is fast for the MVP but may constrain more complex interactive UX.

## Continuation Procedure

A new agent must:

1. Read this file.
2. Read the active phase in `spec.md`.
3. Read relevant decisions in `decision.md`.
4. Inspect the existing implementation.
5. Continue from the **Next executable step**.
6. Update this file before ending a meaningful development session.

## State Update Rule

After every meaningful implementation session update:
- current phase
- current spec
- completed work
- tests
- blockers
- exact next step

Do not append a historical narrative here; that belongs in `progress_log.md`.
