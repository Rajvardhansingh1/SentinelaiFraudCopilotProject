# SentinelAI + Fraud Copilot

A reusable LLM guardrail/evaluation platform powering a multi-agent expense/invoice fraud-detection copilot.

## What this project demonstrates

This project combines two engineering problems:

**SentinelAI**
- FastAPI LLM proxy
- prompt-injection/jailbreak detection
- PII and secret scanning
- structured-output validation
- hallucination scoring
- grounding
- token/cost/latency tracking
- rate limiting
- evaluation logging
- red-team playground

**Fraud Copilot**
- OCR-based receipt/invoice extraction
- image tamper forensics
- configurable expense-policy checking
- grounded audit-report generation
- LangGraph orchestration
- human-in-the-loop review

The important architecture rule is simple:

> Fraud Copilot agents never call an LLM provider directly. Every LLM call goes through SentinelAI.

OCR and OpenCV forensics are local processing steps and therefore do not go through the LLM proxy.

## Demo concept

A visitor can either:

1. Submit adversarial prompts in the red-team playground and see SentinelAI evaluate them.
2. Upload/select a receipt and watch extraction → forensics → policy check → report generation.

A sample receipt can contain hidden adversarial text inside the image to demonstrate why OCR output must also be treated as untrusted input.

The final fraud/no-fraud result is never automatically applied. A human reviewer must approve or reject it.

## Running it

**Fraud Copilot is currently paused** — this project is focused on expanding SentinelAI
(the platform layer) on its own. `agents/api.py` (Fraud Copilot's backend) is not part
of the normal run flow; its code stays on disk. One backend service, one frontend.

```bash
# 1. Python deps (repo root)
python -m venv .venv
.venv\Scripts\activate          # Windows; source .venv/bin/activate on Linux/Mac
pip install -r requirements.txt

# 2. Fill in real credentials
copy .env.example .env          # cp on Linux/Mac
# edit .env — at minimum set GROQ_API_KEY

# 3. Start SentinelAI proxy (terminal 1)
.venv\Scripts\python -m uvicorn proxy.main:app --port 8000

# 4. Start the Next.js frontend (terminal 2)
cd web
npm install
npm run dev
```

Open `http://localhost:3000` — redirects to the Red-Team Playground. Sidebar nav covers Playground / Eval Dashboard. `/review` (Receipt Review) still exists on disk but shows a paused notice and isn't linked from the sidebar.

`web/.env.local` (copy from `.env.local.example`) points the frontend at the proxy:
```
NEXT_PUBLIC_PROXY_BASE_URL=http://localhost:8000
```

**The old Streamlit UI (`frontend/`) is retired** (D-038) — kept on disk, not deleted, but no longer the recommended way to run this. If you need it: `.venv\Scripts\python -m streamlit run frontend\app.py` (must use `python -m streamlit`, not bare `streamlit`, or the absolute imports break).

## Architecture

```text
                    ┌──────────────────────────┐
                    │   Next.js UI (web/)       │
                    │ playground / review /     │
                    │ dashboard                 │
                    └──────────┬───────────────┘
                               │
                 ┌─────────────┴──────────────┐
                 │                            │
          Red-team prompt              Fraud Copilot
                 │                     LangGraph agents
                 │                            │
                 └─────────────┬──────────────┘
                               │ LLM calls only
                     ┌─────────▼─────────┐
                     │ SentinelAI Proxy  │
                     │ FastAPI           │
                     ├───────────────────┤
                     │ Injection         │
                     │ PII/secrets      │
                     │ Schema validation │
                     │ Rate limiting     │
                     │ LLM provider      │
                     │ Hallucination     │
                     │ Logging           │
                     └─────────┬─────────┘
                               │
                         Groq / Gemini
```

Local-only processing:

```text
Receipt image
   ├── PaddleOCR/RapidOCR ──> raw OCR text ──> SentinelAI for LLM structuring
   └── OpenCV + EXIF ───────> forensic evidence
```

## Build phases

1. Core SentinelAI proxy — done
2. Evaluation layer — done
3. Red-team playground — done (Streamlit, retired) / rebuilt in `web/`
4. Fraud agents — done
5. Synthetic dataset — done
6. Review UI + evaluation dashboard — done (Streamlit, retired) / rebuilt in `web/`
7. Deployment + hardening — code/config done, not yet live-deployed
8. Frontend rewrite (Streamlit → Next.js) — done, `web/` is now the active UI

## Stack

- Python, FastAPI + Uvicorn, Pydantic
- LangChain + LangGraph
- Groq (primary) / Gemini (fallback)
- Chroma (grounding)
- Microsoft Presidio + regex (PII/secrets)
- RapidOCR (OCR)
- OpenCV + Pillow + exifread (forensics)
- SQLAlchemy + SQLite
- Next.js 14 + TypeScript + Tailwind + shadcn/ui + Recharts (`web/`)
- Pandas + NumPy, Pytest, Vitest
- GitHub Actions

## Data policy

The evaluation dataset is synthetic/lightly templated. It contains genuine-looking and intentionally tampered receipts/invoices with labels. Real company/client data is not part of the project.

## Project memory

| File | Purpose |
|---|---|
| `CLAUDE.md` | Agent operating rules and development workflow |
| `spec.md` | Full spec-driven requirements and phase gates |
| `decision.md` | Durable decisions, conflicts, and open decisions |
| `state.md` | Current continuation state |
| `progress_log.md` | Chronological development history |
| `testing.md` | Test strategy and quality gates |
| `project_explanation.md` | Detailed architecture and design explanation |

## Current status

All 7 original phases implemented and tested (126 Python tests passing). Frontend rewritten from Streamlit to Next.js (`web/`) — active UI. Not yet deployed live anywhere (Render/HF Spaces/Vercel accounts still needed). **Fraud Copilot is paused** (D-040) — active work is expanding SentinelAI itself (see `phase_dev_upgrade.md`). See `state.md` for the exact continuation point and open items.
