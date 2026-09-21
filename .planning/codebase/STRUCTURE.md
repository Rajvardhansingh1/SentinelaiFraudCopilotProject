# Codebase Structure

**Analysis Date:** 2026-09-21

## Directory Layout

```
P1-SentinelaiFraudCopilotProject/
├── proxy/                  # SentinelAI: domain-agnostic LLM guardrail proxy (port 8000)
│   ├── main.py              # FastAPI app, POST /v1/generate, GET /health, /quota
│   ├── config.py            # pydantic-settings: API keys, ports, rate limit, allowed origins
│   ├── provider.py          # Groq/Gemini SDK wrappers + FallbackProvider
│   ├── schemas.py           # GenerateRequest/Response, SCHEMA_REGISTRY (ReceiptFields, PolicyVerdict, ...)
│   ├── db/                  # CallLog model + SQLAlchemy session (proxy-owned DeclarativeBase)
│   ├── middleware/          # injection_detector, pii_scanner, rate_limiter, schema_validator
│   ├── eval/                # hallucination_scorer (grounded/ungrounded), grounding (TF-IDF/Chroma)
│   └── redteam/             # attack_library.py — canned injection attack strings for the playground
├── agents/                  # Fraud Copilot: LangGraph pipeline + its own API (port 8001)
│   ├── CLAUDE.md            # module conventions (no direct provider imports, error handling)
│   ├── api.py                # FastAPI app: /v1/analyze-receipt, /v1/review-decisions, /v1/calls
│   ├── graph.py               # LangGraph StateGraph wiring the 4 pipeline nodes
│   ├── state.py                # FraudCaseState TypedDict — shared node contract
│   ├── extractor.py            # local RapidOCR + proxy call (operation=extract)
│   ├── forensics.py             # local OpenCV ELA + EXIF, no LLM/proxy call
│   ├── policy_checker.py        # proxy call (operation=policy_check) against expense_policy.yaml
│   ├── report_writer.py         # proxy call (operation=report), free-text audit narrative
│   ├── proxy_client.py           # the only permitted HTTP path to proxy/main.py's /v1/generate
│   ├── db/                     # ReviewDecision model + session (agents-owned DeclarativeBase)
│   └── policies/                # expense_policy.yaml — fraud/policy rules consumed by policy_checker
├── web/                     # Active frontend: Next.js/React (deploys to Vercel)
│   ├── app/                  # routes: playground/, review/, dashboard/, layout.tsx, page.tsx
│   ├── components/            # playground/, review/, dashboard/, layout/, ui/ (per-feature React components)
│   ├── lib/                    # api.ts (HTTP clients), types.ts, session.tsx, sample-attacks.ts, sample-receipts.ts, weakness-heuristics.ts
│   └── tests/                   # Playwright/component tests for the Next.js app
├── frontend/                 # Retired frontend: Streamlit (soft retirement, D-038)
│   ├── app.py                  # now renders a retirement banner only
│   ├── components/               # redteam_playground.py, review_screen.py, eval_dashboard.py
│   ├── lib/                       # pipeline_client.py (in-process agents.graph import), proxy_client.py, dashboard_data.py
│   └── db/                        # frontend-owned ReviewDecision copy (duplicated, not migrated — OD-019)
├── data/                     # synthetic_receipts/ — genuine + tampered + adversarial sample images (D-007)
├── scripts/                  # run_eval_suite.py and other one-off evaluation/dataset scripts
├── eval_reports/             # generated evaluation output (metrics, not source)
├── deploy/                   # render.yaml (proxy + agents API), huggingface_space/ (obsolete, D-036)
├── tests/                    # pytest suite: proxy, middleware, agents, frontend, security, deployment smoke
│   ├── agents/                  # agents-specific tests incl. test_no_direct_provider_calls.py (static enforcement of D-002)
│   └── fixtures/                  # shared test fixtures
├── CLAUDE.md                 # agent operating rules (spec-driven workflow, invariants, skill routing)
├── decision.md                # dated decision log (D-001..D-039, open decisions OD-*)
├── spec.md                    # structured SDD requirements/phases/acceptance criteria
├── state.md                   # current project state and continuation point
├── progress_log.md             # chronological implementation history
├── testing.md                  # testing strategy and quality gates
├── Project 1 Spec — SentinelAI + Fraud Copilot.md   # original project specification (do not modify)
└── requirements.txt            # Python dependencies (Groq/Gemini SDKs, FastAPI, LangGraph, RapidOCR, chromadb, ...)
```

## Directory Purposes

**`proxy/` (SentinelAI platform layer, owner: platform):**
- Purpose: domain-agnostic LLM guardrail gateway — the mandatory boundary every LLM call in the system passes through (D-002)
- Contains: FastAPI app, provider SDK wrappers, guardrail middleware, evaluation/grounding, red-team attack corpus, its own DB models
- Key files: `proxy/main.py` (request pipeline), `proxy/schemas.py` (HTTP contract + `SCHEMA_REGISTRY`), `proxy/config.py` (settings)
- Rule: must never contain fraud-domain logic (e.g. `ForensicsResult` deliberately excluded, D-021)

**`agents/` (Fraud Copilot application layer, owner: application):**
- Purpose: the concrete LLM-consuming application — multi-agent fraud-review pipeline plus its own HTTP API
- Contains: LangGraph graph/state, 4 agent node modules, proxy client wrapper, own FastAPI app, own DB models, policy YAML
- Key files: `agents/graph.py` (pipeline wiring), `agents/api.py` (HTTP surface), `agents/proxy_client.py` (sole path to SentinelAI)
- Rule (per `agents/CLAUDE.md`): no agent file imports a provider SDK directly; forensics never calls the proxy; state lives only in `state.py`; nodes never let exceptions escape uncaught

**`web/` (active frontend, owner: frontend):**
- Purpose: current product UI — playground, receipt review, evaluation dashboard
- Contains: Next.js App Router routes, React components grouped by feature, typed API client layer
- Key files: `web/lib/api.ts` (all HTTP calls to proxy port 8000 and agents API port 8001), `web/lib/types.ts` (shared response types)

**`frontend/` (retired frontend, owner: none — kept for reversibility):**
- Purpose: original Streamlit implementation of the same three surfaces; superseded by `web/`, not deleted (D-038)
- Contains: Streamlit page modules, in-process pipeline client (imports `agents.graph` directly rather than over HTTP), its own duplicated `ReviewDecision` model
- Rule: do not build new features here; `frontend/app.py` intentionally only shows a retirement banner now

**`data/synthetic_receipts/`:**
- Purpose: synthetic evaluation dataset — genuine, tampered, and one adversarial (prompt-injection-carrying) sample receipt (D-007, D-037)
- Generated: partially (some scripted generation), Committed: yes (synthetic only, no real client/company data per CLAUDE.md §12)

**`tests/`:**
- Purpose: pytest suite covering proxy middleware, provider fallback, agents pipeline, frontend clients, security hardening, deployment smoke checks
- Key files: `tests/agents/test_no_direct_provider_calls.py` (statically enforces D-002), `tests/test_security_hardening.py`, `tests/test_eval_suite_smoke.py`

**`deploy/`:**
- Purpose: deployment configuration only, not application code
- Contains: `render.yaml` (proxy + agents API as two Render services, D-030/D-035), `huggingface_space/` (obsolete Streamlit deployment target, flagged not deleted, D-036)

## Key File Locations

**Entry Points:**
- `proxy/main.py`: SentinelAI FastAPI app (uvicorn, port 8000)
- `agents/api.py`: Fraud Copilot FastAPI app (uvicorn, port 8001)
- `web/app/layout.tsx`, `web/app/page.tsx`: Next.js root layout/home
- `frontend/app.py`: retired Streamlit entry (banner only)

**Configuration:**
- `proxy/config.py`: all env-driven settings (API keys, `rate_limit_per_session`, `agents_api_port`, `allowed_origins_list`, `chroma_persist_dir`)
- `.env` / `.env.example` (not read for contents — existence only; never commit secrets, CLAUDE.md §12)
- `web/` uses `NEXT_PUBLIC_PROXY_BASE_URL` / `NEXT_PUBLIC_AGENTS_API_BASE_URL` env vars (`web/lib/api.ts:12-13`)

**Core Logic:**
- `proxy/main.py`: guardrail pipeline (injection → PII → rate limit → provider → schema validate → log)
- `agents/graph.py` + `agents/state.py`: LangGraph pipeline definition and shared state contract
- `proxy/provider.py`: provider fallback logic
- `agents/forensics.py`: local tamper-detection (ELA/EXIF)

**Testing:**
- `tests/`: full pytest suite (see Directory Purposes above)
- `web/tests/`: Playwright/component tests for the Next.js app

## Naming Conventions

**Files:**
- Python: `snake_case.py` throughout (`proxy/middleware/injection_detector.py`, `agents/policy_checker.py`)
- React/TS: `kebab-case.tsx`/`.ts` for components and lib modules (`web/components/playground/attack-picker.tsx`, `web/lib/dashboard-data.ts`), `page.tsx`/`layout.tsx` for Next.js route files

**Directories:**
- Python packages: lowercase, no dashes (`proxy`, `agents`, `middleware`, `eval`, `redteam`)
- Next.js: feature-grouped subfolders under `app/` (route segments) and `components/` (mirrors route names: `playground/`, `review/`, `dashboard/`)

## Where to Add New Code

**New guardrail/middleware (SentinelAI-level, domain-agnostic only):**
- Implementation: `proxy/middleware/<name>.py`, wired into `proxy/main.py::generate()`
- Tests: `tests/test_<name>.py`
- Rule: must not encode fraud-specific logic — that belongs in `agents/`

**New fraud-pipeline agent/node:**
- Implementation: new `agents/<node_name>.py` calling `agents/proxy_client.py::call_proxy()` (never a provider SDK directly), add a node function + edge in `agents/graph.py`, extend `agents/state.py::FraudCaseState` with any new fields
- Tests: `tests/agents/test_<node_name>.py`

**New structured LLM output schema:**
- Add the Pydantic model to `proxy/schemas.py` and register it in `SCHEMA_REGISTRY` only if it will be used with `schema_name` on `/v1/generate`; keep fraud-domain-only models agents-local instead (pattern set by `ForensicsResult`, D-021)

**New Fraud Copilot API endpoint:**
- Implementation: `agents/api.py`, backed by `agents/db/models.py` if persistence is needed
- Client: add a typed function to `web/lib/api.ts` + types in `web/lib/types.ts`

**New frontend page/feature (active app):**
- Route: `web/app/<feature>/page.tsx`
- Components: `web/components/<feature>/`
- API calls: add to `web/lib/api.ts`, never call `proxy`/`agents` DB or provider SDKs from the browser

**Utilities:**
- Python shared helpers: colocate under the owning package (`proxy/` helpers stay in `proxy/`, `agents/` helpers stay in `agents/`) — no cross-cutting `shared/` package exists; do not create one speculatively
- Frontend shared helpers: `web/lib/utils.ts`, `web/lib/format.ts`

## Special Directories

**`eval_reports/`:**
- Purpose: output of `scripts/run_eval_suite.py` (measured metrics, not claims — CLAUDE.md §10/§11)
- Generated: yes
- Committed: check before adding new reports here; treat as build output, not source

**`.venv/`, `web/node_modules/`, `__pycache__/`:**
- Purpose: local dependency/build artifacts
- Generated: yes
- Committed: no

**`frontend/` (retired):**
- Purpose: reversible soft-retirement archive of the pre-D-034 Streamlit app
- Generated: no (hand-written, historical)
- Committed: yes — kept intentionally as a safety net (no separate backup mechanism), not for new development

---

*Structure analysis: 2026-09-21*
