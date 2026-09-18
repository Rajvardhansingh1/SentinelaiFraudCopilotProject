# Project State — SentinelAI + Fraud Copilot

This file is the current project memory. It should describe where a fresh agent must continue, not the entire historical story.

## Current State

**Project:** SentinelAI + Fraud Copilot  
**State date:** 2026-09-18  
**Overall status:** All 7 original spec.md phases done and REAL-verified (live Groq calls, real Playwright browser testing, real security/GSD review) — not just unit-tested. Several real bugs found via that live testing were fixed (see progress_log.md). A new, unplanned "Phase 8" opened: full frontend rewrite Streamlit → React/Next.js (D-034), user-requested after live testing surfaced UX limits. Planning in flight (`REACT_FRONTEND_PLAN.md` not yet landed).
**Current phase:** Phase 8 — Frontend rewrite (React/Next.js). Built and verified. `frontend/` (Streamlit) formally retired 2026-09-19 (D-038) — kept on disk (no git safety net for a hard delete), shows a retirement banner if run, no longer the recommended UI. `web/` (Next.js) is now the active frontend.
**Current spec:** Original 7 phases DONE. Phase 8 DONE (build + retirement), deployment not yet live.
**Next executable step:** Deployment is the main remaining item — needs user's own Render/Vercel accounts, real production `ALLOWED_ORIGINS`, and a second Render service block for `agents/api.py` (D-035's consequence, `PHASE7_PLAN.md` not yet revised for the new topology). Playwright e2e tests are written but unexecuted (no network egress for the browser binary in this environment). OD-018 (ELA signal weak on flat renders) still open.

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
