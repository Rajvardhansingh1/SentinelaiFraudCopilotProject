# React Frontend Rewrite Plan — SentinelAI + Fraud Copilot

**Status:** Planning only. No frontend code written. Companion to D-034 (decision.md), which authorized this rewrite and is not modified by this document.

**Scope:** Plan a new `web/` (Next.js) app that replaces `frontend/` (Streamlit) once it reaches parity. `frontend/` stays live and untouched until then (D-034 consequence). This document does not touch `spec.md`, `decision.md`, `state.md`, or `progress_log.md` — any decision flagged as "open" below needs its own `decision.md` entry before a coding session locks it in.

---

## 1. Scope recap — the 4 complaints and how this plan answers them

1. **"Playground gives no feedback on why a weak attack failed."** Current `redteam_playground.py` only shows `st.success("Not caught")` + raw output — dead end for a would-be attacker who wants to learn. Plan (§4.1): on any non-blocked submission, the UI runs a client-side comparison of the submitted text against `proxy/redteam/attack_library.py`'s named patterns (10 patterns, surfaced via `guardrails.injection.matched_patterns` in the response) and renders concrete, pattern-grounded coaching — never fabricated advice.
2. **"Evidence panels dump raw JSON."** Current `review_screen.py` does `st.write(display["extracted_fields"])` etc. — literal dict rendering. Plan (§4.2): every structured evidence object (extraction fields, forensics result, policy verdict, dashboard stats) gets a purpose-built card component — labeled key-value grid, tamper badge + score gauge, compliant badge + rule list. No raw object ever reaches JSX as text.
3. **"Verdict is buried 4th, evidence-first."** Current review screen order is Extraction → Forensics → Policy → System Assessment. Plan (§4.2): verdict/confidence/tamper card renders first, full width, above the fold; extraction/forensics/policy evidence render below in collapsible sections, collapsed by default except the one most relevant to the verdict.
4. **"Prod-level, intuitive, not a Python data-app."** Plan (§2-§3): Next.js App Router + TypeScript + Tailwind, dark "verification teal" theme carried over from `frontend/.streamlit/config.toml`, componentized layout, real charting library, no Streamlit-style top-to-bottom script reruns.

---

## 2. Stack choice and justification

| Decision | Choice | Why |
|---|---|---|
| Framework | **Next.js 14+, App Router** | Server Components aren't needed for data (proxy is the source of truth, not a DB Next.js owns) but App Router's file-based routing + layouts map directly to the 3-page structure (Playground / Review / Dashboard) with a shared shell (nav, quota badge, theme). Pages Router would work too but App Router is the current default and has no cost here since nothing needs Pages-only features. |
| Language | **TypeScript** | The proxy already has a strict, documented JSON contract (D-015). Typing `GenerateResponse`, `GuardrailsResult`, `ExtractedFields`, etc. once in `web/lib/types.ts` catches the exact class of bug D-031/D-032 were (mismatched response shapes) at compile time instead of in production.
| Styling | **Tailwind CSS** | Fastest path to a consistent dark theme without hand-rolled CSS files; palette drops straight into `tailwind.config.ts` as named tokens (`bg-base`, `bg-surface`, `text-primary`, `accent-teal`) matching the existing config.toml values exactly — visual identity carries over, zero redesign risk. |
| Component library | **shadcn/ui (selectively) — Badge, Card, Collapsible, Tabs, Button, Textarea, Select** | shadcn is copy-in (not an npm dependency black box), unstyled-by-default so it doesn't fight Tailwind theming, and directly covers the exact primitives this app needs (badges for verdict/tamper-likelihood, collapsible evidence sections). Rejected: a heavier suite like MUI or Chakra — they ship their own theming system that would fight the teal palette instead of adopting it, and this app doesn't need a component catalog beyond ~8 primitives. |
| Charts | **Recharts** | Already the project's own noted upgrade path (spec.md original §6 tech table: "React + Tailwind + Recharts"). Covers the dashboard's bar chart (traffic by operation), line chart (hallucination scores over time), and a simple gauge/arc (ELA score, ADR'd in §4.2) without a second charting dependency. |
| Package manager | npm (matches `package-lock.json` convention, no project reason to prefer pnpm/yarn) | Lowest-friction default. |

---

## 3. Project structure — new `web/` directory

```
web/
  package.json
  tsconfig.json
  next.config.ts
  tailwind.config.ts
  postcss.config.js
  .env.local.example          # NEXT_PUBLIC_PROXY_BASE_URL=http://localhost:8000
  app/
    layout.tsx                 # shell: sidebar nav, theme, session-id provider, quota badge
    globals.css                # Tailwind base + CSS var theme tokens (light/dark not needed — dark-only per current app)
    page.tsx                   # redirect/landing -> /playground (parity with Streamlit's default page)
    playground/
      page.tsx
    review/
      page.tsx
    dashboard/
      page.tsx
  components/
    layout/
      sidebar-nav.tsx
      quota-badge.tsx
      cold-start-banner.tsx    # parity with health_check.ping_proxy() UX
    playground/
      attack-picker.tsx        # prewritten dropdown + free-text textarea toggle
      submit-panel.tsx
      result-card.tsx          # blocked / allowed-but-weak / allowed-strong states
      weakness-coach.tsx       # complaint #1 — pattern-gap reasoning, see §4.1
    review/
      receipt-picker.tsx       # sample fast-path + upload
      verdict-card.tsx         # complaint #3 — renders FIRST
      evidence/
        extraction-card.tsx    # complaint #2
        forensics-card.tsx     # complaint #2 — tamper badge + ELA gauge + EXIF flag list
        policy-card.tsx        # complaint #2 — compliant badge + triggered-rules list
        report-card.tsx
      human-decision-panel.tsx # approve/reject, notes, POST to review-decision endpoint
    dashboard/
      metrics-row.tsx          # totals first (verdict-first principle applied to dashboard)
      traffic-chart.tsx        # Recharts bar
      hallucination-chart.tsx  # Recharts line
      guardrail-catches-card.tsx
      cost-latency-cards.tsx
    ui/                         # shadcn primitives (generated, not hand-written)
      badge.tsx card.tsx collapsible.tsx tabs.tsx button.tsx textarea.tsx select.tsx
  lib/
    types.ts                   # TS mirrors of D-015's request/response shapes + agents/graph.py state shape
    api.ts                     # fetch wrapper(s), see §5
    session.ts                 # visitor id + call count, see §6
    sample-attacks.ts           # D-019 cached-fallback data, see §7 (ports frontend/data/sample_attacks.py)
    sample-receipts.ts          # ports SAMPLE_RECEIPTS from review_screen.py
    weakness-heuristics.ts      # complaint #1 pattern-gap logic, see §4.1
    format.ts                   # currency/percent/ms formatters (small, no library)
  public/
    (icons only if needed; prefer inline SVG/lucide-react which ships with shadcn)
  tests/
    e2e/                        # Playwright specs, see §9
      playground.spec.ts
      review.spec.ts
      dashboard.spec.ts
    unit/                       # Vitest + RTL, see §9
      weakness-heuristics.test.ts
      format.test.ts
      sample-attacks.test.ts
```

`frontend/` (Streamlit) is untouched and keeps running side-by-side until parity is verified (§8).

---

## 4. Page-by-page design

### 4.1 Red-Team Playground page (`/playground`)

**Layout (top to bottom):**
1. Header: title + one-line caption (parity with current copy) + quota badge (`calls used / 8`) in the corner, always visible (not buried in a column metric).
2. Collapsible "What's the system prompt the attacker is up against?" — same content as current `st.expander`, using shadcn `Collapsible`, collapsed by default.
3. Attack picker: a `Select` populated from `sample-attacks.ts` labels, **plus** an explicit "Write your own" option that reveals a `Textarea` (500 char cap, live counter) — this already matches current UX, kept because it works; the fix is what happens *after* submit, not the picker itself.
4. Submit button → calls proxy per §5, shows a loading state (skeleton, not a spinner-only block) → renders `ResultCard`.

**`ResultCard` — three states, this is the concrete fix for complaint #1:**

- **Blocked (400, `injection_detected`):** red badge "Blocked", lists `guardrails.injection.matched_patterns` by human name (e.g. "role_override → matched 'act as' / 'you are now' phrasing"). This already works today; keep it, just restyle.
- **Allowed / not caught, i.e. the submission is the hard case:** green/amber badge "Not blocked" + the model's raw output text (safe to show verbatim — it's the LLM's own response, not evidence needing formatting) + a new **`WeaknessCoach`** section underneath, always shown when `guardrails.injection.flagged === false`.
- **Request failed (proxy unreachable / 429 quota):** existing D-019 cached-fallback path, see §7.

**`WeaknessCoach` mechanism — option (a) from the brief, grounded not fabricated:**

`lib/weakness-heuristics.ts` exports `explainWeakness(promptText: string, matchedPatterns: string[]): CoachTip[]`. Logic:
1. It does **not** invent a "why this failed" narrative from nothing. It runs the *same* regex family the proxy exposes — the 10 `ATTACK_PATTERNS` names from `proxy/redteam/attack_library.py` are re-declared as a small static TS lookup table (`lib/weakness-heuristics.ts`'s `PATTERN_HINTS`, ~10 entries, name → plain-English trigger phrase + "why it works" one-liner, authored once from reading the real regexes, not the LLM guessing).
2. Since the response already came back unflagged, `matched_patterns` is empty by definition — so the coach's job is to say **which of the 10 known pattern families the submitted text came closest to, and what's missing**, computed client-side by testing the submitted text against loosened variants of the same trigger phrases (e.g. text contains "ignore" or "pretend" as a bare word but not the full regex shape) using simple substring/keyword checks — not a second regex engine, just `String.includes` against a handful of trigger keywords already implied by the pattern names.
3. Output: 1-3 `CoachTip` cards, e.g.:
   > **Closest miss: `role_override`.** Attacks in this family use explicit role-override phrasing like "you are now..." or "act as...". Your prompt used softer phrasing the detector doesn't key on — try being more explicit about redefining the assistant's role.
4. If the submitted text doesn't resemble any known family at all (a genuinely novel/creative attempt that also didn't get blocked because it's not actually adversarial), the coach says exactly that — "this doesn't resemble any of our known attack families, and wasn't flagged" — rather than forcing a fake match. This is important: never claim a tip is proxy-verified when it's a client-side heuristic guess. Every `CoachTip` UI element carries a small "based on known attack pattern names, not a live proxy check" disclaimer, since the client is pattern-matching independently of the actual server-side detector run (the server already told us it *didn't* match anything — the coach is explaining the pattern taxonomy, not re-running server logic).

This keeps the education grounded in real proxy vocabulary (the same 10 pattern names the server actually uses) without fabricating an LLM-authored explanation or adding a second network call.

**ponytail note:** rejected building an actual second LLM call ("ask the LLM why this attack was weak") — that's a real option but adds cost/latency/a new proxy operation for a nice-to-have; the static heuristic table costs nothing and is grounded in the exact same pattern names the user already sees when something *is* blocked. Flag as an open question in §11 if a future session wants the richer LLM-authored version.

### 4.2 Review Receipt page (`/review`)

**Layout (top to bottom) — verdict first, this is the direct fix for complaints #2 and #3:**

1. `ReceiptPicker`: two sample buttons ("Sample: genuine", "Sample: tampered" — same fast path as today) + a drag/drop or click file upload, side by side. "Run analysis" button, disabled until a receipt is chosen.
2. On result: **`VerdictCard` renders first, full-width, above everything else.** Contents:
   - Large compliant/non-compliant badge (green/red, shadcn `Badge`).
   - Confidence percentage, labeled explicitly as "grounding-fidelity confidence" per D-026's ponytail ceiling note — not presented as a calibrated probability.
   - Hallucination % (small, secondary).
   - Tamper-likelihood badge (from forensics) at-a-glance, right next to compliance — this is the "at-a-glance" requirement from the brief; verdict card surfaces both the policy verdict and the forensics tamper read without the reviewer opening any evidence panel.
   - Prominent "This is model output, not a final decision" caption (parity with existing D-004 boundary), directly above the approve/reject controls which live in this same card or immediately below it — human decision stays visually adjacent to the verdict it's judging.
3. Below the verdict card, a `Tabs` or stacked `Collapsible` group — **"Evidence" section, collapsed by default** except a caption inviting expansion — containing:
   - **`ExtractionCard`**: labeled key-value grid (Vendor / Date / Total / Line items as a small table), built from `extracted_fields` — no raw object ever printed.
   - **`ForensicsCard`**: tamper-likelihood badge (repeated here for context) + an ELA-score gauge (Recharts `RadialBarChart` or a simple CSS arc — small enough not to need a whole gauge library) + a bulleted EXIF-flags list (or "No EXIF inconsistencies found" empty state).
   - **`PolicyCard`**: compliant/non-compliant badge (repeated) + triggered-rules list rendered as named rule chips, or "No policy rules triggered" empty state.
   - **`ReportCard`**: the free-text audit report (already human-readable prose from `report_writer.py` — render as-is, this one was never the JSON-dump problem).
4. `HumanDecisionPanel`: reviewer notes textarea + Approve/Reject buttons, POSTs to the new decision-recording endpoint (§10), success toast confirms "Recorded: approved/rejected".

This directly answers complaint #3 (verdict first) and complaint #2 (every structured field gets a purpose-built card, never `<pre>{JSON.stringify(...)}</pre>`).

### 4.3 Eval Dashboard page (`/dashboard`)

**Layout — verdict-first principle applied to metrics:**

1. `MetricsRow`: 4 large stat tiles across the top — Total calls, Guardrail catches, Total cost, Avg latency (same 4 as current `st.metric` row) — biggest, most-glanceable numbers first, exactly like the review page puts the verdict first.
2. Below: two-column chart row — `TrafficChart` (Recharts bar, calls by operation) and `GuardrailCatchesCard` (small badge list: injection catches / PII catches, not a raw dict).
3. `HallucinationChart` (Recharts line) if scores exist; empty state otherwise.
4. `CostLatencyCards`: two small cards (avg/total cost, avg/p95 latency) — formatted currency/ms, not a raw `{"total_usd": ..., "avg_usd": ...}` dump (fixes the same raw-`st.write(cost)` / `st.write(latency)` pattern complaint #2 covers).
5. Manual "Refresh" button (D-028 parity — no polling loop, same rationale holds for React: this is a reviewer tool, not a live ops screen).

---

## 5. API layer — how Next.js calls the FastAPI proxy

**Recommendation: direct client-side `fetch()` calls from client components against `NEXT_PUBLIC_PROXY_BASE_URL`.** No Next.js API routes as a proxy layer.

**Justification against the CORS setup already in place:** `proxy/main.py` already has CORS middleware keyed off `settings.allowed_origins_list` / `ALLOWED_ORIGINS` specifically so a separately-hosted frontend can call it cross-origin (D-034's own stated consequence). Adding a Next.js API-route hop would:
- Duplicate the CORS work with nothing gained (the browser never touches the proxy directly in that design, so CORS becomes moot — but then the "hide the proxy URL" benefit is also moot for this app, since `NEXT_PUBLIC_PROXY_BASE_URL` is not a secret: no API key lives in the browser call, the proxy itself is the trust boundary and already rate-limits per session-id).
- Add latency and a second failure surface for zero security benefit — there's no secret to hide (the playground/review pages are public demo surfaces by design, per spec.md's red-team-playground goal: "public-facing").
- Complicate the cached-fallback-on-429 pattern (§7), which needs to run entirely client-side to swap in a local sample without a network round-trip through Next.js.

`lib/api.ts` is a thin wrapper: `postGenerate(body): Promise<{status, body}>`, `getQuota()`, mirroring `frontend/lib/proxy_client.py::call_generate`'s never-throw contract (D-031 lesson: wrap the whole call including JSON parsing in try/catch, return a synthetic `503`/`proxy_unreachable` envelope on network failure — same pattern, ported to TS).

**Open question flagged for §11:** if the new `/v1/analyze-receipt` endpoint (§10) ever needs a server-side-only credential Next.js should hold, that specific call could move to a Next.js API route later — not needed at plan time since no such credential exists today.

---

## 6. State/session management

Direct port of `frontend/lib/session.py`'s two functions, same scope (per-browser-tab-session, not auth):

- `lib/session.ts` exports a `SessionProvider` React Context (tiny, no external state library — Redux/Zustand would be over-engineering for 2 values) holding `{ sessionId: string, callCount: number, incrementCallCount: () => void }`.
- `sessionId`: generated once via `crypto.randomUUID()`, persisted to `localStorage` (not just React state) so a page refresh doesn't silently start a new rate-limit session against the proxy — this is actually a *fix* over the Streamlit version, where `st.session_state` already survives reruns within a browser tab session; `localStorage` gives the same durability.
- `callCount`: also mirrored to `localStorage` for the same reason; source of truth for the quota badge is still what the proxy reports when available (`GET /quota`, already built per Phase 7 status) — client-tracked count is a fallback/display aid, not the enforcement mechanism (the proxy enforces the real limit either way).
- Mounted once in `app/layout.tsx`, consumed via a `useSession()` hook.

---

## 7. D-019 cached-fallback-on-429 pattern in React

Direct port, same logic, same reasoning as `frontend/data/sample_attacks.py::find_cached()`:

- `lib/sample-attacks.ts` exports a `SAMPLE_ATTACKS` array (same 4 entries: id, label, prompt, `cachedResponse` — TS object literal, typed against `lib/types.ts`'s `GenerateResponse`) and a `GENERIC_FALLBACK_RESPONSE` (429/`rate_limit_exceeded`), ported 1:1 from the Python source — same 4 attacks, same matched-pattern lists, verified against the same real `ATTACK_PATTERNS` the Python version was checked against (no need to re-verify against the proxy; the values are copied, not regenerated).
- `findCached(promptId: string | null): GenerateResponse` — same lookup-or-fallback logic as `find_cached()`.
- Call site (`submit-panel.tsx`): on a `503`/`proxy_unreachable` or `429` response from `postGenerate()`, call `findCached(selectedAttackId)`, show the same quota/unreachable banner copy, and render the cached response through the identical `ResultCard` component a live response would use — no separate "cached" UI branch, so `WeaknessCoach` still runs correctly on cached "not blocked" cases if any existed (today all 4 cached responses are blocked, so this is defensive consistency, not a new behavior).
- `sample-receipts.ts` ports `SAMPLE_RECEIPTS` similarly for the Review page's fast path (2 entries: genuine/tampered sample paths) — but note these become **served static image assets** under `web/public/samples/` (copied from `data/synthetic_receipts/`) rather than filesystem paths, since Next.js can't read `data/synthetic_receipts/*.jpg` off the Python-side filesystem at runtime — see §10 for how the receipt bytes actually reach the new analyze endpoint.

---

## 8. Migration/parity plan

**Build order** (each stage runnable/demoable before the next starts):

1. Scaffold `web/` (Next.js + Tailwind + shadcn init), shell layout with nav + theme tokens, no real data yet.
2. `/playground` page end-to-end against the *existing* `/v1/generate` — this is the lowest-risk page (no new backend work needed) and directly demonstrates complaint #1's fix first.
3. New backend endpoint `POST /v1/analyze-receipt` (§10) — backend work, blocks the Review page.
4. `/review` page end-to-end against the new endpoint.
5. `/dashboard` page — needs a way to read `CallLog` rows; see §10 for whether that's a new endpoint or direct DB access is acceptable (it currently isn't, since Next.js is a separate Node process with no Python DB access — flagged in §10 as the second backend gap).
6. Parity checklist pass (below) against the live Streamlit app, side by side.
7. Cutover: `frontend/` retired only after checklist passes and the user confirms.

**Parity checklist**, derived from what the 3 retiring test files actually verify (so nothing regresses silently):

From `tests/test_playground_ui.py` (`test_playground_renders_and_blocks_attack`):
- [ ] App renders without a client-side crash on load.
- [ ] Selecting a prewritten attack from the picker and submitting shows a "Blocked" result when the proxy returns `injection_detected` with `matched_patterns`.

From `tests/test_playground_quota.py`:
- [ ] Proxy's real 429-after-N-calls behavior is reachable and detected client-side (`settings.rate_limit_per_session`, currently 8 — backend behavior, not new).
- [ ] `findCached()` (TS port of `handle_response`/`find_cached`) returns the matching attack's `cachedResponse` when a known `promptId` hits 429.
- [ ] `findCached()` returns `GENERIC_FALLBACK_RESPONSE` (`rate_limit_exceeded`) for free-text (`promptId === null`) on 429.

From `tests/test_review_ui.py`:
- [ ] After running the sample-receipt fast path ("genuine" sample button → "Run analysis"), all evidence sections render: extraction, forensics, policy, verdict/confidence, human-review panel — content-equivalent to the old subheader set, now as named cards instead of subheaders.
- [ ] No `ReviewDecision` row is written merely from viewing the evidence — only an explicit Approve/Reject click writes one (`test_no_decision_recorded_without_clicking_approve_or_reject`'s invariant carries over unchanged).
- [ ] Clicking Approve records `human_decision: "approved"`; clicking Reject records `"rejected"` (via the new endpoint from §10, hitting the same `ReviewDecision` table D-027 defined).

New parity items from the 4 user complaints (not covered by old tests since the old UI didn't do these):
- [ ] Playground: submitting a not-blocked prompt shows a non-empty `WeaknessCoach` section referencing at least one real pattern name.
- [ ] Review: verdict card is the first rendered element after running analysis, evidence sections are visually below it.
- [ ] No page renders a raw JSON object as visible text anywhere (`extracted_fields`, `forensics_result`, `policy_verdict`, dashboard `cost`/`latency`/`catches` dicts) — manual visual check per page, since this is a "does it look right" criterion Playwright can assert on structurally (no literal `{` `"key":` substring in rendered evidence card text) but ultimately needs a human/visual pass.

---

## 9. Testing approach

- **Vitest + React Testing Library** for component/unit-level logic that doesn't need a real browser: `lib/weakness-heuristics.ts` (pure function, easiest to get wrong and most valuable to unit test — mirrors how `handle_response()` in the Python version was made "pure logic, unit-testable without Streamlit"), `lib/sample-attacks.ts`'s `findCached()`, `lib/format.ts`'s formatters, and card components' rendering given a fixed props object (e.g. `ForensicsCard` renders the right badge color for `tamper_likelihood: "high"` vs `"low"`).
- **Playwright** (already used in this project via the `playwright-cli` skill) for the true end-to-end flows: full playground submit→result round trip against a running dev proxy, full review sample→analyze→approve round trip, dashboard refresh. These directly replace the retiring `streamlit.testing.v1.AppTest` specs — Playwright is a strict upgrade here since it drives a real browser (the old `AppTest` suite's own documented limitation was "no real file-upload simulation, no CSS/a11y checks" per spec.md's Phase 6 status; Playwright removes both limitations).
- No new test infra beyond these two — no Cypress, no separate a11y tool (Playwright can assert basic a11y via its own accessibility tree snapshot if needed later; not scoped now, YAGNI).

---

## 10. Backend changes needed beyond what's already done

**`/v1/generate` (D-015) covers the Playground page fully** — no changes needed there.

**The Review page is the real gap.** Today, `frontend/lib/pipeline_client.py::run_on_receipt()` calls `agents.graph.build_graph()` as an **in-process Python import** — this only works because Streamlit is itself a Python process. A Next.js/Node.js frontend cannot import `agents/graph.py`. This is the single biggest backend-side consequence of the rewrite, exactly as flagged in the task brief, and it must be resolved before the Review page can be built (§8 build order already sequences this as its own step).

**Proposed new endpoint:**

```
POST /v1/analyze-receipt
```

Request: `multipart/form-data` — `session_id: str`, `image: file` (png/jpg/jpeg). Multipart (not base64-in-JSON) because the payload is an actual image file and this matches how the existing Streamlit `st.file_uploader` handles bytes today (`review_screen.py`'s upload branch already writes raw bytes to a temp path — the new endpoint does the same server-side, same path-traversal precaution: server generates its own temp filename, never trusts a client-supplied name).

Response (200): the same shape `agents/graph.py`'s `invoke()` already returns today, passed through as JSON — `extracted_fields`, `forensics_result`, `policy_verdict`, `report_text`, `report_guardrails`, `errors`. This is a direct wrap of `frontend/lib/pipeline_client.py::run_on_receipt()`'s existing never-raise contract (§ D-031's lesson: any node failure surfaces as an `errors` entry, never an uncaught exception) — the wrapping is thin, no new pipeline logic.

**Where it lives:** `proxy/main.py` gains this route (it's the one FastAPI process already running; no new service). This does **not** violate D-001 (SentinelAI domain-agnostic) if scoped carefully — the endpoint should be a thin adapter that imports and calls `agents.graph.build_graph()`, structurally living either (a) directly in `proxy/main.py` guarded as fraud-copilot-specific, or (b) more cleanly, in a new `agents/api.py` FastAPI `APIRouter` mounted onto the same app instance, keeping `proxy/` itself domain-agnostic and putting the domain-specific route in the `agents/` package where `pipeline_client.py`'s logic already conceptually lives. **Recommend (b)** — matches the existing module boundary (SentinelAI = `proxy/`, Fraud Copilot = `agents/`) cleanly; this should get its own `decision.md` entry when a coding session picks it up, since it's a structural choice, not just an endpoint addition.

**Second, smaller gap — the Dashboard page.** `frontend/lib/dashboard_data.py::fetch_calls()` queries `proxy/db/models.py`'s `CallLog` table via direct SQLAlchemy access — again, only possible because Streamlit is a Python process sharing the same DB file. Next.js needs this over HTTP too. Proposed: `GET /v1/calls` (or reuse the existing `GET /quota` pattern's spirit) returning a paginated/limited list of recent `CallLog` rows as JSON, with the same fields `dashboard_data.py`'s helper functions (`traffic_by_operation`, `guardrail_catch_counts`, `hallucination_scores`, `cost_summary`, `latency_summary`) already compute from — those five aggregation functions port near-verbatim to `lib/dashboard-data.ts`, operating client-side on the fetched array exactly as they do today in Python, so the endpoint just needs to return raw rows, not pre-aggregated stats (keeps the endpoint dumb, matches D-001's domain-agnostic bias — though arguably `CallLog` read access is proxy-native data, so this one *can* live directly in `proxy/main.py` without the same boundary question the analyze-receipt endpoint raises).

**The `ReviewDecision` write (Approve/Reject) also needs an endpoint** — today `record_review_decision()` in `review_screen.py` writes directly to the frontend-owned SQLite table (D-027) via in-process SQLAlchemy. Proposed: `POST /v1/review-decisions` (lives alongside the analyze-receipt route, same domain-boundary reasoning — recommend `agents/api.py` again, since `ReviewDecision` is fraud-copilot application data per D-027's own rationale, not proxy telemetry) accepting the same fields D-027's schema already defines (`session_id, receipt_ref, system_verdict, confidence, hallucination_pct, human_decision, reviewer_notes`).

**Summary of net-new backend surface:**
- `POST /v1/analyze-receipt` (wraps `agents/graph.py`)
- `POST /v1/review-decisions` (wraps `frontend/db/models.py::ReviewDecision` writes — note: this table currently lives under `frontend/db/`, which should probably move to `agents/db/` or similar once `frontend/` retires, since "frontend-owned" stops meaning anything when the frontend is a separate Node process — flag for §11)
- `GET /v1/calls` (wraps `proxy/db/models.py::CallLog` reads)

All three are additive; `/v1/generate` (D-015) is unchanged.

---

## 11. Open questions / flagged for a decision.md entry (not resolved here)

1. **Hosting target for the Next.js app.** Vercel is the natural fit for Next.js (zero-config, built-in image optimization, edge network) but was not part of the original Phase 7 deployment plan (`deploy/render.yaml` for the proxy, HF Spaces for the old Streamlit frontend, per D-030). This changes `PHASE7_PLAN.md`'s deployment topology — needs an explicit decision (Vercel vs. redeploying the React build to HF Spaces/Render as a static export) before Phase 7 is revisited. Flagged, not resolved.
2. **Where `POST /v1/analyze-receipt` and `POST /v1/review-decisions` physically live** — `proxy/main.py` directly vs. a new `agents/api.py` router mounted onto the same app (this plan recommends the latter in §10, but it's a structural call a coding session should confirm/decide formally, since it touches the SentinelAI/Fraud-Copilot module boundary CLAUDE.md §5 calls out as an architecture invariant).
3. **`ReviewDecision`'s table ownership** once `frontend/` (the Python Streamlit app) retires — D-027's rationale for a "frontend-owned table" was specifically about keeping it out of `proxy/db/` (SentinelAI); it should probably move under `agents/db/` for the new architecture, but this is a rename/relocation decision, not urgent for initial React build-out (the physical SQLite file and schema don't need to change, just which package's models.py declares it).
4. **CORS origin list in production** — `ALLOWED_ORIGINS` needs the real Vercel/deployed Next.js URL added once hosting (item 1) is decided; not a design question, just a deployment-time config item to not forget.
5. **Whether `WeaknessCoach`'s heuristic (§4.1) should eventually become a real LLM-authored explanation** via a new proxy operation — explicitly deferred in this plan (ponytail: static table is free and grounded; an LLM call adds cost/latency for a nice-to-have). Revisit only if user feedback says the static coaching feels thin.

---

## Summary

New `web/` Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui (primitives only) + Recharts app, calling the FastAPI proxy directly via `fetch()` (no API-route hop, CORS already wired per D-034). Three pages — Playground, Review, Dashboard — each redesigned to put the verdict/result first and render structured evidence as real cards instead of JSON dumps, with a new grounded (not fabricated) weakness-coaching mechanism on the Playground page answering complaint #1. Biggest backend gap: `agents/graph.py` is currently only reachable in-process from Python; needs three new thin HTTP endpoints (`POST /v1/analyze-receipt`, `POST /v1/review-decisions`, `GET /v1/calls`) since Node.js can't import Python. `frontend/` stays live until the parity checklist (§8, derived from the 3 retiring Streamlit test files plus the 4 new complaint-driven behaviors) passes.
