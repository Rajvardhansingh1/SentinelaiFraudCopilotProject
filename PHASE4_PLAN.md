# Phase 4 Plan — Fraud Copilot Agents

Planning only. No app code touched by this document's author.

## 1. Scope recap

Build four independently-testable agents (Extractor, Forensics, Policy-Checker,
Report-Writer) and wire them into a LangGraph pipeline (`agents/graph.py`).
Extractor/Policy-Checker/Report-Writer call the LLM only via SentinelAI's
`POST /v1/generate` (existing contract, D-015) — never a provider SDK.
Forensics is pure local CV/EXIF, no LLM. OCR (RapidOCR, D-014) runs locally;
its output is untrusted text that flows into a proxy call, where the existing
injection detector (S2) and PII scanner (S3) already inspect it — nothing
extra needed in agent code for that. Human review/approval is out of scope
here (Phase 6); agents only produce evidence + a non-binding verdict.

## 2. File plan — `agents/`

```
agents/
├── CLAUDE.md                 # module conventions: no provider SDK imports, state contract summary
├── graph.py                  # LangGraph StateGraph: builds nodes, edges, compiles app
├── state.py                  # FraudCaseState TypedDict (shared state contract)
├── proxy_client.py           # thin HTTP wrapper around POST /v1/generate (reused by all 3 LLM-calling agents)
├── extractor.py              # run_ocr() + extract_fields() node fn
├── forensics.py              # run_ela() + check_exif() + analyze() node fn
├── policy_checker.py         # load_policy() + check_policy() node fn
├── report_writer.py          # write_report() node fn
└── policies/
    └── expense_policy.yaml   # rule data, not code
```

- `state.py` is new vs. the original repo-structure sketch in the source spec
  (section 8 only lists `graph.py`); splitting the state contract out is a one-line
  justified deviation (LangGraph nodes and tests both need to import the state type
  without importing the whole graph) — not a new abstraction, just a placement choice.
- `proxy_client.py` is likewise a small addition beyond the original sketch: three
  agents make the identical HTTP call shape, so one `call_proxy(session_id, operation,
  messages, schema_name=None, grounding_context=None) -> dict` function (using
  `requests`, already a proxy dependency) avoids repeating request/error handling
  three times. This is the file that is statically checked for "no provider SDK
  import" together with the other agent files (see §8).

## 3. Extractor agent (`agents/extractor.py`)

1. `run_ocr(image_path: str) -> str` — `rapidocr_onnxruntime.RapidOCR()(image_path)`,
   join recognized text lines with `\n`. Runs fully local, no proxy call. On OCR
   failure (unreadable image, engine exception) raise a typed `OcrError` — do not
   return empty string silently (CLAUDE.md §11: failures must be explicit).
2. Build the proxy request:
   ```python
   call_proxy(
       session_id=session_id,
       operation="extract",
       messages=[
           {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
           {"role": "user", "content": ocr_text},
       ],
       schema_name="receipt_fields",
   )
   ```
   `EXTRACTOR_SYSTEM_PROMPT` instructs the model to return vendor/date/line_items/total
   as JSON matching `ReceiptFields` (already in `proxy/schemas.py`, `SCHEMA_REGISTRY["receipt_fields"]`).
   No new schema needed — reuse `ReceiptFields` exactly as defined.
3. OCR text is the `user` message content, i.e. it goes through `main.py`'s
   `inbound_text` → `check_injection` / `check_pii` path automatically, same as any
   other message content. The agent does not need its own injection check — that
   would duplicate S2 and violate "guardrails live in SentinelAI" (D-001). The
   agent's only job is to *not* bypass the proxy and to *not* trust `output` beyond
   what schema validation already guarantees.
4. Missing OCR fields: per `ReceiptFields`, `vendor`/`date`/`total` default to
   `None` and `line_items` to `[]` — this is the existing Pydantic contract, so
   Phase 4 should follow it as the de facto answer to OD-006 (missing-field
   representation) unless a decision says otherwise. Flag as confirmation-needed
   in §9, don't silently treat it as new.
5. Return shape merged into state: `extracted_fields: dict` (the validated
   `ReceiptFields.model_dump()`), `extraction_guardrails: dict` (the response's
   `guardrails`), `ocr_text: str`.

## 4. Forensics agent (`agents/forensics.py`)

Pure local, no proxy call, no `call_proxy` import.

1. **ELA (Error Level Analysis)**: re-save the image at a fixed JPEG quality
   (e.g. 90) via `cv2.imencode`/`PIL`, diff against the original, amplify the
   difference, and compute a scalar "mean high-frequency residual" — higher means
   more likely locally re-edited/recompressed regions.
2. **EXIF check**: `exifread.process_file` — flag inconsistency signals: missing
   `DateTimeOriginal`, `Software` tag naming an editor (Photoshop/GIMP), or
   modify-date vs. create-date mismatch when present. Missing EXIF entirely is
   common for phone photos and must NOT alone count as tamper evidence (treat as
   a distinct "no_exif_data" flag, not a positive tamper signal — CLAUDE.md §11:
   "do not treat missing evidence as positive evidence").
3. Output — propose a new Pydantic model, since none exists in `proxy/schemas.py`:
   ```python
   class ForensicsResult(BaseModel):
       ela_score: float               # 0.0-1.0, higher = more suspicious
       exif_consistent: bool | None   # None = no EXIF data to evaluate
       exif_flags: list[str] = []
       tamper_likelihood: Literal["low", "medium", "high"]
   ```
   **Open decision (flag, don't resolve):** should `ForensicsResult` live in
   `proxy/schemas.py`'s `SCHEMA_REGISTRY`, or purely in `agents/forensics.py`?
   Since Forensics never calls the proxy, it doesn't need `schema_name` validation
   — putting it in `proxy/schemas.py` would add an unused registry entry and blur
   "SentinelAI is domain-agnostic" (D-001, receipts are a Fraud Copilot concept).
   Recommendation: define it in `agents/forensics.py` (or `agents/state.py` if
   reused across files), NOT in `proxy/schemas.py`. Record this as a decision.md
   entry when Phase 4 actually starts (see §9).

## 5. Policy-Checker agent (`agents/policy_checker.py`)

1. `load_policy(path="agents/policies/expense_policy.yaml") -> dict`, loaded once,
   cached at module level (ponytail: no policy-hot-reload machinery — add if a
   future requirement demands live-editable rules).
2. Minimal concrete YAML:
   ```yaml
   spend_limits:
     default_max_total: 500.00
     category_max:
       meals: 100.00
       travel: 1000.00
       office_supplies: 250.00
   category_restrictions:
     disallowed_categories: ["alcohol", "gifts"]
   receipt_age:
     max_days_old: 90
   ```
3. Proxy call:
   ```python
   call_proxy(
       session_id=session_id,
       operation="policy_check",
       messages=[
           {"role": "system", "content": POLICY_SYSTEM_PROMPT},  # embeds the loaded YAML as text
           {"role": "user", "content": json.dumps(extracted_fields)},
       ],
       schema_name="policy_verdict",
   )
   ```
   Reuses `PolicyVerdict` (`triggered_rules: list[str]`, `compliant: bool`) already
   in `SCHEMA_REGISTRY` — no new schema. The YAML content goes in the system
   message (trusted, agent-authored) with the extracted fields (previously
   OCR-derived, already validated once) as user content.
4. Age check (`receipt_age.max_days_old`) needs "today" and the extracted `date`
   field — if `date` is `None` (OD-006 case), the agent cannot compute age and
   must say so explicitly in the prompt/state rather than assume compliant or
   non-compliant.

## 6. Report-Writer agent (`agents/report_writer.py`)

1. Combines `extracted_fields`, `ForensicsResult`, `PolicyVerdict` into one
   evidence bundle, serialized as the `grounding_context` string passed to the
   proxy — this wires directly into the existing grounded scorer
   (`proxy/eval/hallucination_scorer.py::score_grounded`, D-017) via `main.py`'s
   `if req.grounding_context: guardrails.hallucination = score_grounded(...)`
   (already live, no proxy change needed).
2. `schema_name`: **free text (`None`)**, not a new structured schema. Reasoning:
   the report is meant to be a human-readable audit narrative (source spec §5:
   "structured/human-readable audit report") read by a reviewer in Phase 6's
   Review Screen, not machine-consumed downstream — forcing a rigid schema would
   fight that purpose and there's no consumer requiring structure yet. If Phase 6
   later needs specific fields (e.g. a summary line + confidence number) to
   render distinctly, add a `ReportOutput` schema then — YAGNI for now.
3. Call:
   ```python
   call_proxy(
       session_id=session_id,
       operation="report",
       messages=[
           {"role": "system", "content": REPORT_SYSTEM_PROMPT},
           {"role": "user", "content": "Write the audit report using only the evidence provided."},
       ],
       grounding_context=evidence_bundle_text,
   )
   ```
4. State gets `report_text: str` and `report_guardrails: dict` (carries
   `hallucination.score`/`mode` — surfaced later by the Review Screen per D-004/spec §5).

## 7. LangGraph wiring (`agents/graph.py`, `agents/state.py`)

### State contract (`agents/state.py`)

```python
class FraudCaseState(TypedDict, total=False):
    session_id: str
    image_path: str
    ocr_text: str | None
    extracted_fields: dict | None
    extraction_guardrails: dict | None
    forensics_result: dict | None          # ForensicsResult.model_dump()
    policy_verdict: dict | None            # PolicyVerdict.model_dump()
    policy_guardrails: dict | None
    report_text: str | None
    report_guardrails: dict | None
    errors: list[dict]                     # [{"node": str, "code": str, "message": str}]
```

`total=False` + accumulating `errors` list lets a node fail without crashing
the graph — downstream nodes check `state["errors"]` and either skip
(propagate a partial result) or short-circuit, per node below.

### Node sequence

`Extractor → Forensics → Policy Checker → Report Writer`, linear edges
(`add_edge`), no conditional branching for the MVP — ponytail: a fraud
pipeline is inherently sequential (each stage needs the prior stage's
evidence), a conditional/parallel graph is speculative complexity with no
current requirement. Add branching only if a future requirement needs it
(e.g. skip Policy Checker when Forensics already flags high tamper).

### Failure handling at node boundaries (CLAUDE.md §11: no silent swallow)

- **OCR failure** (Extractor): catch `OcrError`, append to `state["errors"]`,
  set `extracted_fields = None`, still proceed to Forensics (forensics doesn't
  need OCR text) but Policy Checker must see `extracted_fields is None` and
  short-circuit to `compliant=False, triggered_rules=["extraction_failed"]`
  without calling the proxy — nothing to check fields against.
- **Proxy 400 `injection_detected`**: the OCR text or a constructed message
  tripped the injection detector. Node catches the non-200 response, records
  `errors: [{"node": "extractor", "code": "injection_detected", ...}]`, sets
  the field to `None`, does NOT retry with modified content (that would be
  guardrail-bypass behavior, forbidden by CLAUDE.md §12).
- **Proxy 422 `schema_validation_failed`**: proxy already retried once
  internally (S4) before returning this — the node records the failure and
  treats the field as unavailable; it must not fabricate a fallback structured
  value.
- **Proxy 429 `rate_limit_exceeded`**: per D-019, the proxy gives no cached
  content — the *agent* is the caller and must own a fallback. For Phase 4's
  automated tests this simply means the node records `errors` and the graph
  completes with partial state (report still runs, noting "policy check
  unavailable: rate limit"). A cached-sample fallback for the demo path is a
  Phase 6/UI-facing concern, not required for the agent itself.
- **Any other non-200 / connection error** from `call_proxy`: never let an
  exception propagate uncaught out of a node (LangGraph would abort the whole
  run) — catch, log into `errors`, continue with `None` for that field so
  later nodes can make an explicit "evidence missing" decision instead of
  crashing.
- **Report Writer** always runs even with partial upstream state, and must
  state in the report text when evidence is missing rather than inventing it
  (ties directly to grounded hallucination scoring — inventing content not in
  `grounding_context` is exactly what `score_grounded` is meant to catch).

## 8. Test plan (matches spec.md Phase 4 test gate)

- `tests/agents/test_extractor.py` — OCR fixtures: 1-2 tiny synthetic receipt
  images (`tests/fixtures/receipts/genuine_1.jpg` + a plain-text-only image) run
  through `run_ocr`, mocked `call_proxy` returning a valid `receipt_fields`
  payload; assert schema shape and that OCR failure raises `OcrError` instead
  of returning `""`.
- `tests/agents/test_forensics.py` — genuine vs. tampered fixture pair
  (`tests/fixtures/receipts/genuine_1.jpg`, `tampered_1.jpg` — a copy with a
  pasted/recompressed region); assert `tamper_likelihood` differs directionally
  (tampered ≥ genuine ela_score) and an EXIF-stripped image yields
  `exif_consistent=None`, not `False`.
- `tests/agents/test_policy_checker.py` — policy rule fixtures: fields under
  limit / over limit / disallowed category / receipt too old / missing date;
  mocked `call_proxy` returning `policy_verdict`; assert `load_policy` parses
  the YAML in §5 correctly and the missing-date case doesn't silently pass.
- `tests/agents/test_report_writer.py` — grounding test: evidence bundle with a
  known fact (e.g. "total: 42.50") vs. a mocked LLM response that invents an
  unsupported figure; assert `report_guardrails["hallucination"]["score"] > 0`
  for the invented case using the real `score_grounded` (not mocked — this is
  the point of the test).
- `tests/agents/test_graph.py` — LangGraph integration test: full pipeline on
  one sample receipt with all `call_proxy` calls mocked to return valid
  payloads; assert final state has all fields populated and node order is
  Extractor→Forensics→Policy Checker→Report Writer. A second case mocks one
  node's `call_proxy` to return a 429, asserts the graph still completes with
  `errors` populated instead of raising.
- `tests/agents/test_no_direct_provider_calls.py` — static enforcement test:
  read every `agents/*.py` file's source text and assert none contains
  `import groq`, `from groq`, `import google.generativeai`, or
  `from google.generativeai` (simple substring/AST import-name check, no need
  for a linter dependency — stdlib `ast.parse` + walk `ImportFrom`/`Import`
  nodes is enough).

## 9. Open questions / needs a decision.md entry

1. **`ForensicsResult` schema placement** — `agents/forensics.py` (recommended,
   §4) vs. `proxy/schemas.py`/`SCHEMA_REGISTRY`. Needs a dated decision before
   or during Phase 4 execution.
2. **OD-006 (missing extracted fields)** — this plan assumes the existing
   `ReceiptFields` defaults (`None`/`[]`) are the answer, since that's what's
   already shipped in `proxy/schemas.py`. Should be formally confirmed/closed
   as a decision rather than left implicit once Phase 4 starts.
3. **OD-007 (confidence calculation)** — not resolved by this plan. Report
   Writer's output currently has no numeric "confidence" field distinct from
   the hallucination score; Phase 4 execution needs a decision on whether
   confidence is proxy-derived, agent-composed, or deferred to Phase 6.
4. **Report Writer schema-vs-free-text** (§6) — this plan picks free text; flag
   for confirmation since a structured `ReportOutput` schema is a legitimate
   alternative Phase 6 might end up wanting.
5. **Rate-limit fallback content for the agent pipeline** (analogous to D-019's
   playground fallback) — not designed here; likely a Phase 6 UI concern, but
   worth an explicit decision on whether Phase 4 needs any pipeline-level cache
   at all versus just surfacing `errors`.
