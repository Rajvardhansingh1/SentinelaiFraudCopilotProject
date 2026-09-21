# Codebase Concerns

**Analysis Date:** 2026-09-21

## Tech Debt

**PII scanner is regex + optional Presidio, response PII never acts on the result (OD-003 still open):**
- Issue: `proxy/main.py` computes `pii_resp = check_pii(llm_resp.text)` for the LLM's *response* and merges it into `guardrails.pii`, but never blocks, redacts, or retries when `pii_resp.found` is true — the raw (possibly PII-bearing) `llm_resp.text` is returned as `output` regardless. `decision.md` OD-003 ("PII response action: redact, block, retry, or structured failure?") is recorded as still **Open** — this is a documented gap, not an oversight, but it is live in shipped code.
- Files: `proxy/main.py:168-173`, `proxy/middleware/pii_scanner.py`
- Impact: Any PII the LLM echoes back (e.g. from OCR'd receipt text containing a real name/card number) reaches the caller unredacted; the guardrail flag is informational only on the response path (it *does* block on the inbound path via `injection.flagged`, but there is no equivalent inbound PII block — PII is never inbound-blocking either, only inbound-detected).
- Fix approach: Decide and implement one of block/redact/retry for `pii_resp.found` before treating PII protection as complete; `redact_pii()` already exists in the same module and is unused by `proxy/main.py`.

**In-memory rate limiter is single-process and resets on restart:**
- Issue: `proxy/middleware/rate_limiter.py` keys `_session_counts` on a plain in-process `dict`, explicitly marked `# ponytail: in-process counter, single-worker demo deployment assumed`.
- Files: `proxy/middleware/rate_limiter.py:5-7`
- Impact: A multi-worker/multi-instance deployment (e.g. Render autoscaling, or `uvicorn --workers >1`) silently gives each worker its own counter, multiplying the effective per-session quota N-fold with no error or warning. A process restart also silently resets everyone's quota.
- Fix approach: Named upgrade path already documented in the source comment — move to a shared store (Redis) if the proxy ever runs multi-worker. Not needed for the current single-worker deployment target (Render free tier, one instance).

**Grounding store persistence is conditional on `chromadb` import success:**
- Issue: `proxy/eval/grounding.py::get_grounding_store()` falls back to `InMemoryTFIDFStore` (non-persistent, process-local) if `chromadb` fails to import/construct, with no visible signal to the operator that persistence silently degraded.
- Files: `proxy/eval/grounding.py`
- Impact: If `chromadb` fails at deploy time (e.g. disk/permissions issue on Render's free tier — flagged as a real risk in `decision.md` D-030), grounding retrieval keeps working but loses persistence across restarts with no log/alert.
- Fix approach: Log a warning when falling back to the in-memory store so the degradation is visible in production logs, not just inferred from behavior.

**`frontend/db/models.py`'s `ReviewDecision` is a duplicated, unmigrated copy of `agents/db/models.py`'s:**
- Issue: `decision.md` D-035/OD-019 explicitly records this as intentional-but-temporary: the Streamlit app writes its own `ReviewDecision` rows to the same SQLite file as the new `agents/db/models.py` copy, and the two are never reconciled.
- Files: `frontend/db/models.py`, `agents/db/models.py`
- Impact: Review decisions made via the (retired, D-038) Streamlit UI and the (active) React+`agents/api.py` path can diverge — a decision recorded in one is invisible to a dashboard reading the other's table, depending on which ORM model queries which rows.
- Fix approach: Since `frontend/` is retired (D-038, soft retirement — code kept on disk but not the recommended UI), delete or freeze `frontend/db/models.py`'s write path so no new divergent rows are created; keep `agents/db/models.py` as the single source of truth.

## Known Bugs (fixed, but pattern worth re-checking on new code)

`decision.md` records three real bugs found via live testing (not caught by the mocked test suite), all now fixed — the underlying pattern is worth watching for regressions in any new HTTP/provider code:

- **D-031:** `proxy/provider.py`'s `GroqProvider`/`GeminiProvider` originally only wrapped the API call in `try/except ProviderError`, not the SDK import itself — a missing package raised an uncaught `ModuleNotFoundError` that skipped the except clause and 500'd `/v1/generate` with a non-JSON body. Fixed by moving the import inside the try block.
- **D-031:** `agents/proxy_client.py::call_proxy()` originally called `resp.json()` outside the try/except, so a non-JSON response body (exactly what the bug above produces) raised an uncaught `JSONDecodeError` in whichever LangGraph node called it. Now fixed (`.json()` is inside the try in the current source, `agents/proxy_client.py:35`).
- **D-031:** `frontend/lib/proxy_client.py::call_generate()` had no try/except at all originally; now returns a synthetic 503 `proxy_unreachable` envelope on `requests.RequestException` (current source, `frontend/lib/proxy_client.py:38-43`).
- **D-032:** `agents/report_writer.py::write_report()` originally passed evidence only via `grounding_context` (used only for post-hoc hallucination scoring, never injected into the actual LLM prompt by the proxy) — every real report call refused for lack of evidence. Fixed by embedding evidence directly in the user message content.
- **D-033:** `proxy/main.py` originally scanned the *entire* message list (including the caller's own system prompt) for injection/PII, so the playground's own anti-jailbreak system prompt (containing phrasing like "act as a different persona") self-tripped the `role_override` pattern on every single request, including completely benign ones. Fixed by scanning only non-`system`-role content (current source, `proxy/main.py:102-107`).

None of these bugs were caught by the existing test suite because tests mock `call_proxy`/the provider layer and never exercise real prompt-following or real transport-failure behavior — this is a structural test-coverage gap (see Test Coverage Gaps below), not just three isolated incidents.

## Security Considerations

**No authentication/authorization on either backend service — CORS is the only access control:**
- Risk: `proxy/main.py` (`/v1/generate`, `/quota`, `/health`) and `agents/api.py` (`/v1/analyze-receipt`, `/v1/review-decisions`, `/v1/calls`) have no API key, bearer token, or session auth of any kind. `CORSMiddleware` with `allow_origins=settings.allowed_origins_list` is the only restriction, and CORS is a browser-enforced policy — it does not stop a direct `curl`/script/server-to-server call from any origin, only cross-origin `fetch()` from a browser tab.
- Files: `proxy/main.py:42-48`, `agents/api.py:32-38`, `proxy/config.py:19-25`
- Current mitigation: None beyond CORS + the rate limiter (which is per-`session_id`, itself unauthenticated — see below) + `MAX_INPUT_CHARS` size cap + the injection/PII detectors.
- Recommendations: Acceptable for a demo/portfolio deployment where the API surface is not meant to be a real production multi-tenant service, but should be flagged explicitly before any real usage — anyone who has the Render URL can call `/v1/generate` directly, exhaust the shared Groq/Gemini quota, or read `/v1/calls` (full call log, no pagination auth) and `GET /v1/calls?limit=N` in `agents/api.py`, which returns raw `CallLog` rows including `guardrails` JSON.

**Rate limiting is keyed on a client-supplied, unvalidated `session_id`:**
- Risk: `check_and_increment(req.session_id)` in `proxy/main.py:140` trusts whatever `session_id` string the caller sends in the request body — there is no server-issued session token. A client can bypass the per-session quota entirely by sending a new random `session_id` on every request.
- Files: `proxy/middleware/rate_limiter.py`, `proxy/main.py:140`, `proxy/schemas.py` (`GenerateRequest.session_id`)
- Current mitigation: None. This is consistent with the project's stated scope (`decision.md` frames the rate limiter as a per-session UX quota display, not a hard anti-abuse control) but is a real bypass if anyone treats it as abuse protection.
- Recommendations: Fine for the demo's purpose (showing users "you have N/8 calls left"); would need IP-based or authenticated-identity rate limiting before being a real abuse control.

**PII "card" regex is unvalidated digit-run matching, not a real card-number check:**
- Risk: `proxy/middleware/pii_scanner.py:8` — `"card": re.compile(r"\b(?:\d[ -]*?){13,16}\b")` matches *any* 13-16 digit run (with optional spaces/hyphens), with no Luhn checksum or BIN-prefix validation. It will false-positive on things like long order numbers, phone extensions, or receipt line totals concatenated with quantities, and equally will not distinguish a real card number from a random 16-digit string.
- Files: `proxy/middleware/pii_scanner.py:8`
- Impact: Both false positives (legitimate receipt content flagged as PII, though this is currently non-blocking per the OD-003 gap above) and false negatives are possible; the regex is a coarse heuristic, not a validated instrument.
- Recommendations: Add a Luhn check as a cheap filter to reduce false positives if this pattern ever becomes blocking (currently it's detection-only, so the cost of false positives is limited to a flag in `guardrails.pii`, not a wrongly-blocked request).

**Injection detector is pure keyword/regex pattern matching (OD-002 still open) — trivially bypassable by paraphrase:**
- Risk: `proxy/redteam/attack_library.py`'s 10 `ATTACK_PATTERNS` are literal English-phrase regexes (`"ignore (all |any |previous |prior )*instructions"`, `"you are now|act as|..."`, etc.). Any semantically-equivalent attack phrased differently (synonyms, different word order, non-English, base64/unicode obfuscation beyond the one `encoded_payload` pattern, split across multiple messages) passes through undetected. `decision.md` OD-002 ("select the lightweight classifier approach and define whether pattern detection alone can block") is recorded as still **Open**.
- Files: `proxy/redteam/attack_library.py`, `proxy/middleware/injection_detector.py`
- Current mitigation: None beyond the pattern list — this is a known, documented MVP ceiling (matches the project's own red-team playground framing: it exists specifically to demonstrate what basic guardrails do and don't catch).
- Recommendations: Acceptable for the stated demo purpose (`decision.md` frames this as illustrating guardrail concepts, not shipping production-grade jailbreak defense); would need a real classifier (fine-tuned model or LLM-based judge) before being presented as robust injection defense.

**Hallucination scorer (D-017) and confidence (D-026) are lexical-overlap heuristics, explicitly documented as non-semantic:**
- Risk: `score_grounded`'s per-claim comparator is token-overlap ratio (≥0.5 → "supported"), vulnerable to paraphrase/synonym false-unsupported and, conversely, keyword-stuffing false-supported (repeating grounding-context words without actually asserting the same claim would inflate the overlap ratio).
- Files: `proxy/eval/hallucination_scorer.py` (per D-017's description; not separately re-read here beyond decision.md's own characterization)
- Current mitigation: `decision.md` D-017/D-026 both explicitly document this as an MVP ceiling with a named upgrade path (swap in `cross-encoder/nli-deberta-v3-base` without changing the module's public interface) and mandate the UI label the derived "confidence" honestly rather than overclaiming.
- Recommendations: Already tracked; not a hidden risk — flagged here for completeness since it affects the fraud-report trust signal shown to a human reviewer.

## Fragile Areas

**Three parallel proxy-client implementations with duplicated request-building logic:**
- Files: `agents/proxy_client.py` (40 lines), `frontend/lib/proxy_client.py` (43 lines, retired per D-038 but still on disk and still functional), `web/lib/api.ts` (137 lines, TypeScript, active)
- Why fragile: `agents/proxy_client.py::call_proxy()` and `frontend/lib/proxy_client.py::call_generate()` both independently build the same `{session_id, operation, messages, schema_name, grounding_context}` POST body to `/v1/generate` and both independently hardcode `PROXY_BASE_URL = os.environ.get("PROXY_BASE_URL", "http://localhost:8000")`. Any change to the request contract (e.g. a new required field, D-015's contract evolving) must be applied in up to three places (two Python + the TS client) with no shared module enforcing consistency. `frontend/lib/proxy_client.py` is retired-but-not-deleted (D-038), so it can silently drift out of sync with the real contract without anyone noticing, since it no longer has active users exercising it.
- Safe modification: When changing the `/v1/generate` request/response contract, grep all three files (`agents/proxy_client.py`, `frontend/lib/proxy_client.py`, `web/lib/api.ts`) rather than assuming one canonical client.
- Test coverage: `tests/test_pipeline_client.py`, `tests/test_frontend_proxy_client.py` cover the two Python clients against mocked responses (see Test Coverage Gaps — mocked only, missed 3 of the real bugs above).

**Forensics ELA signal has a documented, unresolved accuracy ceiling (OD-018, open):**
- Files: `agents/forensics.py::_ela_score()`, thresholds `ELA_HIGH_THRESHOLD = 0.0095` / `ELA_MEDIUM_THRESHOLD = 0.0085`
- Why fragile: `decision.md` D-025 records a measured finding against the full 45-genuine/45-tampered dataset: genuine block-max mean ≈0.0087 vs tampered ≈0.0088 — heavy overlap, tampered bottom-5 scores fall *below* genuine's own median. Root cause is architectural to the synthetic dataset (flat white-background renders lack the natural texture/noise a real scanned receipt would have, so ordinary JPEG text-edge artifacts are comparable in magnitude to the deliberate tamper patch's artifacts).
- Safe modification: Do not retune `ELA_HIGH_THRESHOLD`/`ELA_MEDIUM_THRESHOLD` further against this dataset expecting a real accuracy gain — the thresholds are already set from the dataset's actual measured distribution, not guessed, and the ceiling is a signal-strength problem, not a threshold-calibration problem. OD-018 lists four real fix options (stronger tamper patch, textured synthetic backgrounds, treat EXIF as primary signal, or explicitly caveat ELA numbers in Phase 7's report) — none implemented.
- Test coverage: `tests/test_failure_modes.py` and the eval suite (`scripts/run_eval_suite.py`) measure and report real (mediocre) precision/recall for this signal rather than hiding it — per `decision.md`, this is treated as an honest finding, not silently patched.

**Deployment topology has known-unfinished pieces:**
- Files: `deploy/render.yaml`, `PHASE7_PLAN.md`
- Why fragile: `decision.md` D-035/D-036 both flag that `deploy/render.yaml` was not updated for the two-Render-service topology (`proxy/main.py` + `agents/api.py`) introduced by D-035, and `PHASE7_PLAN.md` was not revised for the Vercel/Render split (D-036). `state.md`'s "Next executable step" confirms deployment is not yet live and needs a second Render service block plus real production `ALLOWED_ORIGINS`.
- Safe modification: Before deploying, reconcile `deploy/render.yaml` against the current three-service reality (SentinelAI proxy, Fraud Copilot API, Next.js frontend) rather than assuming the existing YAML is current.

## Test Coverage Gaps

**Real-integration bugs invisible to the mocked test suite:**
- What's not tested: All three D-031/D-032/D-033 bugs above were found via live Groq calls and real Playwright browser testing, specifically because the existing unit tests mock `call_proxy`/the provider SDK boundary and never exercise real prompt-following behavior, real transport failures, or the real system-prompt content interacting with the real injection detector.
- Files: the mocked equivalents are `tests/test_pipeline_client.py`, `tests/test_frontend_proxy_client.py`, `tests/test_provider.py`, `tests/test_proxy.py`
- Risk: Any future change to prompt construction, provider SDK usage, or the trust boundary between system/non-system messages could reintroduce a similar class of bug without the test suite catching it, since none of these tests hit a real LLM provider or a real end-to-end HTTP round trip.
- Priority: Medium — `tests/test_deployment_smoke.py`/`tests/test_eval_suite_smoke.py` exist and are skipped without a live proxy/LLM keys (`state.md`: "109 tests passing, 3 skipped — need a live deployment/LLM keys, not run in this session"), meaning the closest thing to integration coverage is opt-in and currently not exercised in CI.

**Playwright e2e tests written but never executed in this environment:**
- What's not tested: `web/tests/` (Playwright specs) exist per `state.md` but "no network egress for the browser binary in this environment" — they have not run against the current build.
- Files: `web/tests/`, `web/playwright.config.ts`
- Risk: Any regression in the React frontend's actual rendered behavior (as opposed to component/unit tests) would not be caught until a manual run.
- Priority: Medium — flagged explicitly in `state.md` as a known gap, not a silent one.

**PII response-blocking has no test because there is no behavior to test (OD-003 open):**
- What's not tested: Since `proxy/main.py` never acts on `pii_resp.found` (see Tech Debt above), there is no test exercising "PII in the response gets redacted/blocked" — only detection-level tests exist (`tests/test_pii_scanner.py`).
- Files: `tests/test_pii_scanner.py`, `proxy/main.py`
- Risk: If OD-003 is resolved later without corresponding test additions, regressions in the new block/redact path would be uncaught.
- Priority: Low until OD-003 is actually resolved (tracked as an open decision, not a silent gap).

---

*Concerns audit: 2026-09-21*
