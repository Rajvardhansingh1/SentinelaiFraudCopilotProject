# SentinelAI Security Test CI/CD (D-047, phase_dev_upgrade.md Phase 8)

## What this is (and isn't)

`.github/workflows/ci.yml` runs the Python/web unit test suites (pytest,
vitest) — code correctness. **This is different**: `scripts/sentinel_ci.py`
runs SentinelAI's own *security* tests (proxy/engine, Phases 3-4) against a
*running* SentinelAI instance and decides pass/fail by a policy you
configure — same purpose as a linter or a coverage gate, but for guardrail
regressions instead of code style.

## No secrets required

The CLI talks to a running SentinelAI instance over plain HTTP
(`--target http://...`). It never imports a provider SDK and never needs a
Groq/Gemini API key itself — the *target instance* holds its own credentials
server-side (D-041), the way it always does. Nothing about running this in
CI requires putting a secret in the repo or in workflow config.

## Selecting a target and a test suite

```bash
python -m scripts.sentinel_ci --target http://localhost:8000
python -m scripts.sentinel_ci --target https://staging.example.com \
    --category prompt_injection,jailbreak
```

`--target` is any reachable SentinelAI instance (local, staging, or a real
deployment). `--category` (comma-separated, matches `proxy/engine/plugins/*`
category names) selects a suite; omitted means every registered test.

## The failure policy is never hardcoded

Every threshold is a CLI flag with a visible, overridable default
(`proxy/ci.py::CIPolicy`) — the engine itself never decides what counts as a
failure:

| Flag | Default | Meaning |
|---|---|---|
| `--fail-on-status` | `FAIL` | Comma-separated statuses that count toward failure |
| `--fail-on-severity` | *(any)* | Restrict further to these severities |
| `--max-failures` | `0` | Job fails only if more matching results than this |
| `--check-regression` | off | Also fetch the latest regression report (Phase 7) |
| `--max-regressions` | `0` | Job fails only if more regressions than this (needs `--check-regression`) |

A job that runs with no flags beyond `--target` fails on any `FAIL` result of
any severity — the strictest reasonable default, and still just a default:
change it in your own workflow, nothing in the CLI enforces it.

## Machine-readable and human-readable output

```bash
python -m scripts.sentinel_ci --target http://localhost:8000 \
    --json-out security-results.json \
    --md-out security-summary.md
```

`--json-out` writes every `TestResult` plus the computed verdict — for
downstream tooling. `--md-out` writes the same Markdown block the CLI prints
to stdout — suitable for `$GITHUB_STEP_SUMMARY` or a PR comment.

## Regression detection in CI

`--check-regression` fetches `GET /v1/regression-report` (Phase 7) and folds
its `regressions` count into the policy. If no baseline exists yet, the
check is skipped with a clear message on stderr — it never silently passes
or crashes the job over a missing baseline.

## GitHub Actions integration

See `.github/workflows/security-tests.yml`: boots `proxy.main:app` with
`uvicorn`, waits for `/health`, runs `scripts.sentinel_ci` against it,
publishes the Markdown summary to the job summary, and uploads the JSON as a
build artifact. The workflow's own `--fail-on-severity critical,high` is a
sample policy — edit it for your repo, it isn't special-cased in the CLI.

## Exit codes

`0` = policy satisfied (job passes). `1` = policy violated (job fails). Any
other non-zero exit is an actual error reaching the target (connection
refused, HTTP error), distinguishable in the log from a real policy failure.
