# Testing Strategy — SentinelAI + Fraud Copilot

## 1. Testing Philosophy

Testing is a release gate, not a final cleanup step.

Every development phase must have:
- unit tests
- integration tests where components interact
- negative/error-path tests
- security tests for exposed attack surfaces
- acceptance tests tied to the phase spec

No phase is complete because the happy path works.

## 2. Test Layers

### Layer 1 — Unit tests

Test pure functions and isolated components:
- injection pattern matching
- PII/secret detection
- schema validation
- rate-limit calculations
- claim scoring
- grounding helpers
- OCR normalization
- forensic feature extraction
- policy rule evaluation
- metric calculations

### Layer 2 — Component tests

Test a module with its immediate dependencies:
- FastAPI routes
- provider adapter with mocked provider
- Chroma grounding adapter
- database repository
- LangGraph node behavior
- Streamlit component logic where testable

### Layer 3 — Integration tests

Test cross-component behavior:
- proxy → mocked LLM
- proxy → DB
- evaluator → Chroma
- extractor → proxy
- policy checker → proxy
- report writer → proxy
- full LangGraph pipeline

### Layer 4 — End-to-end tests

Test user-visible workflows:
1. Open app.
2. Run red-team sample.
3. Observe guardrail result.
4. Select sample receipt.
5. Run fraud pipeline.
6. Inspect evidence.
7. Perform human review action.

### Layer 5 — Evaluation tests

Run labeled synthetic data and calculate actual metrics.

### Layer 6 — Security tests

Treat all external input as hostile.

## 3. Phase Test Matrix

| Phase | Required tests | Release gate |
|---|---|---|
| 0 | config/repo/test-runner smoke | test runner passes |
| 1 | proxy unit + integration + security | proxy contract passes |
| 2 | scorer + grounding + DB tests | both scoring modes pass |
| 3 | playground + browser + quota | sample demo works |
| 4 | agent unit + graph integration | complete sample pipeline works |
| 5 | dataset + metrics + held-out attacks | evaluation reproducible |
| 6 | UI + browser + review flow | human review flow works |
| 7 | CI + deployment + security + E2E | release gate passes |

## 4. SentinelAI Tests

### Injection detector

Test:
- role-play jailbreaks
- instruction override
- system prompt extraction attempts
- encoded/obfuscated examples
- benign text that contains attack-like words
- OCR-derived adversarial text
- empty input
- oversized input

Track:
- true positives
- false positives
- false negatives on held-out examples

### PII/secret scanner

Test:
- email
- phone
- card-like number
- API-key-shaped token
- multiple PII entities
- mixed benign text
- secrets in requests
- secrets in model responses

Verify:
- detection behavior
- redaction/blocking behavior once specified
- logs do not contain raw secrets

### Schema validator

Test:
- valid response
- missing required field
- wrong type
- extra field behavior
- malformed JSON
- provider response wrapped in unexpected text
- first failure then valid retry
- repeated failure

### Rate limiter

Test:
- calls below limit
- exact boundary
- call over limit
- separate sessions
- cached response path
- quota metadata

### Provider adapter

Never require a live provider for normal unit tests.

Mock:
- success
- timeout
- rate limit
- malformed response
- provider error
- token usage unavailable

## 5. Evaluation Layer Tests

### Grounded scoring fixtures

Create known examples:

| Response claim | Grounding | Expected |
|---|---|---|
| Exact supported fact | supports it | supported |
| Opposite of source | contradicts it | contradicted |
| New unsupported fact | absent | unsupported |

Test zero claims, one claim, and multiple claims.

### Ungrounded scoring

Use deterministic test doubles for generations so tests do not depend on stochastic LLM output.

Test:
- identical generations
- partially different generations
- fully different generations
- unavailable generation
- insufficient samples

### Chroma

Test:
- insert
- retrieve
- empty collection
- irrelevant query
- deterministic fixture retrieval
- persistence/reload

## 6. Fraud Agent Tests

### Extractor

Build OCR fixtures with:
- clean receipt
- missing vendor
- missing date
- missing total
- multiple line items
- noisy OCR
- adversarial OCR text

Verify structured output contract.

### Forensics

Fixture categories:
- genuine image
- recompressed image
- altered amount
- altered date
- spliced region
- missing EXIF
- inconsistent EXIF

Do not assert that ELA alone proves fraud.

### Policy Checker

Test:
- under limit
- over limit
- restricted category
- old receipt
- multiple violations
- no violation
- missing field

### Report Writer

Test:
- evidence-only report
- conflicting evidence
- missing evidence
- unsupported claim attempts
- valid structured output
- schema failure/retry

## 7. End-to-End Test Cases

### E2E-001 Genuine receipt
Expected:
- OCR succeeds or returns controlled extraction failure.
- Forensics does not create an unexplained hard failure.
- Policy result is produced.
- Report is grounded.
- Human review remains required.

### E2E-002 Tampered receipt
Expected:
- Tampering signal is surfaced.
- Evidence appears in report.
- Human review remains required.

### E2E-003 Image-embedded injection
Expected:
- OCR extracts adversarial text.
- SentinelAI detects/evaluates it before the relevant LLM call.
- Policy/report path does not silently treat the injected instruction as trusted instruction.

### E2E-004 Playground jailbreak
Expected:
- Attack is detected/blocked according to final policy.
- Metadata is visible.
- No general chatbot behavior is exposed.

### E2E-005 Quota exhaustion
Expected:
- Live call is denied after configured cap.
- Cached sample path can be returned where configured.
- User sees explicit quota state.

### E2E-006 Provider failure
Expected:
- Timeout/rate-limit/provider error produces controlled failure.
- No partial result is presented as a final verdict.

## 8. UI/UX Testing

For the Streamlit app verify:
- clear primary actions
- upload state
- processing state
- cold-start state
- success state
- error state
- quota state
- human review state
- evidence hierarchy
- guardrail metadata visibility
- no accidental approval/rejection
- readable charts
- keyboard/accessibility behavior where supported

Use browser automation/visual QA after the UI is actually rendered.

## 9. Security Testing

At minimum:
- secret scanning
- dependency vulnerability scanning
- malformed JSON
- oversized request
- malicious file upload
- path traversal attempts
- prompt injection
- OCR injection
- log leakage
- unsafe YAML handling
- SSRF considerations if URLs ever become inputs
- database query safety
- environment/secrets handling
- rate-limit bypass attempts

Third-party skills/plugins must also be reviewed before installation because they can extend the coding agent's execution surface.

## 10. Evaluation Metrics

### Extraction accuracy
Calculate field-level correctness.

### Tamper detection
Calculate:
- precision
- recall
- optionally F1

### Policy detection
Calculate accuracy against labeled policy outcomes.

### Hallucination
Report distribution, not just one aggregate number.

### Injection
Use a held-out attack set.

### Latency
Measure upload-to-verdict and major stage timings.

Do not compare metrics across different dataset definitions without documenting the population.

## 11. CI Quality Gate

Target CI sequence:

```text
install dependencies
→ lint/static checks
→ unit tests
→ component tests
→ integration tests
→ security checks
→ evaluation smoke test
```

Live provider tests should not be required for every pull request. Use mocks and a separately controlled live smoke test.

## 12. Test Evidence

For meaningful phase completion, preserve:
- command run
- pass/fail
- test count
- relevant metric output
- known failures
- environment caveats

Record the summary in `progress_log.md` and current blockers in `state.md`.
