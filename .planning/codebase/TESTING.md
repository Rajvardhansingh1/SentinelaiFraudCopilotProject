# Testing Patterns

**Analysis Date:** 2026-09-21

## Test Framework

**Python (backend: proxy, agents, frontend/Streamlit, eval, data):**
- Runner: `pytest` (version 9.1.1 per `.pytest_cache` bytecode tags), plus `fastapi.testclient.TestClient` for API-level tests.
- Config: `pytest.ini` — minimal, only `testpaths = tests`. No markers, no coverage config, no `addopts` defined at the ini level.
- 30 top-level test modules in `tests/`, plus 8 more in `tests/agents/` (38 total `.py` test files, ~1,208 lines in `tests/*.py` alone, not counting `tests/agents/`).

**Web (`web/`):**
- Unit runner: `vitest` v2 (`web/vitest.config.ts`), `environment: "jsdom"`, path alias `@` → repo root of `web/`, explicitly excludes `tests/e2e/**` from the unit run.
- Component testing lib: `@testing-library/react` v16 is installed as a devDependency (available for component tests, though current `web/tests/unit/*` are plain logic tests, not component-render tests).
- E2E runner: `@playwright/test` v1.45 (`web/playwright.config.ts`) — `testDir: "./tests/e2e"`, 30s test timeout, `baseURL: http://localhost:3000`, auto-starts `npm run dev` as a web server (reuses an already-running dev server if present, 60s startup timeout).

**Run Commands:**
```bash
# Python — from repo root, with FraudCopilotProject conda env active
pytest                        # runs everything under tests/

# Web — from web/
npm run test                  # vitest run (unit tests, jsdom)
npm run test:e2e              # playwright test (browser e2e against localhost:3000)
npm run lint                  # next lint
```

There is no `pytest -k`/marker convention documented, and no coverage tooling (`pytest-cov`, `coverage.py`) configured in `pytest.ini` or `requirements.txt`-driven CI.

## Test File Organization

**Python:**
- Flat `tests/` directory for proxy/eval/frontend/dataset tests, one file per unit-under-test: `tests/test_proxy.py`, `tests/test_injection_detector.py`, `tests/test_pii_scanner.py`, `tests/test_rate_limiter.py`, `tests/test_schema_validator.py`, `tests/test_provider.py`, `tests/test_grounding.py`, `tests/test_hallucination_scorer.py`, `tests/test_eval_metrics.py`, `tests/test_eval_suite_smoke.py`, `tests/test_eval_dashboard.py`, `tests/test_dataset_integrity.py`, `tests/test_db_persistence.py`, `tests/test_deployment_smoke.py`, `tests/test_failure_modes.py`, `tests/test_foundation.py`, `tests/test_sample_attacks.py`, `tests/test_security_hardening.py`.
- Frontend/Streamlit + playground tests also live in the flat `tests/` dir (not under `frontend/`): `tests/test_frontend_proxy_client.py`, `tests/test_pipeline_client.py`, `tests/test_playground_proxy_integration.py`, `tests/test_playground_quota.py`, `tests/test_playground_ui.py`, `tests/test_review_screen.py`, `tests/test_review_ui.py`.
- `tests/agents/` sub-package mirrors `agents/` module-for-module: `test_api.py`, `test_extractor.py`, `test_forensics.py`, `test_graph.py`, `test_policy_checker.py`, `test_proxy_client.py`, `test_report_writer.py`, plus the architecture-enforcement test `test_no_direct_provider_calls.py`.
- `tests/fixtures/` holds shared fixture data for tests (OCR fixtures, sample receipts, etc.).
- Naming: `test_<module_or_behavior>.py`, functions `def test_<behavior>(...)`, no test classes observed (function-style pytest, not `unittest.TestCase`).

**Web:**
- `web/tests/unit/*.test.ts` — plain vitest unit tests for pure logic (`dashboard-data.test.ts` — 83 lines, `weakness-heuristics.test.ts` — 37 lines), matching `web/lib/dashboard-data.ts` and `web/lib/weakness-heuristics.ts`.
- `web/tests/e2e/*.spec.ts` — Playwright specs, one per route: `dashboard.spec.ts` (23 lines), `playground.spec.ts` (16 lines), `review.spec.ts` (23 lines) — thin smoke-style specs, not exhaustive interaction coverage.

## Test Structure

**Python — FastAPI route testing (`tests/test_proxy.py`):**
```python
from fastapi.testclient import TestClient
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse

def test_generate_happy_path(): ...
def test_generate_blocks_injection(): ...
def test_generate_enforces_rate_limit(monkeypatch): ...
def test_generate_validates_structured_schema(): ...
def test_generate_schema_failure_returns_422(): ...
def test_generate_rejects_malformed_request(): ...
def test_generate_rejects_oversized_input(): ...
def test_generate_does_not_scan_system_prompt_for_injection(): ...
def test_generate_returns_502_when_both_providers_fail(): ...
def test_generate_flags_secret_leakage_in_response(): ...
def test_generate_scores_hallucination_when_grounded(): ...
def test_generate_skips_hallucination_without_grounding(): ...
```
One test function per behavior/scenario, named after the exact behavior asserted (happy path, each guardrail rejection, each failure mode) rather than grouped into broad "test the endpoint" tests. `monkeypatch` is the standard mechanism for injecting fakes (e.g. overriding rate limiter state).

**Architecture-enforcement test (`tests/agents/test_no_direct_provider_calls.py`):** a static-analysis test, not a runtime test — it AST-parses every `.py` file under `agents/` and asserts no forbidden provider SDK (`groq`, `google.generativeai`) is imported. This is the project's mechanism for keeping the "agents never call a provider directly" architecture invariant true over time, independent of behavioral coverage.

**Web — vitest unit test:** plain `describe`/`it`/`expect` structure against pure exported functions from `web/lib/*.ts` (no component rendering, no mocking framework needed since the functions under test are pure).

**Web — Playwright e2e:** short specs (~20 lines each) hitting one route per file, asserting page loads and key UI elements/flows are present — smoke-level e2e, not deep interaction coverage.

## Mocking

**Python:** dependency overrides via FastAPI's `app.dependency_overrides` / direct monkeypatching of provider functions (`get_provider` imported directly in `test_proxy.py` implies provider mocking at the dependency level). `LLMResponse` (from `proxy/provider.py`) is imported directly into tests to construct fake provider responses — tests never hit a live LLM provider for standard unit/integration runs (per `testing.md` §4: "Never require a live provider for normal unit tests").
- `pytest`'s `monkeypatch` fixture is the primary mocking mechanism (seen in `test_generate_enforces_rate_limit(monkeypatch)`).

**Web:** no explicit mocking library in `package.json` beyond what `@testing-library/react` and `vitest` provide natively (`vi.fn`/`vi.mock` available via vitest but not yet exercised in the two current unit-test files, since they test pure functions).

## Fixtures and Factories

**Python:** `tests/fixtures/` directory holds static fixture data (OCR text samples, receipt images/JSON) used by extractor/forensics/report-writer tests per the strategy in `testing.md` (clean receipt, missing vendor/date/total, noisy OCR, adversarial OCR text, genuine/recompressed/altered/spliced images, missing/inconsistent EXIF).

**Data generation:** `data/generate_synthetic_data.py` and `data/vendor_pool.py` produce the synthetic labeled dataset (`data/labels.csv`, `data/synthetic_receipts/`) used by evaluation tests (`tests/test_dataset_integrity.py`, `tests/test_eval_metrics.py`, `tests/test_eval_suite_smoke.py`) and by `scripts/run_eval_suite.py`. Held-out injection attack prompts for evaluation live in `data/holdout_injection_prompts.json`, kept separate from any prompts used to build the detector itself so injection-detection metrics aren't measured against training data.

## Coverage

**Requirements:** None enforced — no `pytest-cov`, no coverage threshold in CI or `pytest.ini`. Coverage is governed qualitatively by `testing.md`'s "Phase Test Matrix" (each of the 8 development phases lists required test types and a release-gate condition) rather than a numeric target.

## Test Types (per `testing.md`'s documented strategy)

The project defines 6 layers in `testing.md` (root): Unit → Component → Integration → End-to-End → Evaluation → Security. In the actual `tests/` directory this maps roughly to:

- **Unit:** `test_injection_detector.py`, `test_pii_scanner.py`, `test_schema_validator.py`, `test_rate_limiter.py`, `test_hallucination_scorer.py`, `test_grounding.py`.
- **Component/Integration:** `test_proxy.py` (FastAPI route + guardrail composition), `test_provider.py` (adapter with mocked provider), `test_graph.py`/`tests/agents/*` (LangGraph node behavior + full pipeline), `test_db_persistence.py`.
- **Evaluation:** `test_eval_metrics.py`, `test_eval_suite_smoke.py`, `test_eval_dashboard.py`, `test_dataset_integrity.py`.
- **Security/adversarial:** `test_security_hardening.py`, `test_sample_attacks.py`, `test_playground_proxy_integration.py`, `test_playground_quota.py`.
- **Deployment smoke:** `test_deployment_smoke.py`.
- **E2E (browser):** delegated to `web/tests/e2e/*.spec.ts` (Playwright) plus manual/ad-hoc browser sessions captured under `.playwright-cli/` (page/console dumps from interactive Playwright-CLI sessions — not automated assertions, but exploratory UI verification artifacts).

**Gap:** no equivalent architecture-enforcement test exists for `web/` (i.e., nothing statically checks that `web/lib/api.ts` never bypasses the proxy/agents API the way `tests/agents/test_no_direct_provider_calls.py` does for Python agents) — if that invariant matters on the TS side too, it currently relies on code review only.

## CI Setup

**`.github/workflows/ci.yml`** — single job, runs on every push and PR:
```yaml
runs-on: ubuntu-latest
steps:
  - actions/checkout@v4
  - actions/setup-python@v5 (python-version: "3.11")
  - pip install -r requirements.txt
  - pytest
```
Only the Python test suite runs in CI. Gaps versus the documented CI quality gate in `testing.md` §11 (`install → lint/static checks → unit → component → integration → security checks → evaluation smoke test`):
- No lint/static-check step (no `ruff`/`flake8`/`mypy` invocation in CI).
- No explicit `npm run test` / `npm run test:e2e` step for `web/` — the Next.js app's vitest and Playwright suites are not run in CI at all.
- No separate security-scan step (secret scanning, dependency vulnerability scanning) beyond whatever `pytest` security-focused tests cover in-process.
- No live-provider smoke test stage (consistent with `testing.md`'s guidance that live provider tests should be separately controlled, not required per PR — but no such separate workflow exists either).

## Common Patterns

**Guardrail rejection testing (Python):** tests assert on HTTP status codes returned by the proxy for each guardrail category (injection block, rate limit, oversized input, malformed request, schema validation failure → 422, both providers down → 502, secret leakage flagged) rather than only testing the guardrail functions in isolation — both the pure-function unit test and the end-to-end route-level assertion exist for the same behavior.

**Never-crash-the-caller testing:** given the `agents/graph.py` node pattern (catch, record to `state["errors"]`, continue), the corresponding tests (`tests/agents/test_graph.py`) are expected to assert that a failing stage still yields a completed `FraudCaseState` with the error recorded and downstream fields `None`, not a raised exception.

---

*Testing analysis: 2026-09-21*
