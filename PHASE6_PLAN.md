# Phase 6 Plan — Review UI & Evaluation Dashboard

Status: PLANNING ONLY. No app code touched. Depends on Phase 4 (agents/graph.py) and Phase 5 (sample receipts, dataset) being implemented — this plan assumes their contracts as described in spec.md, not their actual code.

## 1. Scope recap

Two new Streamlit pages on top of the existing Phase 3 app: a **Review Screen** where a human uploads (or picks a sample) receipt, runs it through the Phase 4 LangGraph pipeline, sees all evidence/verdict/guardrail metadata, and makes the mandatory human approve/reject call (D-004 — system never decides); and an **Eval Dashboard** that reads the existing `CallLog` table (Phase 1/2) to show guardrail catches, hallucination scores, cost, latency, and traffic. Both must reuse Phase 3's conventions (`session.py`, component-per-file, proxy_client-style wrappers) rather than inventing new patterns. Multi-page nav is new — Phase 3 only had one page.

## 2. File plan

```
frontend/
├── app.py                          # MODIFIED: add nav, keep playground working
├── components/
│   ├── redteam_playground.py       # unchanged
│   ├── review_screen.py            # NEW — Phase 6
│   └── eval_dashboard.py           # NEW — Phase 6
├── lib/
│   ├── session.py                  # unchanged (get_session_id/get_call_count reused as-is)
│   ├── proxy_client.py             # unchanged
│   ├── pipeline_client.py          # NEW — thin wrapper around agents/graph.py invocation
│   └── dashboard_data.py           # NEW — read-only query module over CallLog
└── data/
    └── sample_attacks.py           # unchanged; sample receipts live in Phase 5's data/synthetic_receipts/
```

**Nav approach:** sidebar radio in `app.py`, not Streamlit's native `pages/` directory. Reason (ladder rung 2 — reuse what's there): `app.py` currently does `st.set_page_config(...); redteam_playground.render()` directly with no page-registration scaffolding, and a `pages/` directory would force renaming `app.py`'s role and duplicate `st.set_page_config` per file (only one call allowed per app, first one wins) — a sidebar radio is a smaller diff and keeps one entrypoint:

```python
import streamlit as st
from frontend.components import redteam_playground, review_screen, eval_dashboard

st.set_page_config(page_title="SentinelAI Playground", page_icon="🛡️")
page = st.sidebar.radio("Page", ["Red-Team Playground", "Review Receipt", "Eval Dashboard"])
if page == "Red-Team Playground":
    redteam_playground.render()
elif page == "Review Receipt":
    review_screen.render()
else:
    eval_dashboard.render()
```

This does not break Phase 3's `test_playground_ui.py`, which does `AppTest.from_file(APP_PATH)` then `at.selectbox[0]...` / `at.button[0]...` — those indices only hold if the playground is the default-selected radio option (index 0), which it is above. Flag: confirm at execution time that adding a `st.sidebar.radio` widget before the playground doesn't shift `at.selectbox[0]`/`at.button[0]` indices in that existing test (radio and selectbox are different widget types in `AppTest`, so they shouldn't collide, but this needs a real run to confirm, not just this plan).

## 3. Review UI design (`components/review_screen.py`)

### Input
- `st.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg"])`.
- Sample-receipt fast path: buttons per Phase 5 sample, e.g. `st.button("Use sample: Genuine receipt")` / `st.button("Use sample: Tampered receipt")`, reading from Phase 5's `data/synthetic_receipts/` (exact filenames TBD by Phase 5 — this plan does not invent them). Mirrors D-019's pattern (Phase 3's sample-attack cached path): each caller owns its own sample content, not the proxy.

### Pipeline invocation — in-process, not HTTP
The original spec's repo structure lists no service wrapper around `agents/graph.py`, and its sequence diagram shows `UI->>EX` directly invoking the Extractor agent (not through an HTTP hop). LangGraph is a Python library, not a deployed service in this architecture — the FastAPI proxy is the only HTTP boundary, and it sits *between* agents and the LLM provider, not between the UI and the agents. **Proposal (needs confirmation once Phase 4 ships):** `frontend/lib/pipeline_client.py` does a direct import:

```python
from agents.graph import run_pipeline  # exact name TBD by Phase 4

def run_on_receipt(image_bytes: bytes, filename: str) -> dict:
    """Runs the compiled LangGraph graph in-process. Returns the graph's final state
    (extraction, forensics, policy, report, verdict, confidence, hallucination%, guardrails)."""
    return run_pipeline(image_bytes, filename)
```
Streamlit already runs as a single long-lived Python process per session, so an in-process call is consistent with D-005 (Streamlit baseline) and avoids inventing a second service + auth boundary for zero benefit (YAGNI). Flag as an open question if Phase 4 instead exposes the graph only via a CLI/script entrypoint — then `pipeline_client.py` would need to shell out instead, which is worse and should be avoided when Phase 4 is planned.

### Evidence panels
Render the graph's final state as three side-by-side (or stacked on narrow viewports) `st.expander` / bordered `st.container(border=True)` sections, each labeled with its source agent, per spec.md's Component Specifications ("Review Screen ... shows the verdict, every piece of evidence, and all guardrail metadata ... side by side"):

1. **Extraction evidence** — vendor, date, line items, total (from `ReceiptFields`), explicit "missing" marker per OD-006 once resolved.
2. **Forensics evidence** — ELA/EXIF tamper-likelihood output, no LLM/guardrail metadata attached (S13 has no LLM dependency).
3. **Policy evidence** — triggered rules, compliant flag (`PolicyVerdict`), plus that call's guardrail block (injection/pii/hallucination) since it went through SentinelAI.

### System verdict block (bordered, labeled "System says")
```python
with st.container(border=True):
    st.subheader("System Assessment (not a decision)")
    st.metric("Verdict", report["verdict"])
    st.metric("Confidence", f"{report['confidence']:.0%}")
    st.metric("Hallucination %", f"{report['hallucination_pct']:.1%}")
    st.caption("Grounding sources:")
    st.write(report["grounding_sources"])
    st.caption("This is model output, not a final decision. A human must approve or reject below.")
```

### Human decision block (separate bordered section, visually distinct)
```python
with st.container(border=True):
    st.subheader("Human Review — Final Decision")
    st.warning("The system above never auto-approves or auto-rejects. You decide.")
    col1, col2 = st.columns(2)
    approve = col1.button("Approve", type="primary")
    reject = col2.button("Reject", type="secondary")
    notes = st.text_area("Reviewer notes (optional)")
    if approve or reject:
        record_review_decision(...)   # see §5
        st.success(f"Recorded: {'Approved' if approve else 'Rejected'} by reviewer.")
```
Structural separation satisfies D-004 ("UI must clearly separate model verdict/evidence from the human final action") two ways: (a) two distinct `st.container(border=True)` blocks with different headers/copy ("System Assessment (not a decision)" vs "Human Review — Final Decision"), (b) the approve/reject widgets are the *only* thing that writes to the decision-persistence layer — nothing in the system block can trigger a stored decision.

## 4. Dashboard design (`components/eval_dashboard.py` + `lib/dashboard_data.py`)

`dashboard_data.py` is a thin read-only query module over `CallLog` via `proxy.db.session.get_session()` (reuse, not a new logging path, per the task's own instruction):

```python
from proxy.db.session import get_session
from proxy.db.models import CallLog

def fetch_calls(since: datetime | None = None) -> list[CallLog]:
    with get_session() as s:
        q = s.query(CallLog)
        if since:
            q = q.filter(CallLog.created_at >= since)
        return q.order_by(CallLog.created_at.desc()).all()
```

Dashboard renders from `fetch_calls()`:
- **Traffic/call counts** — count by `operation` (extract/policy_check/report/playground), by day.
- **Guardrail catches** — count where `guardrails["injection"]["flagged"]` or `guardrails["pii"]["found"]` is true, pulled out of the JSON column.
- **Hallucination scores** — histogram/line of `guardrails["hallucination"]["score"]` over time, split grounded vs ungrounded mode.
- **Cost** — sum/avg `cost_estimate_usd`, by provider.
- **Latency** — avg/p95 `latency_ms`, by operation.
- **Filters** — time range (`st.date_input` or a "last N hours" selectbox), operation type, provider — all are existing columns, no schema change needed.

Charts: `st.line_chart` / `st.bar_chart` (stdlib-adjacent, already a Streamlit dependency — no new charting library, ladder rung 5).

### Refresh strategy — OD-009 is explicitly open, do not resolve it here

Three concrete options, recommendation given but left for a real decision.md entry when Phase 6 is executed:

1. **Manual "Refresh" button** — `st.button("Refresh")` re-runs `fetch_calls()`. Simplest, zero background cost, but stale between clicks.
2. **Streamlit auto-rerun via `st.rerun()` + `time.sleep` loop** — polling inside the page. Rejected as a recommendation: blocks the Streamlit script thread and is a known anti-pattern (freezes other interaction in that session).
3. **`st_autorefresh`-style interval using `st.query_params` / a lightweight timer with `streamlit-autorefresh` component** — requires a new dependency, against ladder rung 5 (no new dep for a few lines).

**Recommendation:** option 1 (manual refresh button), since the dashboard is a demo/reviewer tool, not a live ops screen, and Streamlit already reruns the whole script on any widget interaction (so filter changes double as a refresh for free). This still needs an explicit decision.md entry before Phase 6 execution closes OD-009 — do not treat this recommendation as accepted.

## 5. Approve/reject persistence — needs a decision.md entry

No existing table stores human review decisions; `CallLog` is proxy call telemetry, not application-level review state, and mixing them would blur S7 (proxy observability) with S15/Review Screen (application layer) — a D-001 layering concern (SentinelAI stays domain-agnostic; a `ReviewDecision` row is fraud-domain data and does not belong in `proxy/db/models.py`).

**Proposal:** new table in `agents/db/models.py` (or `frontend/db/models.py` if Phase 4 doesn't already own a DB module — exact location depends on where Phase 4 lands its own state, flag this) — a fresh SQLAlchemy model, e.g.:

```python
class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    receipt_ref: Mapped[str] = mapped_column(String)          # filename or sample id
    system_verdict: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    hallucination_pct: Mapped[float] = mapped_column(Float)
    human_decision: Mapped[str] = mapped_column(String)        # "approved" | "rejected"
    reviewer_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

This is a real DB-contract change (S7/S11 territory per the task) and **must get its own decision.md entry** before Phase 6 execution — specifically: (a) which module owns the table, (b) whether it lives in the same SQLite file as `CallLog` (simplest — one `database_url`, reuse `get_session()`/`init_db()` machinery) or a separate store, (c) whether `receipt_ref` should FK to a Phase 5 dataset row when evaluating against labeled data vs free-form uploads. This plan flags it; it does not resolve it.

## 6. Test plan (matches spec.md's Phase 6 test gate)

Follows Phase 3's established pattern: `streamlit.testing.v1.AppTest` for UI smoke tests (see `tests/test_playground_ui.py`), pure-function unit tests for logic extracted out of `render()` (see `redteam_playground.handle_response`), no Playwright unless AppTest genuinely can't cover something.

| Test gate item | File | Approach |
|---|---|---|
| Component tests | `tests/test_review_screen.py` | Unit-test pure logic pulled out of `review_screen.render()` (e.g. an `evaluate_display(report) -> dict` helper, mirroring `handle_response`), and evidence-panel formatting helpers, without Streamlit. |
| Component tests | `tests/test_eval_dashboard.py` | Unit-test `dashboard_data.fetch_calls()` and any aggregation helpers against an in-memory SQLite `CallLog` fixture (same pattern as `test_db_persistence.py`). |
| End-to-end browser flow | `tests/test_review_ui.py` | `AppTest.from_file(APP_PATH)`, select "Review Receipt" via the sidebar radio, click "Use sample: Genuine receipt", monkeypatch `pipeline_client.run_on_receipt` to a fixed fake graph result, assert evidence panels render, click "Approve", assert a `ReviewDecision` row is written (query the in-memory test DB) and a success message appears. |
| Human review workflow test | same file, or `tests/test_human_review_workflow.py` | Explicit assertion that clicking approve/reject is required to persist a decision — i.e. loading the page and NOT clicking anything writes zero `ReviewDecision` rows (proves no auto-approve, directly testing D-004/CLAUDE.md §5). |
| Responsive/layout checks | manual + `tests/test_review_ui.py` container assertions | `AppTest` does not render real CSS/viewport, so "responsive" can only be checked structurally (containers exist, are ordered correctly) via AppTest, plus a manual check in a real browser at common breakpoints. Flag: AppTest cannot verify actual responsive CSS behavior — that gate item is only partially automatable. |
| Accessibility checks | manual, note in `testing.md` | `AppTest` cannot inspect ARIA/contrast. Streamlit's own DOM has known baseline accessibility (labels on widgets); "where supported" in spec.md's test gate wording already concedes this is not fully automatable. Recommend a manual pass with a screen reader or axe browser extension at execution time, documented in `testing.md`, not a new automated test file. |
| Dashboard metrics match stored logs (acceptance criterion) | `tests/test_eval_dashboard.py` | Seed known `CallLog` rows, assert dashboard aggregation functions return matching counts/sums — a direct numeric equality test, not a UI screenshot test. |

**AppTest limitations to flag explicitly:** `streamlit.testing.v1.AppTest` does not support simulating real file uploads (`st.file_uploader`) or true multi-page navigation the way a browser would render it — it runs the single script tree in-process. Two consequences for Phase 6 execution: (1) the file-upload path itself (as opposed to the sample-receipt fast path) may need a Playwright smoke test if upload-specific behavior must be verified end-to-end — flagged, not decided here; (2) the sidebar-radio nav approach chosen in §2 keeps everything on one `AppTest.from_file(APP_PATH)` script tree, avoiding any AppTest multi-page limitation entirely (this is an additional argument for radio-nav over a native `pages/` directory, which AppTest may not traverse the same way).

## 7. Open questions / decisions needing a decision.md entry (flagged only)

1. **OD-009 (dashboard refresh strategy)** — already open. §4 offers 3 options and a non-binding recommendation (manual refresh button); needs a dated decision.md entry at execution time.
2. **Review-decision storage schema** — new, not yet in decision.md. §5's `ReviewDecision` table (columns, owning module, same-DB-file-as-CallLog or separate) needs its own decision entry since it's a new DB contract (S7/S11 adjacent).
3. **How the UI invokes the LangGraph pipeline** — new. §3 proposes direct in-process import of `agents/graph.py`'s compiled graph (no HTTP hop), based on the original spec's sequence diagram and repo structure showing no service wrapper. Needs confirmation once Phase 4's actual `agents/graph.py` interface exists, and a decision.md entry if any alternative (e.g. a thin internal FastAPI endpoint) is chosen instead.
4. **Sample receipt filenames/loading contract** — depends on Phase 5's actual output under `data/synthetic_receipts/`; §3's fast-path buttons cannot be finalized until Phase 5 ships. Not blocking this plan, but blocking Phase 6 execution.
5. **OD-006 (missing extracted fields representation)** — already open in decision.md; Phase 6's extraction evidence panel (§3) needs it resolved to render "missing" consistently.
6. **OD-007 (confidence calculation)** — already open; Phase 6's verdict block (§3) displays `report["confidence"]` assuming Phase 4 computes and supplies it, but the calculation method itself is Phase 4's open decision, not Phase 6's.
