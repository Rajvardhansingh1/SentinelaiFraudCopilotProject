# Decision Log — SentinelAI + Fraud Copilot

This file records durable architecture/design decisions and resolved conflicts. It is not a progress journal.

## Decision Statuses

- **Accepted** — implementation should follow it.
- **Open** — requires a future decision.
- **Superseded** — replaced by a later decision.
- **Rejected** — considered and explicitly not selected.

---

## D-001 — Two-layer architecture

**Date:** 2026-09-18  
**Status:** Accepted

**Context:** The project combines reusable AI safety infrastructure with a concrete fraud application.

**Decision:** Keep two layers:
- SentinelAI platform layer
- Fraud Copilot application layer

**Rationale:** SentinelAI must remain domain-agnostic and reusable while Fraud Copilot demonstrates a real consumer of the platform.

**Consequence:** Fraud-specific logic must not leak into SentinelAI.

---

## D-002 — SentinelAI is the mandatory LLM boundary

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Every Fraud Copilot LLM call routes through SentinelAI. Agents must not call Groq/Gemini directly.

**Rationale:** This is a core architectural invariant and the primary demonstration of reusable guardrail infrastructure.

**Consequence:** Provider SDKs belong behind the proxy/provider abstraction.

---

## D-003 — Local OCR and image forensics bypass SentinelAI

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** PaddleOCR/RapidOCR and OpenCV forensics execute locally.

**Rationale:** They are not LLM calls and therefore do not require the LLM proxy.

**Consequence:** OCR output becomes untrusted input to SentinelAI when it enters an LLM call.

---

## D-004 — Human approval is mandatory

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** The system never auto-approves or auto-rejects a fraud claim.

**Rationale:** The application is a copilot, not an autonomous adjudication system.

**Consequence:** UI must clearly separate model verdict/evidence from the human final action.

---

## D-005 — Streamlit is the baseline frontend

**Date:** 2026-09-18  
**Status:** Superseded by D-034 (2026-09-19)

**Decision:** Use Streamlit for playground, upload/review UI, and evaluation dashboard.

**Alternative:** React + Tailwind + Recharts.

**Resolution:** React is a possible later polish upgrade but is not required for baseline shipment.

---

## D-006 — Groq + Gemini provider strategy

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Groq is the primary candidate and Gemini is the backup/alternate provider.

**Consequence:** Provider abstraction must prevent application code from depending on a specific provider.

---

## D-007 — Synthetic data only

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Build the evaluation dataset with synthetic/lightly templated receipts and intentionally tampered variants.

**Rationale:** Avoid real company/client data and IP conflicts.

---

## D-008 — Chroma for grounding

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Use Chroma for grounding retrieval in the baseline.

**Consequence:** Grounding interfaces should be isolated so the vector store can be replaced later.

---

## D-009 — SQLite baseline, Supabase optional

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Use SQLite initially; move to Supabase/Postgres only if the single-file approach becomes insufficient.

---

## D-010 — Phase order

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Build in this order:
1. Core proxy
2. Evaluation layer
3. Red-team playground
4. Fraud agents
5. Synthetic dataset
6. Review UI/dashboard
7. Deployment/hardening

**Rationale:** The proxy is the dependency everything else needs. Agents and dataset can later proceed in parallel after proxy stability.

---

## D-011 — Project memory is split across four roles

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:**
- `spec.md` = what must be built
- `decision.md` = why durable choices were made
- `progress_log.md` = what happened chronologically
- `state.md` = where the project currently is

**Rationale:** Avoid turning one large context file into an unmaintainable project memory.

---

## D-012 — Agent instructions stay short

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** `CLAUDE.md` contains only persistent operating rules, workflow, file responsibilities, and skill routing. Detailed requirements belong in `spec.md`.

**Rationale:** The agent should load a concise control document and retrieve detailed project context only when needed.

---

## D-013 — Hallucination scoring has two modes

**Date:** 2026-09-18  
**Status:** Accepted

**Decision:** Implement:
1. grounded claim-level scoring against retrieved context;
2. ungrounded self-consistency scoring when grounding is unavailable.

**Open implementation detail:** Exact claim decomposition method, NLI model, thresholds, and self-consistency aggregation remain to be specified before implementation.

---

## D-014 — OCR engine: RapidOCR

**Date:** 2026-09-18
**Status:** Accepted

**Context:** Spec offers PaddleOCR/PaddlePaddle or RapidOCR (onnxruntime) as OCR options for the Extractor agent.

**Decision:** Use `rapidocr-onnxruntime`.

**Rationale:** PaddlePaddle has known install friction on Windows; RapidOCR is onnxruntime-based, lighter, and equally viable per spec.

**Consequence:** `requirements.txt` lists `rapidocr-onnxruntime` instead of `paddleocr`/`paddlepaddle`.

---

## D-015 — SentinelAI HTTP contract (resolves OD-001)

**Date:** 2026-09-18
**Status:** Accepted

**Decision:** Single endpoint `POST /v1/generate`.

Request:
```json
{
  "session_id": "str",
  "operation": "extract|policy_check|report|playground",
  "messages": [{"role": "system|user|assistant", "content": "str"}],
  "schema_name": "str | null",
  "grounding_context": "str | null"
}
```

Response (200):
```json
{
  "output": "validated structured object or text",
  "guardrails": {
    "injection": {"flagged": false, "matched_patterns": []},
    "pii": {"found": false, "redacted": false, "types": []},
    "schema_valid": true,
    "retried": false,
    "hallucination": {"score": 0.0, "mode": "grounded|ungrounded"}
  },
  "usage": {
    "provider": "groq|gemini|cache",
    "model": "str",
    "tokens_in": 0,
    "tokens_out": 0,
    "latency_ms": 0,
    "cost_estimate_usd": 0.0
  },
  "error": null
}
```

Blocked/error envelope (any status): `error: {code, message}`, `output: null`. Injection block → 400, code `injection_detected`. Schema validation failure after retry → 422, code `schema_validation_failed`. Rate limit exceeded → 429, code `rate_limit_exceeded`, `output: null`.

**Amended 2026-09-19 by D-019:** the "cached sample output on 429" behavior originally described here is a caller-side responsibility, not a proxy-side one. See D-019.

`schema_name` selects the Pydantic model from `proxy/schemas.py` used for S4 validation; `null` means free-text/no structured validation.

**Rationale:** One contract for all callers (agents + playground) keeps SentinelAI domain-agnostic; `operation` is metadata only, not branching logic baked into the platform layer.

**Consequence:** `spec.md` S1 updated to reference this contract. Resolves OD-001.

---

## D-016 — PII scanner: regex-only baseline, Presidio deferred

**Date:** 2026-09-18
**Status:** Accepted

**Context:** Spec S3 requires Presidio for structured PII plus regex for secrets. Presidio requires a spaCy model download (~40MB+) and adds notable install/runtime weight.

**Decision:** Ship Phase 1 with a regex-only scanner (emails, phone numbers, card-like numbers, API-key-shaped strings). Wire `presidio-analyzer`/`presidio-anonymizer` behind the same `pii_scanner.check_pii()` interface as a follow-up before Phase 1 is marked release-ready, tracked as OD-010.

**Rationale:** Unblocks proxy contract, injection detection, schema validation, and rate limiting now; Presidio integration is additive and isolated to one module.

**Consequence:** `spec.md` S3 acceptance is partially met until OD-010 closes. Phase 1 completion protocol must not be signed off until Presidio is wired or OD-010 is explicitly re-scoped.

**Update 2026-09-19:** `pii_scanner.check_pii()` now merges Presidio NER results with the regex baseline when `presidio-analyzer` is installed, and degrades to regex-only otherwise (lazy import, cached probe). OD-010 closed — package/model install remains an environment/deployment step, not a code gap.

---

## D-017 — Hallucination scoring: lexical-overlap heuristic (partial OD-004)

**Date:** 2026-09-19
**Status:** Accepted (MVP baseline, ceiling documented)

**Context:** OD-004 requires claim decomposition, an NLI model, thresholds, and self-consistency aggregation, none of which were previously chosen. A real NLI model (transformers/cross-encoder) is a heavy dependency for this session's scope.

**Decision:**
- Claim decomposition: sentence split on `. ! ?`.
- Grounded mode: per-claim token-overlap ratio against `grounding_context`; ratio ≥ 0.5 → supported, otherwise unsupported. No contradiction class yet (MVP has no negation/NLI detection). Score = unsupported ÷ total claims.
- Ungrounded mode: pairwise Jaccard token-overlap across N sampled generations as a self-consistency proxy; score = 1 − mean pairwise similarity.

**ponytail ceiling:** lexical overlap is a heuristic stand-in for real entailment — no semantic understanding, vulnerable to paraphrase/synonym false-unsupported. Upgrade path: swap the per-claim comparator in `hallucination_scorer.py` for a cross-encoder NLI model (e.g. `cross-encoder/nli-deberta-v3-base` via `sentence-transformers`) without changing the module's public interface.

**Consequence:** `spec.md` S8/S9 acceptance is met at MVP fidelity. Real metrics from Phase 5 evaluation will reflect heuristic-scorer accuracy, not a state-of-the-art NLI model — must not be presented as more rigorous than it is.

---

## D-018 — Grounding store: pluggable, in-memory TF-IDF default

**Date:** 2026-09-19
**Status:** Accepted

**Context:** Spec (D-008) names Chroma for grounding. The default `chromadb` embedding function pulls in `onnxruntime`, a heavy download disproportionate to this session's scope for wiring the interface.

**Decision:** `proxy/eval/grounding.py` defines a `GroundingStore` protocol (`add`, `query`). Default implementation is `InMemoryTFIDFStore` (pure-python bag-of-words + cosine similarity, deterministic, no external deps). `ChromaStore` (wraps `chromadb.PersistentClient`, persisted to `settings.chroma_persist_dir`) implements the same protocol and is a drop-in swap.

**Rationale:** Unblocks S10 now with deterministic, dependency-light retrieval; keeps the swap to real Chroma a one-line change (`get_grounding_store()`) instead of a rewrite.

**Consequence:** Until `ChromaStore` is selected in `get_grounding_store()`, grounding is process-local and non-persistent (acceptable for the MVP demo; Phase 7 deployment should confirm persistence needs before going live). Tracked as OD-011.

---

## D-019 — Cached-sample fallback on rate-limit is caller-side, not proxy-side (narrows D-015)

**Date:** 2026-09-19
**Status:** Accepted

**Context:** Phase 3 planning (PHASE3_PLAN.md) found `proxy/main.py`'s 429 branch returns `output: null`, not the cached sample D-015's original prose implied. Serving a cached sample server-side requires the proxy to know per-operation "what a good cached answer looks like," which is domain/UI knowledge (SentinelAI is domain-agnostic, D-001) — that knowledge belongs in the caller (Streamlit playground, Fraud Copilot agents), not the platform layer.

**Decision:** SentinelAI's 429 response stays minimal (`output: null`, `error.code: "rate_limit_exceeded"`) — it is a signal, not a content provider. Each caller (red-team playground, fraud pipeline) owns its own cached/sample fallback content and displays it client-side when it receives a 429.

**Rationale:** Keeps the proxy domain-agnostic and reusable (D-001); avoids the proxy needing a cache-keying scheme it has no way to do well without caller context.

**Consequence:** D-015's response contract description is amended (cached-output language removed from the 429 case). Phase 3's playground implements its own local sample-response fallback (`frontend/data/sample_attacks.py`), per PHASE3_PLAN.md §5. Future callers (Fraud Copilot sample-receipt fast path, Phase 4) follow the same pattern.

---

## D-020 — Rate-limit default: 8 calls per session (resolves OD-005)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `RATE_LIMIT_PER_SESSION` / `settings.rate_limit_per_session` default is 8, matching the original spec's example ("8 live calls") and already the shipped default in `.env.example` and `proxy/config.py` since Phase 1. The UI's "7/10" example in the original spec section 10 is illustrative copy, not a literal alternate value.

**Rationale:** No functional reason to diverge from the spec's own stated example; avoids inventing a second number.

**Consequence:** Phase 3's quota badge displays against this value. Deployment (Phase 7) may retune it per real free-tier quota observed in practice — that would be a new dated decision, not silent drift.

---

# Open Decisions

## OD-001 — Exact SentinelAI HTTP contract
**Status:** Resolved by D-015.

## OD-002 — Injection detector classifier
**Status:** Open

Need to select the lightweight classifier approach and define whether pattern detection alone can block or whether both signals are required.

## OD-003 — PII response action
**Status:** Open

Need to decide exact behavior when response PII/secrets are detected: redact, block, retry, or return a structured safety failure.

## OD-004 — Hallucination scorer implementation
**Status:** Open

Need to define:
- claim extraction mechanism
- NLI model/provider
- thresholds
- unsupported/contradicted handling
- no-claim edge case
- self-consistency aggregation

## OD-005 — Rate-limit exact value
**Status:** Resolved by D-020.

## OD-006 — Missing extracted fields
**Status:** Resolved by D-022.

## OD-007 — Confidence calculation
**Status:** Resolved by D-026.

## OD-008 — Exact deployment provider
**Status:** Resolved by D-030.

## OD-009 — Streamlit persistence/log refresh behavior
**Status:** Resolved by D-028.

## OD-010 — Presidio integration
**Status:** Resolved 2026-09-19. See D-016 update.

## OD-011 — Switch grounding store to real Chroma
**Status:** Resolved by D-029.

## OD-012 — ForensicsResult schema placement
**Status:** Resolved by D-021.

`PHASE4_PLAN.md` proposes a tamper-likelihood output model for the Forensics agent. Since Forensics has no LLM call (D-003), decide whether this Pydantic model lives in `proxy/schemas.py`/`SCHEMA_REGISTRY` (consistent with `ReceiptFields`/`PolicyVerdict`) or stays agents-local since it never goes through `/v1/generate`. Plan recommends agents-local.

## OD-013 — Report-Writer output: free text vs structured schema
**Status:** Resolved by D-023.

## OD-014 — Pipeline-level rate-limit fallback scope
**Status:** Resolved by D-024.

## OD-015 — Human review-decision storage schema
**Status:** Resolved by D-027.

## OD-016 — Missing-field representation and confidence calculation (reaffirms OD-006/OD-007)
**Status:** OD-006 resolved by D-022. OD-007 (confidence calculation source) remains open — Phase 4 ships without a numeric confidence field (Report Writer surfaces `hallucination.score` only); needed before Phase 6's review screen displays a "confidence" value.

## D-021 — ForensicsResult lives agents-local (resolves OD-012)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `ForensicsResult` Pydantic model defined in `agents/forensics.py`, not added to `proxy/schemas.py`/`SCHEMA_REGISTRY`.

**Rationale:** Forensics never calls the proxy (D-003) so has no `schema_name` validation use; adding it to SentinelAI's registry would blur domain-agnosticism (D-001) with a Fraud-Copilot-specific concept.

---

## D-022 — Missing extracted fields: existing Pydantic defaults (resolves OD-006)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `vendor`/`date`/`total` default to `None`, `line_items` defaults to `[]` — the behavior `ReceiptFields` (`proxy/schemas.py`) already shipped in Phase 1. Formalized as the answer rather than left implicit.

**Rationale:** No reason to invent a second representation; this was already live and Phase 4 depends on it as-is.

**Consequence:** Downstream consumers (Policy Checker, Report Writer, later Phase 6 UI) must explicitly handle `None`/`[]` as "missing," never treat them as valid zero-equivalent values.

---

## D-023 — Report Writer output is free text (resolves OD-013)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** Report Writer calls `/v1/generate` with `schema_name=None`; output is a human-readable audit narrative, not a new structured schema.

**Rationale:** Spec's own description ("structured/human-readable audit report") is read by a human reviewer (Phase 6), not consumed downstream by code; a rigid schema would fight that purpose with no current consumer requiring one (YAGNI).

**Consequence:** If Phase 6 later needs distinct structured fields (e.g. a separate summary line), add a `ReportOutput` schema then — not now.

---

## D-024 — No pipeline-level rate-limit cache in Phase 4 (resolves OD-014)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** When a mid-pipeline `/v1/generate` call returns 429, the LangGraph node records it in `state["errors"]` and continues with `None` for that field. No cached/sample fallback content is built into the agent layer.

**Rationale:** A cached fallback needs UI/demo context (what to show a reviewer) that agents don't have — same reasoning as D-019 (cache ownership is caller-side, domain-agnostic proxy stays minimal). Phase 6 owns any user-facing fallback.

**Consequence:** Phase 4's graph is allowed to complete with partial state under rate-limit pressure; Phase 6 decides how to present that partial state to a reviewer.

---

## OD-017 — Forensics ELA thresholds need retuning against real dataset scale
**Status:** Superseded by D-025 → successor item OD-018 (ELA signal is weak on this dataset, not just mis-thresholded).

## D-025 — ELA: max-block-residual instead of whole-image mean (partial OD-017)

**Date:** 2026-09-19
**Status:** Accepted, with a documented open limitation

**Context:** OD-017 found Phase 4's whole-image-mean ELA score couldn't separate genuine from tampered synthetic receipts — a tampered region is ~1% of the image, so its recompression discontinuity is drowned by uniform background noise in a global mean.

**Decision:** `agents/forensics.py::_ela_score()` now splits the diff into `ELA_BLOCK_SIZE=16` blocks and returns the *max* block-mean residual, not the whole-image mean. This is a real methodology improvement (isolates a localized edit) and is kept regardless of the finding below.

**Honest finding (not resolved, not hidden):** re-measuring against the full Phase 5 dataset (45 genuine / 45 tampered) showed even max-block ELA barely separates the two classes on this specific synthetic dataset (genuine block-max mean ≈0.0087, tampered ≈0.0088, heavy overlap — tampered bottom-5 scores are *below* genuine's own median). Root cause: the synthetic renders are flat white-background/black-text images, so ordinary JPEG block artifacts around text edges are comparable in magnitude to the deliberately-introduced tamper patch's artifacts — there isn't much "quiet" background for the tamper signal to stand out against, unlike a real photographed/scanned receipt with natural texture and noise. `ELA_HIGH_THRESHOLD=0.0095`/`ELA_MEDIUM_THRESHOLD=0.0085` are set from this dataset's actual distribution (not guessed), so `scripts/run_eval_suite.py` will report real, measured (mediocre) tamper-detection precision/recall rather than a fabricated-looking clean number — per CLAUDE.md's "measure, don't claim."

**Consequence:** OD-017 is downgraded from "thresholds are obviously wrong" (fixed) to "ELA has a real, documented, dataset-specific limitation" (open — see OD-018). This is a legitimate finding to report in the final evaluation (Phase 7), not a bug to silently paper over with a threshold that fakes good numbers.

---

## OD-018 — ELA signal weak on flat synthetic receipts (successor to OD-017)
**Status:** Open

Real fix options, none applied here: (a) regenerate tampered samples with a stronger/more visible edit (e.g. overlaying a differently-colored or higher-contrast patch instead of white-fill, so the recompression boundary is more pronounced), (b) add texture/noise to the synthetic receipt backgrounds so they resemble scanned paper rather than flat renders, (c) accept EXIF signals as the primary tamper indicator for this dataset and treat ELA as a weak secondary signal, or (d) note in the final Phase 5/7 evaluation report that ELA's real-world effectiveness can't be fully validated against flat synthetic renders and would need photographed/scanned test images to properly evaluate. Needs a decision before Phase 7's final evaluation report presents tamper-detection numbers.

## D-026 — Confidence = 1 − hallucination score (resolves OD-007)

**Date:** 2026-09-19
**Status:** Accepted (MVP, ceiling documented)

**Decision:** The Review Screen's displayed "confidence" is computed as `1 - report_guardrails["hallucination"]["score"]` — the complement of the Report Writer's grounded hallucination score (D-017).

**Rationale:** No separate model-native confidence signal exists anywhere in the pipeline; inventing a new LLM call or heuristic purely to produce a "confidence" number would be speculative. The hallucination score already measures how well the report is grounded in the collected evidence, which is a reasonable proxy for "how much to trust this report" without adding new machinery (YAGNI).

**ponytail ceiling:** this is not a calibrated confidence interval or model-native probability — it inherits D-017's lexical-overlap heuristic ceiling. Must be labeled in the UI as derived from grounding fidelity, not a true confidence score, so it isn't overclaimed (CLAUDE.md §10).

**Consequence:** No new proxy/agent code needed — `report_guardrails` already carries this value. Review screen just does the subtraction and labels it honestly.

---

## D-027 — Review decisions stored in a new frontend-owned table (resolves review-decision storage open item)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `ReviewDecision` lives in `frontend/db/models.py`, its own `DeclarativeBase`, using the same SQLite file as `proxy/db/models.py`'s `CallLog` (one `database_url`, two independent Base/metadata objects, two `create_all()` calls) via `frontend/db/session.py`.

**Rationale:** Keeps SentinelAI (`proxy/db/`) domain-agnostic — a human's approve/reject decision on a fraud claim is Fraud-Copilot-application data, not proxy telemetry (D-001). A separate physical database file was considered and rejected as unnecessary operational complexity for a single-file SQLite demo (D-009).

**Consequence:** `frontend/db/session.py::init_db()` must be called alongside `proxy/db/session.py::init_db()` at app startup. Schema: `id, session_id, receipt_ref, system_verdict, confidence, hallucination_pct, human_decision, reviewer_notes, decided_at`.

---

## D-028 — Dashboard refresh: manual button (resolves OD-009)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `eval_dashboard.py` uses a manual `st.button("Refresh")` to re-run `fetch_calls()`. No polling loop, no new autorefresh dependency.

**Rationale:** This is a demo/reviewer tool, not a live ops screen; Streamlit already reruns the script on any widget interaction (filter changes double as a refresh), and a polling loop is a known anti-pattern that blocks the session thread. Matches PHASE6_PLAN.md's own non-binding recommendation.

**Consequence:** Dashboard data can be stale between interactions — acceptable for this use case.

---

## D-029 — Chroma grounding store implemented and made the default when available (resolves OD-011)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** `proxy/eval/grounding.py::ChromaStore` implements `GroundingStore` via `chromadb.PersistentClient(path=settings.chroma_persist_dir)`. `get_grounding_store()` now tries `ChromaStore` first (lazy `import chromadb`, matching `provider.py`'s Groq/Gemini pattern) and falls back to `InMemoryTFIDFStore` only if that import/construction fails.

**Rationale:** D-018's `InMemoryTFIDFStore` was always meant as a dependency-light placeholder; `chromadb` installed cleanly in this session (no unreasonable onnxruntime cost), so there's no remaining reason to defer the swap spec.md's Phase 7 baseline requires ("Chroma: embedded/persisted").

**Consequence:** Grounding now persists to disk (`CHROMA_PERSIST_DIR`) across proxy restarts in any environment where `chromadb` is installed — including the Render deployment (`requirements.txt` already lists `chromadb`). Tests cover both `ChromaStore` directly (add/query, persistence across a reopened client) and `get_grounding_store()`'s selection behavior.

---

## D-030 — Deployment target: Render (resolves OD-008)

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** SentinelAI's FastAPI proxy deploys to Render (`deploy/render.yaml`), not Railway.

**Rationale:** Render's `render.yaml` is declarative and matches the free-tier "sleeps after ~15min idle, ~20-30s cold start" behavior the original spec explicitly designs the cold-start UX around (spec.md/original spec §9-10); no functional reason favored Railway. Original spec allowed either.

**Consequence:** `deploy/render.yaml` is the deployment config. Render's free-tier persistent-disk availability should be confirmed at actual deploy time — if unavailable, SQLite/Chroma persistence would need Supabase sooner than D-009's "if it outgrows a single file" implies. Flagged, not blocking, since this repo ships deployment config, not a live deploy in this session.

---

## D-031 — Provider/proxy-client crash guards (bug fixes, not a design decision)

**Date:** 2026-09-19
**Status:** Fixed

Real bugs found via the user's own live run (not synthetic tests), all violating CLAUDE.md §11 ("failures must be explicit," never crash a caller uncaught):

1. `proxy/provider.py`: `GroqProvider`/`GeminiProvider` only wrapped the API call in `try/except ProviderError`, not the `from groq import Groq` / `import google.generativeai` import itself. A missing package (`groq` wasn't installed in the running venv) raised an uncaught `ModuleNotFoundError` that skipped `FallbackProvider`'s except clause entirely, 500ing the whole `/v1/generate` endpoint with a plain-text (non-JSON) body. Fixed: import moved inside the try block in both providers.
2. `agents/proxy_client.py::call_proxy()`: `resp.json()` was outside the try/except, so a non-JSON response body (exactly what bug #1 produces) raised an uncaught `requests.exceptions.JSONDecodeError` in whichever LangGraph node called it — this is the traceback the user hit in `report_writer.py`. Fixed: `.json()` moved inside the try block (it's already a `RequestException` subclass, so one except clause covers both connection failures and bad JSON).
3. `frontend/lib/proxy_client.py::call_generate()`: same class of bug, no try/except at all — a proxy connection failure or bad JSON would crash the Streamlit playground page. Fixed: now returns a synthetic `503`/`proxy_unreachable` error envelope instead of raising, matching the shape `redteam_playground.handle_response()` already expects.

**Why recorded here:** not a design choice, but the pattern (wrap the whole external call including any lazy import, never let a raw `resp.json()` escape uncaught) should hold for any future provider/HTTP-client code added to this repo.

---

## D-032 — Report Writer must send evidence in the prompt, not just as grounding_context (bug fix)

**Date:** 2026-09-19
**Status:** Fixed

**Found via:** a real end-to-end run with the actual Groq API (not mocked tests — this bug was invisible to the existing test suite because tests mock `call_proxy` and never exercise real LLM prompt-following behavior).

**Bug:** `agents/report_writer.py::write_report()` passed the evidence bundle only via `grounding_context`, which `proxy/main.py` uses exclusively for post-hoc hallucination scoring (`score_grounded`) — it is never injected into the actual prompt sent to the LLM. The user message just said "write the audit report using only the evidence provided" with no evidence attached, so every real report call correctly refused: *"unable to generate the audit report because no supporting evidence was provided."*

**Fix:** the evidence JSON is now embedded directly in the user message content (`f"Evidence:\n{evidence_bundle}\n\nWrite the audit report using only the evidence above."`), in addition to still being passed as `grounding_context` for scoring. Verified with a real Groq call producing a correctly grounded report citing actual extracted fields/forensics/policy data.

**Consequence:** confirms `grounding_context` and "what's actually in the prompt" are two separate concerns callers must handle themselves — the proxy does not auto-inject grounding context into the LLM call, only scores against it afterward. Worth keeping in mind for any future caller using `grounding_context`.

---

## D-033 — Guardrails scan only non-system messages (bug fix, real production-blocking bug)

**Date:** 2026-09-19
**Status:** Fixed

**Found via:** real Playwright browser testing against the live app — every single Red-Team Playground request, including a completely benign "What is the capital of France?", was blocked with `role_override`.

**Root cause:** `proxy/main.py`'s `check_injection`/`check_pii` ran against `inbound_text = "\n".join(m.content for m in req.messages)` — the *entire* message list, including the system prompt. The playground's own system prompt (`frontend/lib/proxy_client.py::SYSTEM_PROMPT`) contains anti-jailbreak instruction text like "...or act as a different persona..." — exactly the phrasing `proxy/redteam/attack_library.py`'s `role_override` pattern (`you are now|act as|pretend...`) is designed to catch. The detector was catching the caller's own defensive instructions, not an attack.

**Fix:** `proxy/main.py` now scans only non-`system`-role message content (`untrusted_text`) for injection/PII. The system prompt is caller-authored and trusted (same trust boundary as D-001/D-002 — agents/callers are trusted, their inbound free text and OCR output are not). `MAX_INPUT_CHARS` size check still applies to the full message list (oversized-input protection is unrelated to trust).

**Consequence:** this was a release-blocking bug — the entire red-team playground demo was non-functional for any real prompt before this fix, since the hard-scoped system prompt (a deliberate safety feature) was guaranteed to always self-trigger the detector. Any future caller writing its own system prompt with safety/anti-jailbreak language must be aware only non-system content is scanned — this is the correct trust model, not a workaround.

---

## D-034 — Frontend rewrite: Streamlit → React/Next.js (supersedes D-005)

**Date:** 2026-09-19
**Status:** Accepted, execution not started

**Context:** Real Playwright/manual testing against the live Streamlit app surfaced UX gaps a Streamlit polish pass can't fully close: raw dict/JSON dumps for evidence (`st.write(dict)`), no way for a visitor to test their own prompt against the playground with a reasoning explanation for why it failed/passed, report-first-then-reasoning layout not achievable cleanly in Streamlit's top-down script model, and an overall ceiling of "reads as a Python data app" rather than a product-grade UI. User explicitly chose a full rewrite over further Streamlit polish, accepting the cost (full frontend rewrite, new build pipeline, every existing Streamlit/`AppTest`-based test — 15 tests across `test_playground_ui.py`, `test_review_ui.py` — retired and replaced, an API auth/CORS layer added to the proxy since a separately-hosted React app is a new origin).

**Decision:** New frontend built in React + Next.js. `proxy/main.py` gains CORS restricted to the frontend's origin(s) (dev + prod) as part of this work — required regardless of framework choice once frontend and backend are different origins/ports, which they already are today (Streamlit talks to the proxy over HTTP too) but becomes a real cross-origin browser concern with a React SPA.

**Consequence:** `frontend/` (Streamlit) is retired once the React app reaches parity; `PHASE3_PLAN.md`/`PHASE6_PLAN.md`'s Streamlit-specific decisions (D-019 cached-fallback pattern, D-026/027/028) carry over conceptually (same behavior, different implementation) but their Streamlit-specific code does not. Scoped and planned before execution, not built blind — see progress_log.md for the planning subagent's output once it lands.

---

## D-035 — Fraud Copilot gets its own HTTP API (`agents/api.py`), separate from SentinelAI's proxy

**Date:** 2026-09-19
**Status:** Accepted

**Context:** `REACT_FRONTEND_PLAN.md` flagged that a Node.js React app can't in-process-import Python (`agents/graph.py`, `frontend/db` ORM) the way Streamlit did (`frontend/lib/pipeline_client.py`). Three new endpoints are needed: run the pipeline on a receipt, record a human review decision, list call logs for the dashboard.

**Decision:** These endpoints live in a new `agents/api.py` FastAPI app — a second, separate service from `proxy/main.py`, not routes bolted onto the SentinelAI proxy. This matches the original two-layer architecture (D-001): SentinelAI stays domain-agnostic; the Fraud Copilot application layer gets its own HTTP surface. `agents/api.py` calls SentinelAI internally the same way it always has (`agents/proxy_client.py::call_proxy()` → `/v1/generate`), it does not merge the two services.

**Consequence:** Three services now exist for local dev / deployment: SentinelAI proxy (`proxy/main.py`, port 8000), Fraud Copilot API (`agents/api.py`, new port e.g. 8001), and the frontend (React, or Streamlit until retired). `ReviewDecision` moves ownership from `frontend/db/models.py` to a Fraud-Copilot-owned DB module (e.g. `agents/db/models.py`) when `agents/api.py` is built — `frontend/db/` was always a compromise made because Streamlit could only import Python in-process; that compromise goes away once there's a real API layer. `deploy/render.yaml` needs a second service block for this — Phase 7's deployment plan is not yet updated for this, flagged as a follow-up, not done silently.

---

## D-036 — Hosting split: Vercel for the React frontend, Render for both Python services

**Date:** 2026-09-19
**Status:** Accepted

**Decision:** The Next.js app deploys to Vercel (natural fit for Next.js, free tier, no cold-start problem unlike Render's free tier). `proxy/main.py` and the new `agents/api.py` both stay on Render (two Render web services instead of one).

**Rationale:** Fighting Vercel's platform to deploy Streamlit/FastAPI, or fighting Render to serve Next.js optimally, both work against the grain. Split by what each platform is actually good at.

**Consequence:** `deploy/huggingface_space/README.md` becomes obsolete once React replaces Streamlit (HF Spaces was specifically for the Streamlit app) — not deleted yet, flagged for removal once the rewrite ships. `PHASE7_PLAN.md` needs a revision pass for this new topology — tracked, not done in this entry.

---

## OD-019 — agents/api.py execution-time details
**Status:** Partially resolved — endpoint shapes finalized (see below). Weakness-coach heuristic-vs-LLM and prod `ALLOWED_ORIGINS` remain open (both deferred by design, not blockers).

`agents/api.py` built 2026-09-19: `POST /v1/analyze-receipt` (multipart: `session_id`, `image` file; always 200, pipeline failures surface in `errors`), `POST /v1/review-decisions` (JSON, D-027's `ReviewDecision` fields, now backed by a new `agents/db/models.py` — separate `DeclarativeBase` from both `proxy/db` and the still-live `frontend/db`, same physical SQLite file), `GET /v1/calls?limit=N` (raw `CallLog` rows, reuses `proxy.db` directly, no duplicated model). `proxy/config.py` gained `agents_api_port: int = 8001`. Note: `frontend/db/models.py`'s `ReviewDecision` is intentionally duplicated (not migrated) during the Streamlit→React window — Streamlit keeps writing to its own copy until retirement.

## D-037 — Surface the SentinelAI/Fraud-Copilot connection via the adversarial sample receipt

**Date:** 2026-09-19
**Status:** Accepted

**Context:** User feedback: the platform (SentinelAI, Red-Team Playground) and the application (Fraud Copilot, Review Receipt) read as two separate features rather than one integrated system, even though they were architecturally connected from Phase 5 onward — OCR'd receipt text flows through the same injection detector the playground exercises, and `data/synthetic_receipts/adversarial/adversarial_001.jpg` was built specifically to demonstrate this (hidden injection payload in the image, per the original spec's "flagship demo" framing, section 10). The connection existed but was never surfaced in any UI.

**Decision:** Add the adversarial sample as a 3rd fast-path option on the Review Receipt page (both the still-live Streamlit app and the new React rewrite). When it's analyzed and the proxy's injection detector catches the OCR'd payload, the UI explicitly names the connection — "the same engine protecting the Red-Team Playground" — rather than showing a generic error.

**Rationale:** Makes an already-real architectural connection visible instead of adding a new fake one. No new detection logic, no new backend behavior — pure UI surfacing of existing behavior.

**Consequence:** `frontend/components/review_screen.py`'s `SAMPLE_RECEIPTS` gains a 3rd entry. React's `lib/sample-receipts.ts` gains the same. Both should render a distinct callout when this sample's analysis surfaces an injection-detector catch during extraction.

---

## D-038 — Streamlit frontend retired (executes D-034's stated consequence)

**Date:** 2026-09-19
**Status:** Accepted, soft retirement

**Decision:** `frontend/` (Streamlit) is retired — user confirmed. `web/` (Next.js) is now the active/recommended frontend. `frontend/app.py` now shows a retirement banner if run. Code is kept on disk, not deleted (no git repo in this project as a safety net for a hard delete — a soft retirement is the reversible choice). No tests were removed; `test_playground_ui.py`/`test_review_ui.py`/`test_playground_quota.py` still pass and still provide real regression coverage on `frontend/` if anyone needs it, at no cost.

**Consequence:** README.md updated with `web/` run instructions as primary. Deployment plans (`PHASE7_PLAN.md`'s HF Spaces target, `deploy/huggingface_space/README.md`) are now obsolete — not deleted, flagged as stale. If a hard delete of `frontend/` is wanted later, that's a separate, explicit, git-backed action.

---

## D-039 — Playground: presets are editable, weakness-coaching only fires for the visitor's own prompt

**Date:** 2026-09-19
**Status:** Fixed (real UX gap, not a design decision)

**Found via:** user feedback after using the built React playground — prewritten attacks rendered as read-only preview text (no way to tweak one and test a variant), and `WeaknessCoach` fired for any non-blocked result, including an untouched preset — which is noise, since presets are expected/labeled attacks, not the visitor's own attempt.

**Fix:** `web/components/playground/attack-picker.tsx` now renders a single always-editable `Textarea`, prefilled with the selected preset's text (or empty for "(free text)"). `submit-panel.tsx` tracks `isOwnPrompt = isFreeText || promptText !== preset.prompt` and only passes weakness-coaching through when true. The "why was this blocked" pattern list (`matched_patterns`) still always renders on an actual block — that was already working, not part of this gap.

**Consequence:** a visitor can now start from a known attack and edit it into their own variant, and only gets coaching feedback once they've actually made it their own attempt.

---

## Decision-writing rule

When an open decision is resolved:
1. Add a dated decision entry.
2. Mark the OD item resolved.
3. Record rejected alternatives if they materially affected the implementation.
4. Update `spec.md` if the decision changes a requirement or contract.
