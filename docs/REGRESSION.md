# SentinelAI Security Regression Testing (D-046, phase_dev_upgrade.md Phase 7)

## Concept

A **baseline** pins one `TestRunResult.run_id` — a snapshot of every test's
status at a point in time. A later run is compared against it.

## Building blocks

- `Baseline` (`proxy/db/models.py`) — `name`, `run_id`, `created_at`. Stores
  only the pointer; the actual per-test rows stay in `test_run_results`, so
  nothing is duplicated or can drift.
- `proxy/regression.py::compare_runs(baseline, current)` — pure function, no
  DB, no time — takes two lists of `{test_id, category, severity, status,
  provider, model}` snapshots and returns the diff. Easy to unit test
  directly (`tests/test_regression_phase7.py` does, without touching a DB).
- `proxy/regression.py::findings_delta(db, since)` — findings opened or
  resolved since the baseline's `created_at`.
- `create_baseline(db, name, run_id=None)` — defaults to the most recent
  recorded run; returns `None` (never an empty/fake baseline) if there's
  nothing to pin yet.

## What the comparison detects

| Bucket | Meaning |
|---|---|
| `regressions` | PASS → FAIL: a guardrail that worked before doesn't now |
| `new_failures` | A test that didn't exist in the baseline, and fails now |
| `fixed` | FAIL → PASS: a previously-failing guardrail now works |
| `unchanged` | Same status in both runs |
| `other_changes` | Any other status transition (e.g. PASS → INCONCLUSIVE) — kept, never dropped |
| `severity_changes` | Same test, different assigned severity |
| `added_tests` / `removed_tests` | Test IDs present in one run but not the other |
| `provider_config_changed` | The set of `(provider, model)` pairs differs between runs |
| `per_test` | Every test's baseline vs. current status/severity — nothing is collapsed away |
| `findings.new_findings` / `findings.resolved_findings` | From the Findings subsystem (D-044), not re-derived from the run diff |

**No single "security score" is computed anywhere** — phase_dev_upgrade.md
explicitly warns against making a score the sole source of truth. The report
is counts plus full detail; `per_test` is what "the underlying individual
test results must remain accessible" means in practice.

## Endpoints

| Endpoint | Behavior |
|---|---|
| `POST /v1/baselines` | `{name, run_id?}` → pins a baseline. 409 `no_run_to_baseline` if nothing has run yet. |
| `GET /v1/baselines` | List, newest first. |
| `GET /v1/regression-report?baseline_id=&run_id=` | Defaults to the newest baseline vs. the newest recorded run. 404 `baseline_not_found` / 409 `no_run_to_compare` are real states, not generic errors. |

## UI

`web/app/regression/page.tsx` — create a baseline from the latest run, view
the diff as summary cards + regressions/fixed lists + findings delta + a full
per-test baseline→current table. `getRegressionReport()`/`createBaseline()`
in `web/lib/api.ts` return discriminated `{status: "ok"|"error"}` results
(same pattern as D-045's dashboard) so "no baseline yet" and "no run to
compare" render as their own explained states, not a blank screen or a
generic error banner.
