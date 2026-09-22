# SentinelAI Security Dashboard (D-045, phase_dev_upgrade.md Phase 6)

## Where the numbers come from

Everything on the dashboard is read from persisted rows — nothing is
computed from demo data or hardcoded:

| Metric | Source |
|---|---|
| Total tests / passed / failed / errors / not run / inconclusive | `test_run_results` rows belonging to the **most recent** `run_id` |
| Open findings | `findings` rows with status OPEN / ACKNOWLEDGED / RETEST_REQUIRED |
| Severity distribution | severity of those open findings (current risk exposure, not all-time) |
| Recent security activity / test history | last 20 `test_run_results` rows by `executed_at` |
| Affected models / providers | distinct `(provider, model)` across `test_run_results` |

If nothing has run yet, every count is 0 and `last_run_at` is `null` — the UI
shows an explicit empty state, it does not invent placeholder numbers.

## What records a run

`POST /v1/findings/sync` is the only thing that persists test history. It:

1. runs the full engine suite,
2. opens `Finding` rows for new FAILs (Phase 5 behavior, unchanged),
3. logs **every** result — any status — to `test_run_results` under one
   shared `run_id` (Phase 6 addition).

`POST /v1/security-tests/run` remains stateless: it's the "check right now"
path behind the Live test run table, and deliberately records nothing.

`run_id` grouping exists so "total tests" means the latest run's count rather
than a cumulative sum that would inflate on every sync. It's also the
grouping Phase 7's baseline/regression comparison will need.

## Endpoint

`GET /v1/security-dashboard` returns the aggregate summary above.

**Aggregate-only by design.** The payload carries no `raw_input`,
`raw_output`, or evidence blobs — per Phase 6's "do not expose secrets or
sensitive test payloads unnecessarily". Raw attack payloads and model
responses stay behind the Findings detail page, where they're the point.
`tests/test_dashboard_phase6.py` has a regression test asserting payload text
never leaks into this response.

## UI

`web/components/security/dashboard-summary.tsx`, mounted at the top of
`/security` (above the existing Live test run table, which is unchanged).
Three distinct states, as Phase 6 requires:

- **loading** — while the fetch is in flight,
- **error** — SentinelAI unreachable or non-2xx; shows the actual reason,
- **empty** — reachable, but nothing recorded yet; tells the user how to
  populate it.

`getSecurityDashboard()` in `web/lib/api.ts` returns a discriminated
`{status: "ok" | "error"}` result rather than the usual never-throw
empty-value fallback, precisely so empty and error can't be confused.
