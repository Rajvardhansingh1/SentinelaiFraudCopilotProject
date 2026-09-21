# Coding Conventions

**Analysis Date:** 2026-09-21

## Project-Level Rules (from CLAUDE.md files)

The repo root `CLAUDE.md` and `agents/CLAUDE.md` encode binding architecture rules, not just style suggestions. These are enforced by tests, not just documentation:

- **SentinelAI is domain-agnostic; Fraud Copilot is the application layer built on top of it.** Every Fraud Copilot LLM call must route through the proxy (`POST /v1/generate`).
- **No agent file imports a provider SDK directly** (`groq`, `google.generativeai`). The only path to an LLM is `agents/proxy_client.py::call_proxy()`. Enforced statically by `tests/agents/test_no_direct_provider_calls.py`, which AST-parses every file under `agents/` and asserts no forbidden imports.
- **Forensics never calls the proxy** — `agents/forensics.py` is pure local OpenCV/exifread (decision D-003).
- **Shared state contract lives in one place** — `agents/state.py` defines `FraudCaseState` (a `TypedDict`), used by every LangGraph node and `agents/graph.py`. Do not duplicate field definitions elsewhere.
- **A LangGraph node never lets an exception escape uncaught.** It records into `state["errors"]` and continues with `None` for the affected field — no silent swallow, but also no crash (see `agents/graph.py` pattern below).
- **Decisions are referenced inline by ID** (e.g. `D-002`, `D-003`, `D-015`, `D-024`, `D-031`) in docstrings/comments, pointing back to `decision.md`. When touching code that cites a decision ID, read that entry in `decision.md` before changing behavior.
- **Human review is mandatory** — fraud verdicts must never auto-approve/reject; a human always makes the final call. Never remove or bypass this gate.
- **Untrusted-input boundary:** OCR text, uploaded images, LLM output, and external API responses are all treated as untrusted and must pass through SentinelAI's guardrails before being trusted downstream.
- **No secrets in code, tests, docs, logs, or sample data.**

## Naming Patterns

**Python files/modules:**
- `snake_case.py`, one responsibility per file: `injection_detector.py`, `pii_scanner.py`, `rate_limiter.py`, `schema_validator.py` (`proxy/middleware/`); `extractor.py`, `forensics.py`, `policy_checker.py`, `report_writer.py`, `proxy_client.py` (`agents/`).
- Node functions in `agents/graph.py` are suffixed `_node`: `extractor_node`, `forensics_node`, `policy_checker_node`, `report_writer_node`.
- Private/internal helpers prefixed `_`: `_append_error`, `_imported_modules`.

**TypeScript/React (`web/`):**
- Files: `kebab-case.tsx` / `kebab-case.ts` — `cost-latency-cards.tsx`, `guardrail-catches-card.tsx`, `human-decision-panel.tsx`, `weakness-heuristics.ts`.
- Directory-per-domain under `web/components/`: `dashboard/`, `playground/`, `review/`, `ui/`, `layout/` — mirrors the three app routes (`web/app/dashboard`, `web/app/playground`, `web/app/review`) plus a shared primitives folder (`ui/`).
- Types centralized in `web/lib/types.ts` and imported via `import type { ... } from "./types"`.

**Types:**
- Python: `TypedDict` for structured shared state (`FraudCaseState`), Pydantic models for API/schema contracts (`proxy/schemas.py`, e.g. `InjectionResult`).
- TypeScript: explicit `type`-only imports (`import type {...}`) kept separate from value imports.

## Code Style

**Python:**
- Type hints throughout, including modern `str | None` union syntax (Python 3.10+ style) rather than `Optional[str]`.
- Module-level constants in `UPPER_SNAKE_CASE` read from environment with a sane default: `PROXY_BASE_URL = os.environ.get("PROXY_BASE_URL", "http://localhost:8000")` (`agents/proxy_client.py`).
- Small, single-purpose functions — e.g. `check_injection()` in `proxy/middleware/injection_detector.py` is a 3-line function that delegates pattern matching to `proxy/redteam/attack_library.py` and wraps the result in a Pydantic result type.
- Custom exceptions documented with a docstring explaining exactly what they mean and what they don't (see `ProxyCallFailed` below) — favor precise, narrow exception types over generic `Exception`.
- Comments explain *why*, referencing decision IDs, not just what the code does.

**TypeScript:**
- Functional components, Next.js 14 app router (`web/app/*/page.tsx`).
- `NEXT_PUBLIC_*` env vars for client-exposed config, with fallback defaults matching the Python services' defaults (`http://localhost:8000` proxy, `http://localhost:8001` agents API) — keeps `web/lib/api.ts` and Python `agents/proxy_client.py` symmetrical.
- Cross-stack duplication is called out explicitly in comments, e.g. `web/lib/api.ts`: `// Ported from frontend/lib/proxy_client.py::call_generate (D-015/D-031).` — when the same logic/prompt exists in both the Streamlit (`frontend/`) and Next.js (`web/`) frontends, the port is documented, not silent.

## Error-Handling Pattern (critical, repeated across the codebase)

**LangGraph nodes (`agents/graph.py`):** every node wraps its work in try/except, never re-raises, and instead appends a structured error to `state["errors"]` via `_append_error(state, error)`, leaving the corresponding state field `None`. This lets the pipeline continue producing a report even when one stage fails, while making the failure visible downstream (never silently treated as success).

**Proxy client boundary (`agents/proxy_client.py`):**
```python
class ProxyCallFailed(Exception):
    """Raised on connection errors only. Non-200 HTTP responses are returned, not raised —
    callers (LangGraph nodes) decide how to record guardrail rejections (D-024)."""
```
Pattern: distinguish "the network/transport failed" (raise) from "the proxy responded but rejected the request" (return status + body, let the caller decide). `requests.RequestException` is caught broadly because it also covers non-JSON response bodies (an unhandled 500 from the proxy), and the caller is never allowed to crash on either case.

**Guardrail/middleware layer (`proxy/middleware/`):** each check (injection, PII, schema, rate limit) returns a typed Pydantic result object rather than raising — the caller (`proxy/main.py`) composes these results into the request/response decision. Guardrails are checks, not control-flow exceptions.

## Import Organization

**Python:** stdlib imports first, then third-party (`requests`, `fastapi`), then local package imports (`from proxy...`, `from agents...`). No wildcard imports observed.

**TypeScript:** `import type` grouped separately from value imports at the top of `web/lib/api.ts`; local relative imports (`./types`) after external/none — this file has no external deps, only local types.

## Module Design

**Proxy (`proxy/`):** guardrails live in `proxy/middleware/` as independent, composable checks; `proxy/main.py` wires them into the FastAPI route; `proxy/schemas.py` holds shared Pydantic contracts; `proxy/provider.py` is the sole LLM-provider adapter; `proxy/redteam/` holds the attack pattern library consumed by `injection_detector.py`.

**Agents (`agents/`):** `state.py` (shared contract) + `graph.py` (orchestration/node wiring) + one file per pipeline stage (`extractor.py`, `forensics.py`, `policy_checker.py`, `report_writer.py`) + `proxy_client.py` (the only LLM egress point) + `api.py` (FastAPI surface for the agents service, port 8001 by default).

**Frontend duality:** `frontend/` is the Streamlit app (Python); `web/` is the Next.js/React app (TypeScript). Where both exist, the Next.js version documents when it ports logic from the Streamlit/Python equivalent (see `web/lib/api.ts` comment above) rather than silently reimplementing it differently.

**Web (`web/`):** `web/app/` = route pages only (thin); `web/components/<domain>/` = feature components; `web/components/ui/` = shared primitives (button, card, tabs, select, badge, textarea, collapsible); `web/lib/` = data fetching (`api.ts`), pure helpers (`format.ts`, `utils.ts`, `weakness-heuristics.ts`, `dashboard-data.ts`), fixtures (`sample-attacks.ts`, `sample-receipts.ts`), and shared types (`types.ts`) plus session context (`session.tsx`).

---

*Convention analysis: 2026-09-21*
