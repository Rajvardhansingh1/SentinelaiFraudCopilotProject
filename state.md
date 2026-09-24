# Project State — SentinelAI + Fraud Copilot

This file is the current project memory. It should describe where a fresh agent must continue, not the entire historical story.

## Current State

**2026-09-24, V3 frontend design pass (landing page, About, Install, skeleton loaders):** executed the 18-task plan at `docs/superpowers/plans/2026-09-24-v3-frontend.md` against spec `docs/superpowers/specs/2026-09-24-v3-frontend-design.md` (both gitignored `*.md`, not in git). 16 commits on `main` (Task 3 — removing `lucide-react` — was skipped: a later mobile-sidebar fix added a real usage in `sidebar-nav.tsx`, so the dependency stays; documented in `progress_log.md`). Built: real landing page at `/` (hero, 3D network canvas via three.js/`@react-three/fiber`, walkthrough, CTA), `/about`, `/install` (terminal commands verified against README.md), a `Skeleton` primitive retrofitted into 8 authenticated pages' loading states (dashboard, findings, finding detail, remediation, regression, monitoring, security, agents), IBM Plex Sans/Mono site-wide, auth gating for the 3 new public routes with logged-in-user redirect from `/` to `/playground`. Two real bugs found and fixed along the way, both pre-existing and unrelated to this plan's own scope: (1) `vitest.config.ts`/`package.json` had no JSX-in-tests support at all (no prior component-render test existed, no `@testing-library/jest-dom`) — fixed via `esbuild.jsx: "automatic"` + a new `vitest.setup.ts`. (2) `web/next.config.js`'s CSP lacked `'unsafe-eval'` in `script-src`, silently breaking **all** client-side hydration when testing against `npm run dev` (added in a later session than the last dev-server Playwright run) — fixed to only relax in dev, not production. Final verification: backend `pytest` 375 passed/2 skipped (was 374/3, the flip is a live-proxy-dependent test, not a regression — no backend code touched), `web` `tsc --noEmit` clean, `vitest run` 23/23 passed (5 new test files), `playwright test` 8 passed/1 skipped (paused Fraud Copilot review)/0 failed against a live local proxy + dev server (both started/stopped manually this session, per Playwright config's `webServer` only auto-boots the frontend). Full detail: `progress_log.md`'s 2026-09-24 "V3 frontend" entry.

**2026-09-24 follow-up bug-fix pass:** a testing subagent found and this session fixed 5 real bugs, separate from the CORS/security-headers/favicon/mobile-sidebar fixes below: (1) HIGH — `/v1/generate`'s rate limiter keyed off client-controlled `session_id`, letting anyone bypass it by rotating the value; now keys on the authenticated `user.id`. (2) HIGH — `gateway/main.py` (Phase 10 runtime gateway) had zero authentication; added a shared-secret `GATEWAY_API_KEY` bearer check (a stateless server-to-server service, not a JWT-per-user model like the proxy — see `gateway/main.py` comments). Production deploy of the gateway now needs `GATEWAY_API_KEY` set on Render, same as `JWT_SECRET`. (3) LOW — `README.md` had a stale claim that `localhost:3000` redirects straight to the playground; it redirects to `/login` when logged out since Phase 2. (4) LOW — `/regression` page fetched the regression report before checking whether a baseline existed, guaranteeing a 404/console-error on every fresh project; now checks `listBaselines()` first. (5) LOW — `/login` had no redirect-if-already-authenticated guard, so back-button navigation could dead-end an authenticated user on the bare login form; added one. Full details: `progress_log.md`'s 2026-09-24 "Follow-up bug fixes" entry.

**2026-09-24 (later same day): 4 real bugs found by a live black-box test of the deployed app fixed**: (1) CRITICAL — CORS headers missing on `require_auth`'s short-circuited error responses (`proxy/main.py`: `CORSMiddleware` was registered before the custom auth middleware, so Starlette's `insert(0)` middleware-stack behavior put `require_auth` *outside* CORS; its direct 401 `JSONResponse` returns bypassed CORS entirely, causing the browser to block them client-side. Fixed by registering `CORSMiddleware` after `require_auth`. Regression test: `tests/test_cors.py`). (2) LOW — added `X-Content-Type-Options`, `X-Frame-Options`, CSP via `web/next.config.js`. (3) COSMETIC — added `web/app/icon.svg` favicon. (4) MEDIUM — `web/components/layout/sidebar-nav.tsx`'s fixed `w-56` sidebar broke at phone width; now collapses into a hamburger-toggled off-canvas drawer below Tailwind's `lg` breakpoint. See `progress_log.md`'s 2026-09-24 "Live black-box bug fixes" entry for full detail, including one open caveat: the CSP's `connect-src` allows `https://*.onrender.com` as a best guess for the real Render proxy hostname (not recorded anywhere in the repo, no deploy access this session) — narrow it once known.

Both passes merged to `main` in the same session. Combined backend suite after merge: verify fresh (each pass independently measured 370 passed/3 skipped against slightly different baselines — see CI run below for the merged total). `tsc` clean, 18/18 vitest on both.

**All 13 spec_V3.md phases DONE** as of 2026-09-24 (D-055 through D-060), merged to `main`. Phase 7's before/after comparison UI turned out to already exist (`web/app/regression/page.tsx` — verified by reading it, not assumed). Phase 6's remediation-center page, real project context (repo_url/description) for remediation, a real `pip-audit` dependency review, and a manual logs-for-secrets review were all completed in the same pass after a literal re-check against spec_V3.md §68's acceptance checklist surfaced them as gaps. A real Supabase project's schema was also applied (10 tables, verified via Supabase MCP) — infrastructure only, no live service deployed against it yet.

**Project:** SentinelAI + Fraud Copilot
**State date:** 2026-09-24
**Overall status:** All 7 original spec.md phases + Phase 8 done and REAL-verified. Fraud Copilot paused (D-040). SentinelAI platform: `phase_dev_upgrade.md` Phases 0-12 all DONE. spec_V3.md:
- Phase 1 (baseline docs) DONE.
- Phase 2 (auth + projects, D-055/D-056/D-059) DONE — stateless JWT auth, User→Workspace→Project model, global auth middleware, **every** subsystem project-scoped (generate, findings, dashboard, calls, baselines, regression, events, reports, agent actions), cross-project isolation covered by `tests/test_auth.py`, auth-endpoint rate limiting.
- Phase 3 (target/execution model, D-056) DONE — `Project.target_type` + `TestRunResult.execution_source`.
- Phase 4 (centralized execution/result sync) DONE — satisfied by Phase 2/3's auth+scoping+execution_source together; no separate work needed.
- Phase 5 (remediation intelligence, D-057) DONE — structured Observed/Analysis/Recommendation/Confidence object per finding, `proxy/remediation.py`.
- Phase 6 (finding/remediation UX, D-060) DONE — finding detail page + new `/remediation` center page (every open finding's recommendation, worst-severity-first, evidence/analysis expandable, retest button), dashboard links to both.
- Phase 7 (retesting/regression) DONE — `web/app/regression/page.tsx` already had the full before/after comparison table, regressions/fixed lists, findings-since-baseline; confirmed by reading it, this session's earlier "PARTIAL" note was wrong.
- Phase 8 (SDK/CLI/CI) DONE — `scripts/sentinel_ci.py` supports a persistent project-scoped API key (`--api-key`/`--project-id`) alongside the original one-off bootstrap.
- Phase 9 (API/service integrations, D-058) DONE — `ProjectAPIKey`, `Authorization: ApiKey`, scoped to `/v1/findings/sync` + `/v1/regression-report`.
- Phase 10 (reporting) DONE — project-scoped executive/technical reports in JSON/Markdown/CSV.
- Phase 11 (monitoring) DONE — events fully project-scoped.
- Phase 12 (hardening, D-059/D-060) DONE — auth-endpoint rate limiting added; `pip-audit` actually run (found 4 chromadb CVEs, all in server/RBAC features this app's embedded-only `PersistentClient` usage never touches — documented, not silently dismissed); every `logging`/`print` call site in proxy/gateway/scripts manually reviewed for secret leakage — clean.
- Phase 13 (final validation) DONE — `web/tests/e2e/full-journey.spec.ts`, live against a real proxy: signup → create project → run assessment → findings → remediation center → project settings → generate report, all passing.

**Current phase:** Everything in spec_V3.md is built and tested. Real project context (`repo_url`/`description`, set via `/projects/settings`, editable any time) feeds into remediation's `project_context` field — restated facts only, never invented. Only remaining work is genuinely outside the codebase: real deployment. A real Supabase project (`eaapkdcsufyeunmmiizv`) has its schema applied (10 tables, via Supabase MCP `apply_migration`) but no live proxy has ever run against it — Render/Vercel were never actually deployed, and the DB password isn't available to this session (never exposed via MCP).
**Current spec:** All 13 spec_V3.md phases DONE. Nothing left unbuilt in the codebase.
**Next executable step (updated after D-060):** All work committed directly to `main`. Full backend suite: 366 passed, 3 skipped, 0 failed. Frontend: `tsc` clean, production build succeeds (18 routes), 18 vitest unit tests pass, 4 Playwright e2e specs pass live against a real proxy (1 skipped — paused Fraud Copilot review). If continuing: real deployment only — get the Supabase DB password (Project Settings → Database), set it + `JWT_SECRET`/`GROQ_API_KEY`/`GEMINI_API_KEY`/`ALLOWED_ORIGINS` on Render for both `sentinelai-proxy` and `sentinelai-gateway`, deploy `web/` to Vercel with `NEXT_PUBLIC_PROXY_BASE_URL` pointed at the Render proxy URL, then set `ALLOWED_ORIGINS` to the Vercel URL.

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
