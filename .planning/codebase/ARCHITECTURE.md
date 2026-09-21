<!-- refreshed: 2026-09-21 -->
# Architecture

**Analysis Date:** 2026-09-21

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        web/  (Next.js frontend, active)              │
│  Playground UI   Review Receipt UI   Eval Dashboard UI               │
│  `web/app/playground` `web/app/review` `web/app/dashboard`           │
│  (frontend/ Streamlit app is retired — soft, code kept, D-038)       │
└───────────────┬───────────────────────────────┬──────────────────────┘
                │ POST /v1/generate              │ POST /v1/analyze-receipt
                │ (playground)                   │ POST /v1/review-decisions
                │                                 │ GET  /v1/calls
                ▼                                 ▼
┌─────────────────────────────┐   ┌────────────────────────────────────┐
│   proxy/  SentinelAI          │   │   agents/  Fraud Copilot API        │
│   FastAPI, port 8000          │◄──┤   FastAPI, port 8001 (agents/api.py)│
│   `proxy/main.py`              │   │   invokes LangGraph pipeline        │
│   domain-agnostic LLM gateway │   │   `agents/graph.py`                 │
└───────────────┬───────────────┘   └───────────────┬──────────────────┘
                │                                     │ calls back into
                ▼                                     │ proxy via
┌───────────────────────────────┐                    │ agents/proxy_client.py
│ Guardrail middleware           │◄───────────────────┘  (D-002 boundary)
│ injection / pii / rate-limit /│
│ schema-validator                │
│ `proxy/middleware/*`            │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│ Provider abstraction            │
│ Groq (primary) → Gemini (fallback)
│ `proxy/provider.py`             │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│ SQLite (CallLog, ReviewDecision)│
│ `proxy/db/`, `agents/db/`       │
└───────────────────────────────┘
```

Local, non-LLM processing (OCR, forensics) runs inside `agents/` and never
touches the proxy (D-003):

```text
agents/extractor.py::run_ocr()   → RapidOCR (local, onnxruntime)
agents/forensics.py::analyze()   → OpenCV/exifread (local, ELA + EXIF)
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| SentinelAI proxy | Domain-agnostic LLM gateway: injection/PII scan, rate limit, provider call+fallback, schema validation, hallucination scoring, call logging | `proxy/main.py` |
| Provider abstraction | Wraps Groq/Gemini SDKs behind one `Provider` interface with fallback | `proxy/provider.py` |
| Guardrail middleware | Injection pattern matching, PII/secret regex+Presidio, per-session rate limiting, Pydantic schema retry-once validation | `proxy/middleware/*.py` |
| Hallucination/grounding eval | Grounded claim-overlap scoring, ungrounded self-consistency scoring, pluggable grounding store (TF-IDF/Chroma) | `proxy/eval/hallucination_scorer.py`, `proxy/eval/grounding.py` |
| Red-team attack corpus | Canned prompt-injection attack strings used by the playground | `proxy/redteam/attack_library.py` |
| Fraud Copilot API | Second FastAPI service exposing pipeline execution, review-decision recording, call-log listing to the frontend | `agents/api.py` |
| LangGraph pipeline | 4-node sequential fraud-review graph: extractor → forensics → policy_checker → report_writer | `agents/graph.py` |
| Extractor agent | Local OCR (RapidOCR) then LLM field-extraction call through the proxy | `agents/extractor.py` |
| Forensics agent | Local OpenCV ELA + EXIF tamper analysis, no LLM call | `agents/forensics.py` |
| Policy checker agent | LLM call through the proxy against `agents/policies/expense_policy.yaml` | `agents/policy_checker.py` |
| Report writer agent | LLM call through the proxy producing free-text audit narrative + hallucination score | `agents/report_writer.py` |
| Proxy client (agents) | The only permitted path from agent code to SentinelAI (`POST /v1/generate`) | `agents/proxy_client.py` |
| Fraud Copilot DB | `ReviewDecision` (human approve/reject) storage, separate `DeclarativeBase` from proxy's | `agents/db/models.py`, `agents/db/session.py` |
| Next.js frontend (active) | Playground, Review Receipt, Eval Dashboard pages; talks to both proxy (port 8000) and agents API (port 8001) | `web/app/*`, `web/lib/api.ts` |
| Streamlit frontend (retired, soft) | Same three surfaces, in-process Python calls instead of HTTP to a separate agents API; kept on disk, shows a retirement banner | `frontend/app.py`, `frontend/components/*.py`, `frontend/lib/pipeline_client.py` |

## Pattern Overview

**Overall:** Two-layer platform/application architecture (D-001) — a
domain-agnostic LLM guardrail proxy (SentinelAI) consumed by a fraud-specific
multi-agent pipeline (Fraud Copilot), each with its own FastAPI process and
its own SQLite-backed data ownership, fronted by a separate Next.js SPA.

**Key Characteristics:**
- Every LLM call in the system funnels through one endpoint: `POST /v1/generate` on `proxy/main.py` (D-002, D-015). No agent or frontend code holds a provider SDK key or imports `groq`/`google.generativeai` directly — enforced statically by `tests/agents/test_no_direct_provider_calls.py`.
- Three independently deployable services: SentinelAI proxy (port 8000), Fraud Copilot API (port 8001, `agents/api.py`), Next.js frontend (Vercel). Two Python services share one physical SQLite file but use separate SQLAlchemy `DeclarativeBase`/metadata objects (D-027, D-035).
- Non-LLM processing (OCR, image forensics) is intentionally kept outside the proxy boundary — it is local computation, not a guardrailed LLM call (D-003).
- Human-in-the-loop is architecturally enforced, not just UI convention: the pipeline never writes a `human_decision`; that only happens via a distinct `POST /v1/review-decisions` call the reviewer UI issues after a person acts (D-004, D-027).
- Every external HTTP call in the codebase (provider SDK call, proxy→provider, agent→proxy, frontend→proxy/agents-api) is fully wrapped including the lazy `import`/`.json()` parse, after a real bug (D-031) showed a bare `resp.json()` or unguarded import escaping a `try/except` crashes the whole caller.

## Layers

**SentinelAI platform layer (`proxy/`):**
- Purpose: reusable LLM guardrail + evaluation gateway, no fraud-domain knowledge
- Location: `proxy/`
- Contains: FastAPI app (`main.py`), provider abstraction, guardrail middleware, hallucination/grounding eval, red-team attack corpus, SQLAlchemy call-log model
- Depends on: Groq/Gemini SDKs, Chroma (optional), SQLite
- Used by: `agents/proxy_client.py` (Fraud Copilot), `web/lib/api.ts` (playground), `frontend/lib/proxy_client.py` (retired Streamlit)

**Fraud Copilot application layer (`agents/`):**
- Purpose: fraud-specific multi-agent pipeline built on top of SentinelAI
- Location: `agents/`
- Contains: LangGraph graph/state, 4 agent nodes, `proxy_client.py` HTTP wrapper, own FastAPI HTTP surface (`api.py`), own DB models
- Depends on: `proxy/schemas.py` types only (no direct provider access), RapidOCR, OpenCV/exifread
- Used by: `web/lib/api.ts` (Next.js Review/Dashboard pages), `frontend/lib/pipeline_client.py` (retired Streamlit, in-process import instead of HTTP)

**Frontend layer (`web/`, active):**
- Purpose: visitor-facing playground, receipt review workflow, evaluation dashboard
- Location: `web/app/*` (routes), `web/components/*` (UI), `web/lib/*` (API clients, formatting, types)
- Contains: React/Next.js pages calling `proxy/main.py` directly (playground only) and `agents/api.py` (analyze-receipt, review-decisions, calls)
- Depends on: `NEXT_PUBLIC_PROXY_BASE_URL` (default `http://localhost:8000`), `NEXT_PUBLIC_AGENTS_API_BASE_URL` (default `http://localhost:8001`)
- Used by: end users / reviewers in the browser

**Frontend layer (`frontend/`, retired):**
- Purpose: original Streamlit playground/review/dashboard; superseded by `web/` (D-034, D-038)
- Location: `frontend/`
- Contains: `app.py` entry (now shows retirement banner), `components/*.py` pages, `lib/pipeline_client.py` (in-process `agents.graph` import — this is why a real HTTP API layer was later needed for `web/`), `db/models.py` (its own `ReviewDecision` copy, duplicated not migrated, D-027/OD-019)
- Status: code kept on disk for reversibility, not deleted; still covered by its own tests

## Data Flow

### Primary Request Path — Playground `/v1/generate` call

1. Visitor submits a prompt on `web/app/playground/page.tsx`; `web/lib/api.ts::postGenerate()` POSTs to `proxy/main.py`'s `POST /v1/generate` with a fixed anti-jailbreak `SYSTEM_PROMPT` + the visitor's message (`web/lib/api.ts:16-67`).
2. `proxy/main.py::generate()` splits inbound content into `inbound_text` (size check) and `untrusted_text` (excludes `system`-role messages, D-033) (`proxy/main.py:102-107`).
3. Oversize check (`MAX_INPUT_CHARS=50_000`) → 413 if exceeded (`proxy/main.py:109-121`).
4. `check_injection(untrusted_text)` and `check_pii(untrusted_text)` run (`proxy/middleware/injection_detector.py`, `proxy/middleware/pii_scanner.py`) — only on the visitor's own text, never the trusted system prompt (`proxy/main.py:123-125`).
5. Injection match → 400 `injection_detected`, logged, no provider call (`proxy/main.py:128-138`).
6. `check_and_increment(req.session_id)` enforces the per-session rate limit (default 8, D-020); over limit → 429 `rate_limit_exceeded` (`proxy/main.py:140-150`, `proxy/middleware/rate_limiter.py`).
7. `provider.generate(req.messages)` calls `FallbackProvider` → Groq first, Gemini on `ProviderError` (`proxy/main.py:152-165`, `proxy/provider.py:83-98`). Provider failure (including import failure of the SDK) → 502 `provider_failed`, never an uncaught 500 (D-031).
8. Response text is PII-scanned again (outbound) and merged into `guardrails.pii` (`proxy/main.py:168-173`).
9. If `req.grounding_context` present, `score_grounded()` computes a hallucination score (`proxy/main.py:183-184`, `proxy/eval/hallucination_scorer.py`) — not used by the playground call itself (no grounding context sent), but is exercised by agent calls.
10. If `req.schema_name` present, `validate_structured_output()` parses/validates against a `proxy/schemas.py::SCHEMA_REGISTRY` Pydantic model, retrying the caller-supplied generation once on failure; still-invalid → 422 `schema_validation_failed` (`proxy/main.py:186-204`). Playground calls pass `schema_name: null` (free text).
11. Every branch (success, injection block, rate limit, schema failure, provider failure, oversize) is written to `CallLog` via `_log()` before returning (`proxy/main.py:80-95`).
12. `GenerateResponse` (output/guardrails/usage/error envelope, D-015) returns to the browser; `web/lib/api.ts` never throws on transport failure — a network error or bad JSON is converted to a synthetic 503 `proxy_unreachable` envelope of the same shape (D-031 pattern, `web/lib/api.ts:39-67`).

### Receipt-Review Pipeline (LangGraph, via `agents/api.py`)

1. Reviewer uploads an image on `web/app/review/page.tsx`; `web/lib/api.ts::analyzeReceipt()` POSTs multipart `session_id` + `image` to `agents/api.py`'s `POST /v1/analyze-receipt` (port 8001) (`web/lib/api.ts:96-116`).
2. `agents/api.py::analyze_receipt()` validates the file extension (`.png/.jpg/.jpeg`), writes the upload to a UUID-named temp path (never the client-supplied filename — path-traversal guard), and invokes the compiled LangGraph app (`agents/api.py:68-96`, `agents/graph.py:85`).
3. **`extractor_node`** (`agents/graph.py:14-32`): `agents/extractor.py::run_ocr()` runs local RapidOCR on the image; OCR failure records `errors[]` and short-circuits that node's output (never raises past the node). On success, `extract_fields()` calls the proxy (`agents/proxy_client.py::call_proxy()` → `POST /v1/generate`, `operation="extract"`, `schema_name="receipt_fields"`) with the **untrusted OCR text as the user message** — this is the same injection/PII detector path as the playground, since OCR text is treated as untrusted input entering an LLM call (D-003's stated consequence, demonstrated live by the adversarial sample receipt, D-037).
4. **`forensics_node`** (`agents/graph.py:35-43`): `agents/forensics.py::analyze()` runs local OpenCV ELA (max-block-residual, D-025) + EXIF checks; no LLM call, no proxy round-trip (D-003, D-021 — `ForensicsResult` stays agents-local, never registered in `proxy/schemas.py`).
5. **`policy_checker_node`** (`agents/graph.py:46-52`): `agents/policy_checker.py::check_policy()` calls the proxy (`operation="policy_check"`) with the extracted fields plus `agents/policies/expense_policy.yaml` rules, schema-validated via a registered Pydantic model.
6. **`report_writer_node`** (`agents/graph.py:55-66`): `agents/report_writer.py::write_report()` calls the proxy (`operation="report"`, `schema_name=None` — free text, D-023) with the evidence bundle embedded directly in the prompt (not just `grounding_context`, D-032 bug fix) and also passed as `grounding_context` so `score_grounded()` can compute the hallucination score used later as the review screen's "confidence" (`confidence = 1 - hallucination.score`, D-026).
7. Any node exception is caught by `agents/api.py`'s outer `try/except` and converted into an `errors[]`-only state rather than a 500 (`agents/api.py:82-94`) — matches the pipeline-level contract that a partial pipeline result is still a 200 with per-field `None`s (D-024).
8. `agents/api.py` returns `{extracted_fields, extraction_guardrails, forensics_result, policy_verdict, report_text, report_guardrails, errors}` to the browser; the temp image file is always deleted in a `finally` block (`agents/api.py:95-96`).
9. `web/app/review/page.tsx` renders the system verdict/evidence, but never auto-decides; the reviewer explicitly approves/rejects, which triggers `web/lib/api.ts::recordReviewDecision()` → `agents/api.py`'s `POST /v1/review-decisions` → `agents/db/models.py::ReviewDecision` row (D-004, D-027).
10. `web/app/dashboard/page.tsx` reads aggregate history via `web/lib/api.ts::getCalls()` → `agents/api.py`'s `GET /v1/calls`, which queries `proxy.db`'s `CallLog` table directly (no duplicated model, `agents/api.py:145-168`).

**State Management:**
- Pipeline state is a single `TypedDict` (`agents/state.py::FraudCaseState`) threaded through every LangGraph node; each node returns only the keys it updates (LangGraph merges into the running state). `errors` accumulates via `_append_error()` (`agents/graph.py:10-11`) rather than raising, so the graph always completes.
- No server-side session/auth state — `session_id` is a caller-generated string used only for per-session rate limiting and call-log correlation (`web/lib/session.tsx` generates/persists it client-side).

## Key Abstractions

**`Provider` protocol:**
- Purpose: uniform `generate(messages) -> LLMResponse` interface hiding Groq vs Gemini SDK differences
- Examples: `proxy/provider.py::GroqProvider`, `GeminiProvider`, `FallbackProvider`
- Pattern: Strategy + fallback decorator; lazy `import` inside the `try` block so a missing SDK package degrades to a `ProviderError` (caught by `FallbackProvider`) instead of crashing the whole request (D-031)

**`GroundingStore` protocol:**
- Purpose: pluggable retrieval backend for hallucination grounding
- Examples: `proxy/eval/grounding.py::InMemoryTFIDFStore` (default, dependency-light), `ChromaStore` (persisted, selected first when `chromadb` import succeeds)
- Pattern: interface + swappable implementation selected by `get_grounding_store()` (D-018, D-029)

**`FraudCaseState` (LangGraph state):**
- Purpose: single shared contract every pipeline node reads/writes
- Examples: `agents/state.py`
- Pattern: `TypedDict(total=False)`; nodes are pure functions `(state) -> partial_state_dict`

**`SCHEMA_REGISTRY` (structured LLM outputs):**
- Purpose: maps `schema_name` string in the `/v1/generate` request to a Pydantic model for retry-once validation
- Examples: `proxy/schemas.py`, consumed by `proxy/middleware/schema_validator.py::validate_structured_output()`
- Pattern: registry dict keyed by string name, kept in the domain-agnostic proxy even though only Fraud Copilot currently populates it (fraud-specific models like `ForensicsResult` deliberately excluded, D-021)

**Two-service HTTP boundary:**
- Purpose: keep SentinelAI reusable/domain-agnostic while Fraud Copilot gets its own API surface
- Examples: `proxy/main.py` (port 8000) vs `agents/api.py` (port 8001)
- Pattern: `agents/api.py` calls `proxy/main.py` the same way any external caller would (`agents/proxy_client.py::call_proxy()` over HTTP), never by importing `proxy/` internals directly (D-035)

## Entry Points

**SentinelAI proxy:**
- Location: `proxy/main.py` (uvicorn ASGI app `app`)
- Triggers: any HTTP client (agents, playground, tests) hitting port 8000
- Responsibilities: guardrails, provider dispatch, schema validation, call logging; `init_db()` runs at import time

**Fraud Copilot API:**
- Location: `agents/api.py` (uvicorn ASGI app `app`, default port 8001 via `proxy/config.py::settings.agents_api_port`)
- Triggers: `web/` frontend HTTP calls
- Responsibilities: pipeline invocation, review-decision persistence, call-log listing; `init_db()` + `init_proxy_db()` both run at import time (two DeclarativeBases, one SQLite file)

**Next.js frontend:**
- Location: `web/app/layout.tsx` (root layout), route pages under `web/app/{playground,review,dashboard}/page.tsx`
- Triggers: browser navigation
- Responsibilities: render UI, call `web/lib/api.ts` client functions, never call an LLM provider or DB directly

**Streamlit frontend (retired):**
- Location: `frontend/app.py`
- Triggers: `streamlit run frontend/app.py`
- Responsibilities: now only renders a retirement banner (D-038); underlying page modules (`frontend/components/*.py`) remain functional and tested but are not the recommended entry point

## Architectural Constraints

- **Threading:** Both FastAPI services are synchronous-def route handlers (no `async def` on the hot paths in `proxy/main.py`/`agents/api.py` except the file-upload handler); uvicorn's default threadpool handles concurrency. No custom worker/thread model.
- **Global state:** `agents/api.py::_graph` is a lazy-initialized module-level singleton (built once per process, `agents/api.py:55-65`) — matches `frontend/lib/pipeline_client.py::_get_graph()`'s pattern. `proxy/provider.py::get_provider()` constructs a fresh `FallbackProvider` per request (no shared client state, no connection pooling assumptions).
- **Two DeclarativeBases, one SQLite file:** `proxy/db/models.py` and `agents/db/models.py` (and the retired `frontend/db/models.py`) each define an independent SQLAlchemy `Base`/metadata and call their own `create_all()` against the same `database_url` — by design (D-027), not an oversight, to keep SentinelAI's schema domain-agnostic.
- **Duplicated `ReviewDecision` model:** `frontend/db/models.py::ReviewDecision` and `agents/db/models.py::ReviewDecision` are intentionally two separate model definitions during the Streamlit→React transition window, not a shared import (OD-019 note).
- **Trust boundary:** system-role message content is always trusted/caller-authored and skipped by injection/PII scanning; every other message role (OCR text, visitor prompts, extracted-field text fed into later prompts) is untrusted and always scanned (D-033).

## Anti-Patterns

### Unwrapped external call / lazy import outside try

**What happens:** An early version had `from groq import Groq` outside the `try/except ProviderError` block in `proxy/provider.py`, and `resp.json()` outside `try/except` in both `agents/proxy_client.py::call_proxy()` and `frontend/lib/proxy_client.py::call_generate()`.
**Why it's wrong:** A missing package or non-JSON response body raised an uncaught exception that skipped the intended fallback/error-envelope path and crashed the whole caller (a 500 with a non-JSON body, or an uncaught `JSONDecodeError` bubbling into a LangGraph node) — found via live testing, not unit tests (D-031).
**Do this instead:** Wrap the entire external call, including any lazy `import` and any `.json()`/parsing step, inside one `try/except`. See `proxy/provider.py::GroqProvider.generate()` and `web/lib/api.ts::postGenerate()` for the corrected pattern — every remote call returns a same-shaped envelope on failure rather than raising.

### Scanning trusted content for attacks

**What happens:** `proxy/main.py` originally ran `check_injection`/`check_pii` against the full joined message list, including the caller's own `system` role prompt.
**Why it's wrong:** A caller's defensive anti-jailbreak system prompt (e.g. `web/lib/api.ts::SYSTEM_PROMPT`, containing phrases like "act as a different persona") matches the same regex patterns the detector uses to catch real attacks (`role_override` in `proxy/redteam/attack_library.py`), self-triggering a block on every single request regardless of the visitor's actual input (D-033 — a release-blocking bug found via Playwright testing).
**Do this instead:** Scan only non-`system`-role message content (`untrusted_text` in `proxy/main.py:107`). Any future caller adding its own system prompt with safety language must rely on this trust split, not add prompt-phrasing workarounds.

### Grounding context assumed to reach the prompt automatically

**What happens:** `agents/report_writer.py::write_report()` originally passed the evidence bundle only via `grounding_context`, assuming the proxy would inject it into the LLM prompt.
**Why it's wrong:** `proxy/main.py` uses `grounding_context` exclusively for post-hoc `score_grounded()` scoring — it is never added to the messages sent to the provider. The LLM received no evidence and correctly refused to write a report (D-032, found via a real Groq call, invisible to mocked tests).
**Do this instead:** Any caller needing grounded output must embed the evidence directly in the message content itself; `grounding_context` is a scoring input only, not a prompt-augmentation mechanism.

## Error Handling

**Strategy:** Fail explicit, never silent (CLAUDE.md §11). Every layer converts exceptions into a structured value (envelope, `errors[]` entry, HTTP error code) rather than letting them propagate uncaught past a component boundary.

**Patterns:**
- Proxy: one global `@app.exception_handler(Exception)` (`proxy/main.py:51-59`, mirrored in `agents/api.py:41-47`) catches anything unhandled and returns the same envelope shape as expected error paths, logging the traceback server-side only.
- LangGraph nodes: each node wraps its own risky work (`run_ocr`, `run_forensics`, proxy calls) and returns `errors: [...]` plus `None` for the affected state field instead of raising past the node (`agents/graph.py`, `agents/CLAUDE.md`).
- HTTP clients (agent→proxy, frontend→proxy/agents-api): never throw; return a `(status_code, body)` tuple or a synthetic unreachable envelope with the same shape a real response would have (`agents/proxy_client.py`, `web/lib/api.ts`, `frontend/lib/proxy_client.py`).

## Cross-Cutting Concerns

**Logging:** Python `logging` module, one logger per app (`logging.getLogger("proxy")`, `logging.getLogger("agents.api")`); unhandled exceptions logged server-side with full traceback, never leaked to the client response body.
**Validation:** Pydantic models throughout — `proxy/schemas.py` for the `/v1/generate` contract and `SCHEMA_REGISTRY`-registered structured outputs (retried once on failure, D-015/CLAUDE.md); request bodies on both FastAPI apps use Pydantic (`GenerateRequest`, `ReviewDecisionIn`).
**Authentication:** None implemented — `session_id` is a caller-supplied/generated string used only for rate-limiting and log correlation, not an auth token. Cross-origin access is restricted via `CORSMiddleware` with `settings.allowed_origins_list` on both FastAPI apps (D-034's stated consequence of a separately-hosted frontend).

---

*Architecture analysis: 2026-09-21*
