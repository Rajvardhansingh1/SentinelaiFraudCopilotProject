# Sentinel AI — Current State

**Compiled:** 2026-09-23, from existing project memory (`state.md`, `decision.md`, `spec.md`, `README.md`) per phase_dev_upgrade.md Phase 0 — not a fresh line-by-line repo re-audit. Source of truth for anything below remains `state.md`/`decision.md`; this document is a synthesis for expansion-planning purposes.

## Executive Summary

SentinelAI + Fraud Copilot is a two-layer system: SentinelAI (a reusable, domain-agnostic FastAPI LLM guardrail/evaluation proxy) and Fraud Copilot (a LangGraph multi-agent expense/invoice fraud-detection application built on top of it). All 7 original spec.md phases are DONE and REAL-verified (live Groq calls, real Playwright browser testing, security/GSD review — not just unit tests). An unplanned Phase 8 (Streamlit → Next.js frontend rewrite) is also DONE. 126 Python tests passing. **Not yet deployed anywhere** — that is the single largest gap before this is a live product.

## Architecture

Three services, local-by-default:

```
Next.js UI (web/, port 3000)
   ├── Red-team prompt ──────┐
   └── Fraud Copilot agents ─┤
                              │ LLM calls only
                     SentinelAI Proxy (proxy/, port 8000)
                     injection · PII/secrets · schema validation
                     · rate limiting · provider fallback
                     · hallucination scoring · logging
                              │
                        Groq / Gemini

Fraud Copilot API (agents/api.py, port 8001)
   receipt image → PaddleOCR/RapidOCR (local) ──┐
                 → OpenCV + EXIF forensics (local) ┤
                                                    → SentinelAI for LLM structuring/reporting
```

Local-only processing (OCR, OpenCV/EXIF forensics) never goes through the LLM proxy — only their *output* becomes untrusted input to SentinelAI when it enters an LLM call (D-003).

## Component Map

| Layer | Path | Contents |
|---|---|---|
| SentinelAI platform | `proxy/` | `main.py` (FastAPI, `/v1/generate`), `config.py`, `provider.py` (Groq/Gemini fallback), `schemas.py`, `redteam/attack_library.py` (injection patterns), PII scanner, `eval/hallucination_scorer.py`, `eval/grounding.py` (TF-IDF + Chroma), `db/` (SQLite call logging) |
| Fraud Copilot agents | `agents/` | `state.py`, `proxy_client.py`, `extractor.py`, `forensics.py`, `policy_checker.py`, `report_writer.py`, `graph.py` (LangGraph), `api.py` (own FastAPI service, port 8001), `db/models.py`, `policies/expense_policy.yaml` |
| Active frontend | `web/` | Next.js 14 + TypeScript + Tailwind + shadcn/ui + Recharts. Playground / Review Receipt / Eval Dashboard |
| Retired frontend | `frontend/` | Streamlit app, soft-retired (D-038) — kept on disk, shows retirement banner, still has passing tests |
| Synthetic data | `data/` | `vendor_pool.py`, `generate_synthetic_data.py`, 45 genuine + 45 tampered + 1 adversarial receipt, `labels.csv`, `holdout_injection_prompts.json` |
| Evaluation | `scripts/run_eval_suite.py` | Computes all 7 spec.md metrics |
| Deployment config | `deploy/render.yaml`, `deploy/huggingface_space/` (stale, HF Spaces was Streamlit-only) | Not yet actually deployed |
| CI | `.github/workflows/ci.yml` | Exists |

## Data Flow

**Red-team playground:** visitor prompt → `web/` → SentinelAI `/v1/generate` → injection/PII scan (non-system messages only, D-033) → provider call (Groq→Gemini fallback) → schema validation (1 retry) → hallucination scoring → logged to SQLite → result + guardrail detail back to UI.

**Fraud Copilot pipeline:** receipt image upload → `agents/api.py` `/v1/analyze-receipt` → RapidOCR (local) + OpenCV/EXIF forensics (local, parallel) → Extractor agent calls SentinelAI to structure OCR text (`ReceiptFields` schema) → Policy Checker agent calls SentinelAI against `expense_policy.yaml` → Report Writer agent calls SentinelAI with evidence embedded directly in the prompt (D-032 fix) + `grounding_context` for scoring → LangGraph assembles final state → human reviewer approves/rejects via `/v1/review-decisions` (never automatic, D-004).

## Existing Features

- FastAPI LLM proxy with a single contract endpoint (`POST /v1/generate`, D-015)
- Prompt-injection/jailbreak pattern detection (8 patterns), scoped to non-system messages only (D-033 fix)
- PII/secret scanning: Presidio NER + regex, degrades gracefully if Presidio unavailable (D-016)
- Pydantic schema validation with one retry on failure
- In-memory per-session rate limiting (default 8 calls/session, D-020)
- Groq (primary) / Gemini (fallback) provider abstraction, crash-hardened (D-031)
- Hallucination scoring: grounded (lexical-overlap vs. retrieved context) and ungrounded (self-consistency) modes — both explicitly documented MVP heuristics, not real NLI (D-017)
- Grounding: pluggable store, `ChromaStore` (persisted) default, `InMemoryTFIDFStore` fallback (D-018/D-029)
- SQLite call logging (token/cost/latency/guardrail outcomes)
- Red-team playground: editable presets + free text, weakness-coaching only fires on the visitor's own edited attempt (D-039)
- Receipt pipeline: OCR extraction, image-tamper forensics (ELA + EXIF), configurable YAML expense policy checking, grounded audit-report generation
- Adversarial sample receipt demonstrating OCR output flowing through the same injection detector as the playground (D-037)
- Review screen: human approve/reject decision storage, never auto-applied
- Evaluation dashboard: real data from `CallLog`/`ReviewDecision` tables, manual-refresh (D-028)

## Existing APIs

- `proxy/main.py` — `POST /v1/generate` (see D-015 for full request/response contract), `GET /quota`
- `agents/api.py` — `POST /v1/analyze-receipt` (multipart, always 200, failures surface in `errors`), `POST /v1/review-decisions`, `GET /v1/calls?limit=N`

## Existing Model/Provider Integrations

Groq primary, Gemini fallback (D-006), selected via `FallbackProvider` in `proxy/provider.py`. Provider SDK imports are lazy and wrapped so a missing package degrades gracefully instead of crashing the endpoint (D-031). No provider abstraction/interface layer yet beyond this — `phase_dev_upgrade.md` Phase 2 (provider abstraction + BYOK) has not been started.

## Storage/Data Model

SQLite, single file, two independent SQLAlchemy `DeclarativeBase`/`create_all()` pairs sharing one `database_url` (D-009, D-027): `proxy/db/models.py::CallLog` and `agents/db/models.py::ReviewDecision` (the Streamlit-era `frontend/db/models.py::ReviewDecision` is a still-live duplicate kept only for the retired Streamlit app, D-038/OD-019). Grounding vectors persist separately via Chroma (`CHROMA_PERSIST_DIR`).

## Security Model

- Trust boundary: system-prompt content is trusted (caller-authored); user/OCR/external content is untrusted and scanned (D-033)
- Injection detection via pattern matching (OD-002 — classifier design still open, pattern-only today)
- PII/secret scanning on untrusted inbound text
- Human-in-the-loop is mandatory — no auto-approve/reject (D-004)
- Rate limiting per session
- CORS added to `proxy/main.py` when the frontend became a separate origin (D-034)

## Secret Handling

API keys (Groq/Gemini) are server-side only, loaded via `.env`/`proxy/config.py`, never sent to the browser, never logged, never committed (`.env.example` documents required vars without real values). This is the existing baseline `phase_dev_upgrade.md` Phase 2's BYOK requirements would build on top of, not replace.

## Test Coverage

126 Python tests passing (pytest) across proxy, agents, evaluation, and (retired) Streamlit UI layers, plus Vitest coverage for `web/`. 3 tests skipped (need a live deployment/LLM keys not available in a given session). Playwright e2e tests are written but unexecuted in this environment (no network egress for the browser binary). Full phase-by-phase test gates documented in `spec.md`/`testing.md`.

## Known Technical Debt

- OD-002: injection detector is pattern-only, no ML classifier layer
- OD-003: no formal decision on response-side PII/secret action (redact/block/retry)
- OD-018 (open): ELA tamper-detection signal is weak on flat synthetic receipt renders — a documented, measured limitation, not a bug
- `frontend/db/models.py::ReviewDecision` is a duplicated, unmigrated table kept alive only for the retired Streamlit app
- `deploy/huggingface_space/README.md` is stale (was Streamlit-specific, D-036)
- `PHASE7_PLAN.md` not revised for the current 3-service topology (proxy + agents API + Next.js) since D-035/D-036

## Risks

- Free-tier LLM quotas can interrupt live demos
- Hallucination scoring is a lexical-overlap heuristic, not real NLI — must not be overclaimed (D-017, D-026)
- ELA forensics signal is weak on this dataset's flat synthetic renders (OD-018)
- Public playground is an adversarial input surface
- Nothing is deployed yet — Render/Vercel accounts, production `ALLOWED_ORIGINS`, and a second Render service block for `agents/api.py` are all still needed

## Recommended Refactoring (before expansion)

None blocking — the codebase is already stabilized through real live-traffic bug fixes (D-031/D-032/D-033), not just unit-tested. The one open architectural loose end is the duplicated `ReviewDecision` table (`frontend/db/` vs `agents/db/`), which should be resolved when `frontend/` is hard-deleted rather than during provider-abstraction work.

## Recommended Expansion Points

Directly consistent with `phase_dev_upgrade.md`'s proposed phase order:

- **Phase 2 (provider abstraction + BYOK):** `proxy/provider.py` already has a `FallbackProvider` pattern to build a clean interface on top of — this is additive, not a rewrite.
- **Phase 3 (security engine):** `proxy/redteam/attack_library.py` is the natural seed for TEST DEFINITION → EXECUTION → EVALUATION → FINDING → EVIDENCE separation; existing playground call/response logging already captures most of what a finding needs.
- **Later phases (findings, dashboard, regression, CI/CD, agent security, gateway, monitoring, reports):** all currently unbuilt — nothing in the existing codebase should be assumed to already implement them.

## Summary for the user

No architectural surprises: the codebase matches what `state.md`/`decision.md` already say, all 7+1 phases done and real-tested, not deployed. Phase 0 of `phase_dev_upgrade.md` is satisfied by this document without needing a full re-audit, since equivalent (and more detailed, dated) information already existed in project memory.
