# SentinelAI Findings Subsystem (D-044, phase_dev_upgrade.md Phase 5)

## What generates a Finding

A `Finding` is opened only from a `TestStatus.FAIL` result from `proxy/engine`
(Phase 3/4) — a FAIL means a guardrail that should have caught an attack
didn't. `ERROR` (the test itself broke) and `INCONCLUSIVE` (no classifier
exists to judge it, e.g. `unsafe_output_behavior`) are test-health signals,
not vulnerabilities, and never become findings.

## Fields

`id`, `test_id`, `category`, `severity`, `title`, `description`,
`affected_target`, `evidence` (the full `RawExecution` the test produced),
`reproduction`, `provider`, `model`, `status`, `created_at`, `updated_at`.

## States

`OPEN` → `ACKNOWLEDGED` / `RETEST_REQUIRED` → `RESOLVED`. Transitions aren't
restricted to a strict state machine — a human can move a finding to any of
the 4 states via `PATCH /v1/findings/{id}` (no automatic transitions yet;
Phase 7's baseline/regression comparison is where "this now passes, mark
resolved" logic belongs, not here).

**Rows are never deleted.** Resolving a finding only changes `status` and
`updated_at` — `evidence`/`reproduction` stay exactly as captured.

## Deduplication

`POST /v1/findings/sync` runs the full engine suite and opens a new Finding
for each FAIL — but only if no Finding for that `test_id` is already
OPEN/ACKNOWLEDGED/RETEST_REQUIRED. Running sync repeatedly doesn't spam
duplicates. If a finding was RESOLVED and the same test fails again later, a
**new** Finding row is opened — the resolved one is left untouched (its own
history, not overwritten).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /v1/findings/sync` | Run the suite, open new findings for new FAILs, return `{results, findings_created}` |
| `GET /v1/findings?status=` | List, optional status filter |
| `GET /v1/findings/{id}` | One finding, full detail |
| `PATCH /v1/findings/{id}` | Status-only update |

`POST /v1/security-tests/run` (Phase 4) is untouched — it still runs the
suite without persisting anything, for the read-only `/security` page.

## UI

`web/app/findings/page.tsx` — list with a status filter and a sync button.
`web/app/findings/[id]/page.tsx` — detail page with the
Finding → Test → Attack → Model response → Evidence → Reproduce drill-down as
tabs, plus status-change buttons. All 4 finding statuses get distinct badge
colors (`components/findings/finding-status-badge.tsx`), same principle as
Phase 4's `TestStatus` badges — never collapsed to a boolean.
