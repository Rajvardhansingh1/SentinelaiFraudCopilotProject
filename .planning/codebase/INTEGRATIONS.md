# External Integrations

**Analysis Date:** 2026-09-21

## APIs & External Services

**LLM Providers:**
- Groq - primary LLM provider, `proxy/provider.py::GroqProvider`
  - SDK: `groq` Python client (`from groq import Groq`), lazy-imported inside `generate()`
  - Model: `openai/gpt-oss-20b` (comment notes `llama-3.1-8b-instant` was retired by Groq — update the model string here if Groq retires this one too)
  - Auth: `groq_api_key` setting, sourced from `GROQ_API_KEY` env var (`proxy/config.py`)
  - Call shape: `client.chat.completions.create(model=..., messages=[{"role", "content"}, ...])`
- Google Gemini - fallback LLM provider, `proxy/provider.py::GeminiProvider`
  - SDK: `google-generativeai` (`import google.generativeai as genai`), lazy-imported inside `generate()`
  - Model: `gemini-1.5-flash`
  - Auth: `gemini_api_key` setting, sourced from `GEMINI_API_KEY` env var
  - Call shape: flattens `messages` into a single `"role: content"`-joined prompt string, then `genai.GenerativeModel(model).generate_content(prompt)` — no native multi-turn chat structure used, unlike the Groq path
- Fallback wiring: `proxy/provider.py::FallbackProvider` wraps both — tries Groq first, catches `ProviderError`, retries once against Gemini. `get_provider()` is the FastAPI dependency injected into `POST /v1/generate` (`proxy/main.py`).

**LLM access boundary (architectural invariant, D-002):**
- Neither `agents/` nor `frontend/`/`web/` ever call Groq/Gemini directly. All LLM calls go through `proxy/main.py`'s `POST /v1/generate` endpoint.
- `agents/proxy_client.py::call_proxy` (Python, via `requests`) is the only path from LangGraph nodes to the proxy.
- `web/lib/api.ts::postGenerate` (TypeScript, via `fetch`) is the only path from the Next.js playground UI to the proxy.
- Both clients follow a "never throw" contract: network/parse failures are converted into a synthetic error envelope (`proxy_unreachable` / 503) rather than propagating exceptions, so callers always get a uniform response shape.

## Data Storage

**Databases:**
- SQLite, two separate SQLAlchemy-managed databases:
  - Proxy call log DB - `proxy/db/models.py` (`CallLog`), `proxy/db/session.py`, connection string `database_url` setting → env `DATABASE_URL` (default `sqlite:///./data/logs.db`)
  - Agents review-decision DB - `agents/db/models.py` (`ReviewDecision`), `agents/db/session.py`, same connection mechanism, imports `proxy.db.models.Base` shared metadata
  - `StaticPool` is used when the URL contains `:memory:` (in-memory SQLite for tests)
- No external/managed database service — SQLite file(s) on local disk or the Render persistent disk in production

**Vector/Grounding Store:**
- ChromaDB (optional) - `proxy/eval/grounding.py::ChromaStore`, `chromadb.PersistentClient(path=settings.chroma_persist_dir)`, env var `CHROMA_PERSIST_DIR` (default `./data/chroma`)
- Falls back automatically to `InMemoryTFIDFStore` (dependency-free, process-local, non-persistent cosine-similarity store) if `chromadb` import fails — selection logic in `get_grounding_store()`

**File Storage:**
- Local filesystem only. Uploaded receipt images are written to `tempfile.gettempdir()` with a UUID filename in `agents/api.py::analyze_receipt`, processed, then deleted in a `finally` block (`tmp_path.unlink(missing_ok=True)`) — no object storage (S3/GCS/etc.) integration.

**Caching:**
- None.

## Authentication & Identity

**Auth Provider:**
- None. No user login/session-auth system. `session_id` is a caller-supplied opaque string used only for per-session rate limiting and log correlation, not authentication.

## PII / Security Detection (in-process, not a hosted API)

- Microsoft Presidio (`presidio-analyzer`, `presidio-anonymizer`) - optional NER-based PII detection, `proxy/middleware/pii_scanner.py::_get_presidio_analyzer`
  - Lazy-imported and cached (`_presidio_analyzer`/`_presidio_checked` module globals); silently falls back to regex-only detection if Presidio or its underlying `spacy` model (`en_core_web_lg`, must be downloaded separately) isn't installed
  - Runs entirely locally — no external API call
- Regex-based secondary detection (always active, no dependency): email, phone, card-number, and API-key patterns in `proxy/middleware/pii_scanner.py::PATTERNS`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Datadog/etc.). Errors are caught by a global FastAPI exception handler in both `proxy/main.py` and `agents/api.py`, logged server-side via stdlib `logging`, and returned as a generic `internal_error` envelope to the client (never leaks tracebacks).

**Logs:**
- stdlib `logging` module, logger names `"proxy"` and `"agents.api"`.
- Every proxy call is also persisted as a structured row in the `CallLog` SQLite table (`proxy/main.py::_log`) — provider, model, latency, token counts, guardrail results, error code — this doubles as the audit trail surfaced by the eval dashboard (`GET /v1/calls` in `agents/api.py`).

## CI/CD & Deployment

**Hosting:**
- Render.com - `deploy/render.yaml`, web service `sentinelai-proxy`, Python env, `startCommand: uvicorn proxy.main:app --host 0.0.0.0 --port $PORT`, persistent 1GB disk at `/opt/render/project/data` for the SQLite DB and Chroma persistence dir. Only the SentinelAI proxy service is defined here — no Render service definition found for `agents.api` or `web/`.
- Hugging Face Spaces - `deploy/huggingface_space/` directory present as an alternate deployment target (not deeply inspected in this pass).

**CI Pipeline:**
- GitHub Actions - `.github/workflows/ci.yml`

## Environment Configuration

**Required env vars (backend, `.env` / `proxy/config.py::Settings`):**
- `GROQ_API_KEY` - Groq auth, required for the primary LLM path
- `GEMINI_API_KEY` - Gemini auth, required for the fallback LLM path
- `SENTINELAI_HOST`, `SENTINELAI_PORT` - proxy bind address (defaults `0.0.0.0`:`8000`)
- `AGENTS_API_PORT` - Fraud Copilot API port (default `8001`)
- `RATE_LIMIT_PER_SESSION` - per-session call cap (default `8`)
- `DATABASE_URL` - SQLAlchemy connection string (default `sqlite:///./data/logs.db`)
- `CHROMA_PERSIST_DIR` - Chroma persistence directory (default `./data/chroma`)
- `ENV` - `development` (default, exposes `/docs`/`/redoc`/`/openapi.json`) or `production` (disables them)
- `ALLOWED_ORIGINS` - comma-separated CORS allowlist (default `http://localhost:3000,http://localhost:8501`)
- `PROXY_BASE_URL` - read directly by `agents/proxy_client.py` and `frontend/lib/proxy_client.py` via `os.environ`, independent of the `Settings` class, to locate the running proxy service (default `http://localhost:8000`)

**Required env vars (frontend, `web/.env.local`):**
- `NEXT_PUBLIC_PROXY_BASE_URL` - default `http://localhost:8000`, used in `web/lib/api.ts`
- `NEXT_PUBLIC_AGENTS_API_BASE_URL` - default `http://localhost:8001`, used in `web/lib/api.ts`

**Secrets location:**
- `.env` at repo root (git-ignored) for backend secrets; `web/.env.local` for frontend-visible (non-secret) base URLs. `deploy/render.yaml` declares `GROQ_API_KEY`/`GEMINI_API_KEY` as `sync: false` (set manually in the Render dashboard, never committed).

## Webhooks & Callbacks

**Incoming:**
- None. No webhook receivers.

**Outgoing:**
- None beyond the direct Groq/Gemini API calls described above (request/response, not webhook-style).

---

*Integration audit: 2026-09-21*
