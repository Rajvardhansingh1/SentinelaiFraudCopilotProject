# Technology Stack

**Analysis Date:** 2026-09-21

## Languages

**Primary:**
- Python 3 (3.10+ syntax: `X | None` unions) - backend: `proxy/`, `agents/`, `frontend/` (retired Streamlit), `tests/`
- TypeScript - active frontend: `web/` (Next.js App Router, strict mode per `web/tsconfig.json`)

**Secondary:**
- YAML - policy config `agents/policies/expense_policy.yaml`, deploy config `deploy/render.yaml`, CI `.github/workflows/ci.yml`

## Runtime

**Environment:**
- Python via conda env `FraudCopilotProject` (per `CLAUDE.md` — must `conda activate FraudCopilotProject` before running anything) or a `venv` (per `README.md` quickstart)
- Node.js for `web/` (Next.js 14 requires Node 18.17+)

**Package Manager:**
- Python: `pip` with `requirements.txt` (root) — no lockfile (no `requirements.lock`/`poetry.lock`), so installed versions float within unpinned ranges
- Node: `npm` with `web/package-lock.json` (present, pinned)

## Frameworks

**Core (Python backend):**
- FastAPI - two separate services: `proxy/main.py` (SentinelAI guardrail proxy, port 8000) and `agents/api.py` (Fraud Copilot API, port 8001)
- Uvicorn - ASGI server for both FastAPI apps
- Pydantic + `pydantic-settings` - request/response schemas (`proxy/schemas.py`) and env-driven config (`proxy/config.py`)
- LangGraph - agent pipeline orchestration, `agents/graph.py` (`StateGraph` with `extractor → forensics → policy_checker → report_writer` nodes)
- LangChain / `langchain-groq` - listed in `requirements.txt`; the actual LLM calls in `proxy/provider.py` use the raw `groq` and `google-generativeai` SDKs directly rather than LangChain wrappers
- SQLAlchemy - ORM for both `proxy/db/` and `agents/db/` (SQLite by default)
- Streamlit - `frontend/app.py`, **retired** (see D-038 in `decision.md`); kept on disk but not the active UI

**Core (web/ frontend):**
- Next.js 14.2.5 (App Router) - `web/app/` with `layout.tsx`, `page.tsx`, and route subfolders `playground/`, `review/`, `dashboard/`
- React 18.3.1 / React DOM 18.3.1
- Tailwind CSS 3.4.7 + `tailwind-merge` + `class-variance-authority` - styling, `web/tailwind.config.ts`
- Radix UI primitives (`@radix-ui/react-collapsible`, `-select`, `-tabs`) - unstyled component base (shadcn/ui pattern)
- `lucide-react` - icon set
- `recharts` 2.15.4 - eval dashboard charts

**Testing:**
- Pytest - Python test suite, config `pytest.ini` (`testpaths = tests`), tests in `tests/` (unit + `tests/agents/`, `tests/fixtures/`)
- Vitest 2.0.5 - `web/` unit/component tests, config `web/vitest.config.ts` (jsdom environment, excludes `tests/e2e/**`), `@testing-library/react` for component rendering
- Playwright 1.45.3 - `web/` end-to-end browser tests, config `web/playwright.config.ts`, specs under `web/tests/e2e/`

**Build/Dev:**
- `next dev` / `next build` / `next start` / `next lint` - `web/package.json` scripts
- PostCSS + Autoprefixer - `web/postcss.config.js`
- TypeScript 5.5.4 - strict mode, path alias `@/*` → repo root (`web/tsconfig.json`)
- GitHub Actions - `.github/workflows/ci.yml`

## Key Dependencies

**Critical:**
- `groq` + `langchain-groq` - primary LLM provider client, `proxy/provider.py::GroqProvider` (model `openai/gpt-oss-20b`)
- `google-generativeai` - fallback LLM provider, `proxy/provider.py::GeminiProvider` (model `gemini-1.5-flash`)
- `langgraph` - defines the 4-node fraud-review pipeline as a compiled state graph
- `presidio-analyzer` / `presidio-anonymizer` - NER-based PII detection, optional/lazy-imported in `proxy/middleware/pii_scanner.py` (falls back to regex-only if unavailable; requires separate `spacy` model download `en_core_web_lg`)
- `rapidocr-onnxruntime` - local OCR engine, `agents/extractor.py::run_ocr` (lazy import)
- `opencv-python` (`cv2`) + `pillow` + `exifread` - image forensics: Error Level Analysis and EXIF metadata checks, `agents/forensics.py`
- `chromadb` - optional persisted vector store for grounding/hallucination scoring, `proxy/eval/grounding.py::ChromaStore` (lazy import; falls back to an in-process TF-IDF store `InMemoryTFIDFStore` when unavailable)
- `sentence-transformers` - listed in `requirements.txt` for embeddings (chromadb default embedding path); not directly imported in reviewed source files
- `slowapi` - listed in `requirements.txt` for rate limiting, but the actual implementation in `proxy/middleware/rate_limiter.py` is a hand-rolled in-process counter, not slowapi — likely an unused/legacy dependency

**Infrastructure:**
- `sqlalchemy` - `proxy/db/session.py`, `agents/db/session.py`; SQLite via `DATABASE_URL` (default `sqlite:///./data/logs.db`), `StaticPool` used when `:memory:` (tests)
- `python-dotenv` (via `pydantic-settings` `env_file=".env"`) - local env loading, `proxy/config.py`
- `pyyaml` - loads `agents/policies/expense_policy.yaml`
- `pandas` + `numpy` - eval dataset/metrics processing (`proxy/eval/`, `eval_reports/`)
- `requests` - synchronous HTTP client used by `agents/proxy_client.py::call_proxy` and `frontend/lib/proxy_client.py` to call the SentinelAI proxy over HTTP
- `python-multipart` - required by FastAPI for `UploadFile`/`Form` multipart parsing (`agents/api.py::analyze_receipt`)

## Configuration

**Environment:**
- `.env` (repo root, git-ignored) loaded by `pydantic-settings` in `proxy/config.py::Settings`; `.env.example` documents the shape
- Key settings: `groq_api_key`, `gemini_api_key`, `sentinelai_host`/`port`, `agents_api_port`, `rate_limit_per_session`, `database_url`, `chroma_persist_dir`, `env` (`development`/`production`), `allowed_origins` (comma-separated CORS list)
- `web/.env.local` (copy of `web/.env.local.example`) sets `NEXT_PUBLIC_PROXY_BASE_URL` and `NEXT_PUBLIC_AGENTS_API_BASE_URL` so the Next.js app can reach both Python services
- `PROXY_BASE_URL` env var also read directly via `os.environ` in `agents/proxy_client.py` (separate from the pydantic-settings-managed proxy config) and `frontend/lib/proxy_client.py`

**Build:**
- `web/next.config.js`, `web/tailwind.config.ts`, `web/postcss.config.js`, `web/tsconfig.json`
- No Python build step — services run directly via `uvicorn`

## Platform Requirements

**Development:**
- conda env `FraudCopilotProject` (mandated by `CLAUDE.md`) or Python venv, Python 3.10+
- Node.js + npm for `web/`
- Three local processes to run the full stack: `uvicorn proxy.main:app --port 8000`, `uvicorn agents.api:app --port 8001`, `npm run dev` (Next.js on port 3000)

**Production:**
- `deploy/render.yaml` - Render.com web service for the SentinelAI proxy only (`buildCommand: pip install -r requirements.txt`, `startCommand: uvicorn proxy.main:app --host 0.0.0.0 --port $PORT`, persistent disk mounted at `/opt/render/project/data` for SQLite + Chroma, `ENV=production` disables `/docs`/`/redoc`/`/openapi.json`)
- `deploy/huggingface_space/` - alternate/additional deployment target present in the repo (not inspected in depth for this pass)
- Per `README.md` Build Phases, deployment is "code/config done, not yet live-deployed"

---

*Stack analysis: 2026-09-21*
