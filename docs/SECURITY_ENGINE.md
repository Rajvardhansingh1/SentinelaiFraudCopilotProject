# SentinelAI Security Testing Engine (D-042, phase_dev_upgrade.md Phase 3)

## Pipeline

```
TEST DEFINITION  ->  EXECUTION  ->  EVALUATION  ->  RESULT (+ EVIDENCE)
 SecurityTest         .run()         .evaluate()      TestResult
```

- **`proxy/engine/models.py`** — `SecurityTest` (definition), `RawExecution`
  (execution output = evidence), `TestResult` (evaluated outcome), `Severity`,
  `TestStatus` (`PASS`/`FAIL`/`ERROR`/`NOT_RUN`/`INCONCLUSIVE` — never
  collapsed to a boolean, per Phase 4's requirement, built in from day one).
- **`proxy/engine/runner.py`** — `run_test()`/`run_suite()`. A plugin's `run`
  or `evaluate` raising becomes `TestStatus.ERROR`, never an uncaught
  exception.
- **`proxy/engine/registry.py`** — `register()`/`all_tests()`. The only
  extension point; the runner never branches on attack type.
- **`proxy/engine/plugins/`** — attack-specific test definitions. Currently
  one plugin: `injection_tests.py`, migrating the existing 4 playground
  sample attacks (`frontend/data/sample_attacks.py`) to run against the real
  `proxy/middleware/injection_detector.py::check_injection()`.

## Every `SecurityTest` carries

`id`, `name`, `category`, `description`, `severity`, `attack_input`,
`expected_behavior`, plus its own `run`/`evaluate` callables. A `TestResult`
adds `status`, `detail`, `evidence` (`RawExecution`: raw input/output,
provider, model), `executed_at`, and `reproduction` (enough to re-run the
exact same test later).

## Adding a new attack category

1. New module in `proxy/engine/plugins/`, e.g. `system_prompt_extraction.py`.
2. Define `run(test) -> RawExecution` (call whatever needs calling — a
   detector, a provider, the full `/v1/generate` path) and
   `evaluate(evidence) -> (TestStatus, str)`.
3. `@register` a builder function returning a `list[SecurityTest]`.
4. Import the module from `proxy/engine/plugins/__init__.py`.

Nothing in `proxy/engine/runner.py` or `proxy/main.py` changes.

## Attack categories (Phase 4)

| Category | Plugin | Evaluation mechanism |
|---|---|---|
| `prompt_injection` | `injection_tests.py` | `check_injection()` (pattern match) |
| `jailbreak` | `jailbreak_tests.py` | `check_injection()` (pattern match) |
| `system_prompt_extraction` | `system_prompt_extraction_tests.py` | `check_injection()` (pattern match) |
| `sensitive_information_disclosure` | `sensitive_disclosure_tests.py` | `check_pii()` on a simulated model output |
| `unsafe_output_behavior` | `unsafe_output_tests.py` | none yet — always `INCONCLUSIVE` |

`unsafe_output_behavior` is honest about a real gap: SentinelAI has no
harmful-content/toxicity classifier. Per phase_dev_upgrade.md's own warning
("do not claim that a model is secure simply because tests pass"), these
tests report `INCONCLUSIVE`, never a fabricated `PASS`/`FAIL`. See the
`ponytail:` comment in `unsafe_output_tests.py` for the upgrade path.

## Severity rubric

Assigned per test at definition time, based on what a successful bypass would
let through in Fraud Copilot's context (D-002/D-004 — the human is always the
final decision-maker, so severity here means "how much this misleads or
burdens that human," not "does it auto-cause harm"):

- **CRITICAL** — full behavior override (jailbreak takeover) or a bypass that
  could push toward an incorrect fraud verdict (e.g. `policy_override`).
- **HIGH** — leaks system instructions or defeats a single safety control
  without full takeover.
- **MEDIUM** — partial information leak or a lower-impact bypass attempt.
- **LOW** — reserved for benign/diagnostic test cases.

## Running the built-in suite

`POST /v1/security-tests/run` (proxy/main.py, D-043) runs every registered
test and returns each `TestResult`, JSON-serialized. All current tests are
local (pattern/regex based) — no LLM or network calls, safe to run
synchronously per request. The Next.js `/security` page
(`web/app/security/page.tsx`) calls this and renders every result with a
status badge that keeps `PASS`/`FAIL`/`ERROR`/`NOT_RUN`/`INCONCLUSIVE`
visually distinct — never collapsed into a single boolean, per Phase 4's
explicit requirement for a security product.

## Scope note

Phase 3 was the framework + migration only. Phase 4 (this) adds the
jailbreak/system-prompt-extraction/sensitive-disclosure/unsafe-output
categories and the run endpoint + UI. Phase 5's Findings subsystem builds on
`TestResult`, it doesn't change this pipeline.
