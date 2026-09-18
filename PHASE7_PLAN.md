# Phase 7 Plan — Deployment & Hardening

Planning only. No app code, no spec.md/decision.md/state.md/progress_log.md edits.

## 1. Scope recap

Phase 7 does not build new features. It takes what Phases 1-6 already built (proxy,
playground, agents, dataset, review UI/dashboard) and puts it somewhere public, makes
free-tier failure modes (cold start, rate limits) visible instead of silent, wires CI,
and closes out with a security review and a final measured evaluation report. Per D-019
the caching pattern already exists (caller-side, per-operation) — Phase 7 extends it to
Phase 6's sample-receipt path, it doesn't invent a new caching layer.

## 2. File plan

```
deploy/
  render.yaml                          # proxy deploy config (pending OD-008)
  huggingface_space/
    README.md                          # HF Spaces YAML frontmatter + space docs
.github/
  workflows/
    ci.yml                             # pytest on push — no .github/ dir exists yet, confirmed
frontend/
  lib/
    health_check.py                    # new — cold-start probe, see §5
```

No `.github/` directory currently exists in the repo (confirmed via glob) — `ci.yml` is a
net-new file/directory, not an edit.

## 3. FastAPI proxy deployment

**OD-008 is open** (Render vs Railway). Original spec section 9 allows either. This plan
writes a `render.yaml` because Render's `render.yaml` is declarative and matches the
"free web service, sleeps after ~15min" behavior spec.md/section 9/10 explicitly design
around — but this is a proposal, not a resolution. **Flagging: OD-008 must be resolved
(dated decision.md entry) before or during Phase 7 execution.** If Railway is chosen
instead, swap `render.yaml` for a Railway `railway.json`/`Procfile` — same build/start
commands, different host-specific file.

`deploy/render.yaml` sketch:

```yaml
services:
  - type: web
    name: sentinelai-proxy
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn proxy.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: RATE_LIMIT_PER_SESSION
        value: "8"
      - key: DATABASE_URL
        value: sqlite:////opt/render/project/data/logs.db
      - key: CHROMA_PERSIST_DIR
        value: /opt/render/project/data/chroma
      - key: ENV
        value: production
    disk:
      name: sentinelai-data
      mountPath: /opt/render/project/data
      sizeGB: 1
```

Notes:
- `startCommand` uses `$PORT` (Render injects it), not `SENTINELAI_PORT` from
  `.env.example` — `proxy/config.py`'s `sentinelai_port` is for local dev; production
  binds whatever the host assigns. No code change needed, just don't rely on the env var
  in the deploy start command.
- `GROQ_API_KEY`/`GEMINI_API_KEY` set as Render dashboard secrets (`sync: false`), never
  committed — consistent with CLAUDE.md §12 and cross-phase invariant #7.
- `disk` mount is required for SQLite (D-009) and Chroma persistence to survive restarts
  on Render's free tier — free-tier disks are ephemeral without this; confirm Render's
  free-plan disk availability before execution, since Render's free tier has historically
  restricted persistent disks to paid plans. If unavailable, this is another OD-008-adjacent
  gap to flag at execution time (SQLite/Chroma would reset on every deploy/restart).
- `/health` already exists (`proxy/main.py:29`) — reused as-is, not rebuilt.

## 4. Streamlit deployment (Hugging Face Spaces)

`deploy/huggingface_space/README.md` — HF Spaces reads YAML frontmatter to configure the
Space itself:

```markdown
---
title: SentinelAI Fraud Copilot
emoji: 🛡️
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: "1.x"   # pin to the streamlit version in requirements.txt at execution time
app_file: frontend/app.py
pinned: false
---

# SentinelAI + Fraud Copilot — Demo

Public demo of the SentinelAI proxy + Fraud Copilot playground/review UI.
```

`PROXY_BASE_URL` (already read via `os.environ.get("PROXY_BASE_URL", ...)` in
`frontend/lib/proxy_client.py:5`) is set as an HF Space **secret/variable** (Settings →
Variables and secrets) pointing at the deployed Render URL, e.g.
`https://sentinelai-proxy.onrender.com`. No code change required — the existing fallback
to `http://localhost:8000` stays for local dev.

Deployment mechanics (git push to the HF Space's own git remote, or HF's GitHub Action
sync) are an execution-time step, not a planning artifact — noted here only as a
prerequisite: the HF Space repo must include `requirements.txt` and `frontend/`.

## 5. Cold-start UX

Render/Railway free tiers sleep after ~15min idle; first request after sleep takes
~20-30s (spec.md, original spec §9/§10). Neither is implemented yet — Phase 3 built
per-session rate limiting and the cached-fallback pattern, not a wake-up indicator.

**New file: `frontend/lib/health_check.py`** (small, mirrors `proxy_client.py`'s style):

```python
def ping_proxy(timeout: float = 3.0) -> bool:
    """GET /health with a short timeout. False = likely cold/sleeping or down."""
    try:
        resp = requests.get(f"{PROXY_BASE_URL}/health", timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False
```

`frontend/app.py` calls `ping_proxy()` once per session on first render (cache in
`st.session_state` so it's not re-checked every rerun). If it fails/times out, show
`st.info("Waking up the server... this can take ~20-30s on the first request.")` and
retry with a longer timeout (e.g. 35s) before letting the user proceed, or just let the
first real `/v1/generate` call eat the cold-start latency while the spinner is visible —
either is acceptable; the concrete choice belongs to execution, this plan just fixes
where the logic lives (`health_check.py`, called from `app.py`, not duplicated per-page).

Why a new file and not inline in `app.py`: it's reused across every page (playground,
review UI, dashboard) that hits the proxy, and it's the kind of thing a failure-mode test
(§10) wants to import and call directly without going through Streamlit.

## 6. Response/prompt caching for demo paths — coordination point, not new work

D-019 already establishes the pattern: caller owns cached fallback content, shown on
429. Phase 3 implemented it for the playground (`frontend/data/sample_attacks.py`,
`find_cached()`, `frontend/components/redteam_playground.py:14`). Original spec §10 also
calls for the same treatment on Fraud Copilot's sample receipts.

**Phase 7's job is NOT to build a second caching mechanism.** It is to confirm, at
execution time, that Phase 6's review UI sample-receipt fast path follows the identical
D-019 pattern (a `frontend/data/sample_receipts.py`-equivalent with a `find_cached()`-
equivalent, checked on a 429 from `/v1/generate`). If Phase 6's plan already covers this,
Phase 7 just verifies it in the deployment smoke test (§10) rather than re-implementing.
Flagging as a coordination point for whoever plans/executes Phase 6.

## 7. Live quota badge

Phase 3's `get_call_count()` (`frontend/lib/session.py:12`) is **per-session**, displayed
as `st.caption(f"Session calls used: {get_call_count()}")` — this satisfies "quota
badge" for the individual visitor's own usage, which is what D-020 and spec.md's rate
limit (8/session) actually gate on.

The original spec's "API calls: 7/10 used today" phrasing (§10) reads as a *global*
daily counter against the real Groq/Gemini free-tier quota, which is a different
mechanism — it would need a shared counter (e.g. a row in the existing SQLite logs DB,
incremented per proxy call, reset daily) exposed via a small `/quota` endpoint or read
directly by the dashboard from `proxy/db/`.

Proposal: don't build a second tracking system. The proxy's existing `proxy/db/`
observability logging (S7) already records every call — Phase 7 adds one cheap read: a
`GET /quota` endpoint (or the dashboard queries the logs DB directly, since it's SQLite
and same-process-readable) returning `{"calls_today": N, "limit": ...}`, computed via a
`WHERE created_at >= today` count. This is additive to existing logging, not new
infrastructure. Flag: whether "N" is measured against Groq's actual daily free-tier cap
or an arbitrary display number is an execution-time decision — original spec's "10" is
illustrative, same footnote as D-020 already made for the per-session number.

Per-session badge (Phase 3, done) and global badge (Phase 7, additive) are not the same
feature — this plan is explicit that both exist rather than assuming Phase 3 covers it.

## 8. CI — `.github/workflows/ci.yml`

No `.github/` directory exists yet (confirmed). New file:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest
```

Matches spec.md's exact Phase 7 requirement ("CI pytest run on push") — nothing more
(no lint/coverage/matrix unless the project later asks for it; YAGNI).

## 9. Security review and final evaluation report

Both reuse existing tooling, per the CLAUDE.md skill list and prior phases:

- **Final security review**: run the `security-review` skill (listed in CLAUDE.md §13,
  "Security analysis for proxy, uploads, secrets, PII, APIs, and adversarial inputs")
  against the deployed/deployable state of the repo. Output becomes the "Security review
  has no unresolved release-blocking issue" acceptance criterion evidence. No new
  security tooling is built for Phase 7.
- **Final evaluation report**: run `scripts/run_eval_suite.py` — **this script does not
  exist yet** (confirmed via glob; `scripts/` directory not present). It is Phase 5's
  deliverable (Synthetic Dataset & Evaluation), not Phase 7's. Phase 7 depends on it
  existing and executes it, recording the measured precision/recall/hallucination
  numbers as the "final metrics are documented" acceptance criterion. If Phase 5 hasn't
  shipped this script by the time Phase 7 executes, that's a blocking dependency, not
  something Phase 7 should reimplement.

## 10. Test plan (Phase 7 test gate, from spec.md)

| Gate item | Concrete check |
|---|---|
| CI | `.github/workflows/ci.yml` green on push (§8) |
| Deployment smoke tests | New `tests/test_deployment_smoke.py` (or a manual checklist if no live endpoint in CI): `GET /health` on the deployed Render URL returns 200; deployed HF Space loads `frontend/app.py` and renders the playground; one live `/v1/generate` round-trip against the deployed proxy from the deployed Streamlit app succeeds |
| Browser end-to-end tests | Playwright (per CLAUDE.md §13 skill list) against the deployed HF Space URL: load playground, submit a sample attack, confirm injection block renders; load review UI, submit a sample receipt, confirm verdict + human-approval gate renders (not auto-decision, invariant #4) |
| Security scan/review | `security-review` skill output, no unresolved release-blocking finding (§9) |
| Evaluation suite | `scripts/run_eval_suite.py` (Phase 5 dependency) run against the synthetic dataset, results recorded, not claimed without measurement (invariant #6) |
| Failure-mode tests | New `tests/test_failure_modes.py`: (a) simulate proxy-down — `ping_proxy()` returns `False` when the health endpoint is unreachable (mock `requests.get` to raise/timeout); (b) simulate quota-exhausted — existing pattern from `redteam_playground.py`'s `handle_response()` already covers 429→cached-fallback, extend the same test style to whatever Phase 6 builds for sample receipts (§6 coordination point) |

## 11. Open questions / decisions needed (flagged only, not resolved here)

- **OD-008 (Render vs Railway)** — open. This plan drafts `render.yaml` as a concrete
  starting point per spec.md's ordering ("Render or Railway") and because Render's
  declarative config fits the free-tier sleep/cold-start behavior the rest of Phase 7
  is built around, but the actual choice needs a dated `decision.md` entry before
  execution, and needs to confirm free-tier persistent-disk availability (§3) either way.
- **OD-011 (switch grounding store to real Chroma)** — open, and decision.md explicitly
  says "before Phase 7 deployment at the latest." spec.md's Phase 7 baseline lists
  "Chroma: embedded/persisted" as a deployment target, but D-018's shipped default is
  `InMemoryTFIDFStore` (process-local, non-persistent). **This is a prerequisite gap,
  not a Phase 7 task**: Phase 7 cannot honestly claim "Chroma embedded/persisted" is
  deployed until `get_grounding_store()` is switched to `ChromaStore` (already written
  per D-018, just not selected) and `chromadb`'s onnxruntime dependency weight is
  accepted. Flagging explicitly rather than assuming it's already resolved, per this
  task's instructions.
- **Global quota badge exact source of truth (§7)** — whether it reads real Groq/Gemini
  account quota (would need provider usage API integration, not currently planned
  anywhere) or a simple "count of our own calls today" proxy — this plan proposes the
  latter (cheap, uses existing logging) but it's a scope call worth a decision.md entry
  if the demo needs to reflect actual provider-side remaining quota.
- **Render free-tier persistent disk availability** — needs confirming at execution
  time; if unavailable, SQLite/Chroma persistence (D-009, OD-011) would need Supabase
  or an alternate persisted store sooner than "if it outgrows a single file" implies.
