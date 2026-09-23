# Project State — SentinelAI + Fraud Copilot

This file is the current project memory. It should describe where a fresh agent must continue, not the entire historical story.

## Current State

**Project:** SentinelAI + Fraud Copilot  
**State date:** 2026-09-23  
**Overall status:** All 7 original spec.md phases done and REAL-verified (live Groq calls, real Playwright browser testing, real security/GSD review) — not just unit-tested. Several real bugs found via that live testing were fixed (see progress_log.md). Phase 8 (Streamlit → React/Next.js rewrite, D-034) also done. **2026-09-23 (D-040): Fraud Copilot paused** — user wants SentinelAI (platform layer) expanded on its own for now, per `phase_dev_upgrade.md`. `web/app/review` shows a paused notice, `agents/api.py` is out of the normal run flow, all Fraud Copilot code kept on disk untouched.
**Current phase:** SentinelAI expansion per `phase_dev_upgrade.md` (Phase 0 audit done → `docs/SENTINEL_CURRENT_STATE.md`; Phase 1 stabilization already substantially satisfied by the existing decision log's real-bug-fix history — D-031/032/033). Fraud Copilot (Phases 4-6 of the original spec, plus the paused React review UI) is out of scope until explicitly resumed.
**Current spec:** Original 7 phases + Phase 8 DONE for what was built; Fraud Copilot paused, not removed. `phase_dev_upgrade.md` Phases 2-12 (provider abstraction/BYOK, security engine, attack library, findings, dashboard, regression, CI/CD, agent security, gateway, monitoring, reports) are the active forward roadmap, scoped to `proxy/` only.
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
