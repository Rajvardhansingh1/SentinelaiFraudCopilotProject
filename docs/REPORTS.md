# SentinelAI Security Reports (D-052, phase_dev_upgrade.md Phase 12)

## Built only from stored data

`proxy/reports.py` reads `test_run_results`, `findings`, `baselines`, and
`security_events` — the same tables every earlier phase writes to. Generating
a report never runs a test. An empty period produces an explicitly empty
report (`latest_run: null`, `test_cases: []`, a `limitations`/`notes` entry
saying so) — never a fabricated number.

## Executive report

Scope, testing period, key findings (top 10 open, by severity), severity
distribution (open findings only — current risk, not all-time), major
changes (regressions/fixes vs. the newest baseline, provider/model config
drift, findings opened/resolved in period), remediation status (finding
counts by status), security events in period, and an honest
**limitations** section — always present, flags INCONCLUSIVE/ERROR results
by name, and states outright that passing tests prove specific attacks were
caught, not that the system is secure (phase_dev_upgrade.md's own warning,
carried into the report itself).

## Technical report

Every test case in the latest run: id, category, severity, description,
**attack input**, expected behavior, result, provider/model, timestamp,
reproduction (`run_id` + the exact endpoint call to reproduce it). If a
run's `test_id` is no longer in the registry (a plugin was removed/renamed),
the case still appears with `attack_input: null` and
`definition_available: false` — never a crash, never a silent drop. Every
finding in the period with full evidence and reproduction.

## Remediation guidance (closes a Phase 5 gap)

Findings never had a `remediation` field until now. `proxy/remediation.py`
maps each engine category to actionable guidance; both `Finding` API
responses and every report row carry it.

## Secrets never appear

Every string in a report passes through `scrub()`:
- the server's configured `GROQ_API_KEY`/`GEMINI_API_KEY` are replaced by
  literal match (a credential embedded in captured evidence, e.g. from a
  provider error message, can't survive into a report);
- `proxy/middleware/pii_scanner.py::redact_pii` runs on every string (same
  scanner used elsewhere in SentinelAI);
- `run_id` fields are exempted from PII redaction (a digit-heavy uuid can
  false-match the phone regex) — everything else is scrubbed.

Tested with a synthetic finding whose evidence and detail literally contain
the configured key: absent from both the JSON and Markdown output.

## Endpoints

`GET /v1/reports/executive` / `GET /v1/reports/technical` —
`?since=&until=` (ISO timestamps) narrow the period; `?format=md` returns
the same content as Markdown (`text/plain`) instead of JSON.

## UI

`web/app/reports/page.tsx` — generate/regenerate each report, view the
rendered Markdown, download as `.md`.
