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

## D-040 — Fraud Copilot paused; active focus shifts to expanding SentinelAI alone

**Date:** 2026-09-23
**Status:** Accepted

**Context:** User request: build out SentinelAI (the platform layer) per `phase_dev_upgrade.md`'s phased plan (provider abstraction/BYOK, security engine, attack library, findings, dashboard, regression testing, CI/CD, agent security, gateway, monitoring, reports) without also carrying Fraud Copilot (the application layer) forward right now. Fraud Copilot resumes later.

**Decision:** Fraud Copilot functionality is removed from the active frontend/backend surface, code kept on disk (no deletion — same reversible posture as D-038's Streamlit retirement):
- `web/components/layout/sidebar-nav.tsx`: "Review" link removed.
- `web/app/review/page.tsx`: replaced with a paused notice; original implementation's supporting components (`web/components/review/**`) and `lib/api.ts`'s `analyzeReceipt`/`recordReviewDecision` are untouched, just unlinked.
- `web/tests/e2e/review.spec.ts`: `test.skip`, not deleted.
- `agents/api.py` (Fraud Copilot's own FastAPI service, port 8001) is no longer part of the documented/normal run flow (`README.md` updated). Code untouched.
- `GET /v1/calls` moved onto `proxy/main.py` itself (it only ever read `proxy.db.CallLog`, i.e. SentinelAI's own call log — never fraud-specific data) so the Eval Dashboard keeps working without `agents/api.py` running. `web/lib/api.ts::getCalls()` now calls `PROXY_BASE_URL` instead of `AGENTS_API_BASE_URL`.
- Eval Dashboard itself is kept — it always displayed SentinelAI proxy call/guardrail data (D-028), not Fraud Copilot data, so it's in-scope for a SentinelAI-only focus.

**Rationale:** D-001's two-layer architecture already separates SentinelAI (domain-agnostic) from Fraud Copilot (the application). Pausing Fraud Copilot is a scope-and-visibility change, not an architecture change — nothing about SentinelAI's design needed to move for this.

**Consequence:** `agents/`, `web/app/review/`, `web/components/review/` remain on disk, untested-by-CI-in-practice while paused (their existing tests still exist, just not exercised as part of the active workflow). `spec.md`'s original 7-phase Fraud Copilot content stays historically accurate (describes what was built) — not rewritten. Forward work (per `phase_dev_upgrade.md`) targets `proxy/` only. Resuming Fraud Copilot later means: restore the sidebar link, restore `web/app/review/page.tsx`'s original content, run `agents/api.py` again — no code reconstruction needed.

---

## D-041 — Provider abstraction + BYOK (phase_dev_upgrade.md Phase 2)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** `proxy/provider.py` already had a clean `Provider` Protocol and a decoupled security engine (`proxy/main.py` only ever called `.generate()`, no SDK imports at that layer) — Phase 2's interface/decoupling requirements were substantially already met. What was missing: per-call provider selection and BYOK (caller-supplied API key), and a registry so adding a provider doesn't touch `proxy/main.py`.

**Decision:**
- `GroqProvider`/`GeminiProvider` gain an `api_key: str | None = None` constructor param; `None` means "use the server's own key" (unchanged default behavior).
- New `MissingCredentialsError(ProviderError)` raised inside `generate()` before any SDK import/network call when no key resolves (neither BYOK nor server config).
- New `PROVIDER_REGISTRY: dict[str, type[Provider]]` and `build_provider(name, api_key)` — the extension point for future providers.
- `GenerateRequest.provider_config: ProviderConfig | None` (`{provider, api_key}`) lets a caller pick one named, non-fallback provider with an optional BYOK key. Omitted (the default) preserves the exact pre-D-041 `FallbackProvider(GroqProvider(), GeminiProvider())` behavior — zero change for existing callers.
- `proxy/main.py::generate()` catches `MissingCredentialsError` specifically → 400 `provider_credentials_missing`, distinct from the existing 502 `provider_failed` (key present but rejected/timeout/etc).

**Rationale:** Minimal diff on top of an already-decoupled design (YAGNI — no need to redesign the interface itself). BYOK as an optional per-request override, not a new server mode, keeps the default path's behavior and tests untouched.

**Consequence:** `docs/PROVIDERS.md` documents the interface, selection, credential handling, error codes, and how to add a provider. 12 new tests (`tests/test_provider.py`, `tests/test_proxy.py`) cover valid config, missing/invalid credentials, timeout, normal inference, and credential non-exposure. Full suite: 137 passed, 3 skipped (unchanged skip count).

---

## D-042 — Security testing engine framework (phase_dev_upgrade.md Phase 3)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 3 asks for a reusable framework separating TEST DEFINITION -> EXECUTION -> EVALUATION -> FINDING -> EVIDENCE, an extensible plugin architecture (no attack type hardcoded into the core), and migration of the existing Sentinel tests into it without breaking them. "Finding" generation proper is explicitly Phase 5's job ("build the Findings subsystem on top of the existing security engine") — Phase 3 stops at a rich, self-contained `TestResult`.

**Decision:** New `proxy/engine/` package: `models.py` (`SecurityTest`, `RawExecution`, `TestResult`, `Severity`, `TestStatus` — the 5-state status enum required by Phase 4 is built in now, not bolted on later), `runner.py` (`run_test`/`run_suite`, never raises — a plugin bug becomes `TestStatus.ERROR`), `registry.py` (`register`/`all_tests`, the sole extension point). `proxy/engine/plugins/injection_tests.py` migrates the 4 existing playground sample attacks (`frontend/data/sample_attacks.py`, already regression-tested in `tests/test_sample_attacks.py`) to run against the real `check_injection()` detector — same prompts (imported, not retyped), same detector, now wrapped in the engine's pipeline.

**Rationale:** Matches the explicit separation the spec asks for while reusing everything that already worked (`check_injection`, the sample-attack list) rather than inventing new attack content — that's Phase 4's job.

**Consequence:** `docs/SECURITY_ENGINE.md` documents the pipeline and how to add a plugin. 8 new tests (`tests/test_security_engine.py`) cover the runner's error handling, registry accumulation, and a regression guard that the migrated injection tests still catch the same attacks the raw detector does. Full suite: 145 passed, 3 skipped (up from 137/3, zero regressions).

---

## D-043 — Attack library expansion + security-test UI (phase_dev_upgrade.md Phase 4)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 4 asks for 5 attack categories (prompt injection, jailbreak, system prompt extraction, sensitive information disclosure, unsafe output behavior), multiple test cases per category, deterministic evaluation where possible, severity by documented rule, reproducibility, regression tests, and a UI that visibly distinguishes PASS/FAIL/ERROR/NOT_RUN/INCONCLUSIVE — explicitly warning not to claim a model is secure just because tests pass.

**Decision:**
- 3 new `proxy/engine/plugins/*`: `jailbreak_tests.py` (3 cases), `system_prompt_extraction_tests.py` (4 cases, exercising `attack_library.py` patterns that had no prior test case), `sensitive_disclosure_tests.py` (4 cases, using `check_pii()` against simulated model output rather than the inbound detector).
- `unsafe_output_tests.py` (2 cases) has no real classifier to evaluate against — honestly reports `TestStatus.INCONCLUSIVE` always, with a `ponytail:` comment naming the upgrade path (a moderation/LLM-judge call inside `evaluate()`), rather than fabricating a PASS.
- `injection_tests.py` refactored to share a new `plugins/_common.py::injection_pattern_test()` helper with the two other pattern-based plugins (no behavior change, less duplication).
- Severity rubric documented in `docs/SECURITY_ENGINE.md` (CRITICAL/HIGH/MEDIUM/LOW by real-world impact in Fraud Copilot's context).
- New `POST /v1/security-tests/run` (`proxy/main.py`) runs the full registered suite (all local/deterministic, safe synchronously) and returns serialized `TestResult`s.
- New `web/app/security/page.tsx` + `components/security/status-badge.tsx`: table of every result, status badge mapped 1:1 across the 5 `Badge` component variants (`success`/`danger`/`default`/`warning`/`muted`) so no two states share a color. New sidebar nav entry "Security Tests".

**Rationale:** Reuses the Phase 3 engine and existing detector/scanner exactly as designed — no new detection logic invented except where the spec explicitly requires new categories. The INCONCLUSIVE-only unsafe-output plugin is a direct, literal application of Phase 4's own instruction not to overclaim.

**Consequence:** 9 new Python tests (`tests/test_attack_library_phase4.py`), full suite 154 passed/3 skipped (up from 145/3, zero regressions). Web: `tsc --noEmit` clean, vitest 13 passed (unchanged). `docs/SECURITY_ENGINE.md` updated with the category table, severity rubric, and UI/endpoint description.

---

## D-044 — Findings subsystem (phase_dev_upgrade.md Phase 5)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 5 asks for a Findings subsystem on top of the Phase 3/4 engine: finding ID/test ID/category/severity/title/description/affected target/evidence/reproduction/timestamp/model-provider/status fields, OPEN/ACKNOWLEDGED/RESOLVED/RETEST_REQUIRED states, never deleting historical evidence on resolution, and a Finding→Test→Attack→Model response→Evidence→Reproduce detail UI.

**Decision:**
- New `Finding` SQLAlchemy model (`proxy/db/models.py`) — persisted (not in-memory), since findings must survive across runs and carry a real history. Rows are only ever updated (`status`/`updated_at`), never deleted.
- New `proxy/findings.py`: `sync_findings(db, results)` opens a Finding only for `TestStatus.FAIL` results (`ERROR`/`INCONCLUSIVE` are test-health signals, not vulnerabilities — no finding). Dedup rule: skip if an OPEN/ACKNOWLEDGED/RETEST_REQUIRED finding already exists for that `test_id`; a RESOLVED finding that fails again gets a fresh row, old one untouched.
- 4 new endpoints on `proxy/main.py`: `POST /v1/findings/sync` (run + persist), `GET /v1/findings` (list, optional `status` filter), `GET /v1/findings/{id}`, `PATCH /v1/findings/{id}` (status-only, 404 on missing id, 422 on an invalid status via `FindingPatch`'s `Literal`). The existing `POST /v1/security-tests/run` (Phase 4) is untouched — sync/list/detail are additive.
- Status transitions are unrestricted (any state to any state via PATCH) — no state machine invented, since the spec doesn't require one and automatic pass→resolved transitions are explicitly Phase 7's job (baseline/regression comparison), not this phase's.
- Frontend: `web/app/findings/page.tsx` (list + filter + sync button), `web/app/findings/[id]/page.tsx` (detail with the 5-tab drill-down: Test/Attack/Model response/Evidence/Reproduce, plus status-change buttons), `components/findings/finding-status-badge.tsx` (4 states, 4 distinct badge colors — same never-collapse-to-boolean principle as Phase 4's `TestStatus` badges).

**Rationale:** Builds strictly on `TestResult` from Phase 3/4 without re-running or duplicating test logic. Persisting to SQLite (not in-memory) is required by "do not delete historical evidence" — an in-memory store can't survive a proxy restart and wouldn't count as a real history.

**Consequence:** 11 new tests (`tests/test_findings.py`) covering FAIL-only creation, dedup, resolved-then-refails history preservation, the full endpoint flow, 404s, and invalid-status rejection. Full suite: 165 passed, 3 skipped (up from 154/3, zero regressions). Web: `tsc --noEmit` clean, vitest 13 passed (unchanged — no web unit tests added for the new pages, consistent with the project's existing pattern of Playwright e2e over component unit tests for full pages). `docs/FINDINGS.md` documents the model, states, dedup rule, and endpoints.

---

## D-045 — Security dashboard + persisted test-run history (phase_dev_upgrade.md Phase 6)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 6 requires a dashboard built on real backend data (total tests, passed, failed, errors, open findings, severity distribution, recent activity, affected models, test history) with explicit empty/loading/error states, no fake metrics, and no unnecessary exposure of sensitive test payloads. Gap found: nothing persisted PASS/ERROR/INCONCLUSIVE results — `Finding` only records FAILs (D-044) and `POST /v1/security-tests/run` is stateless (D-043). Without new persistence, "total tests / passed / history" could only have been faked, which the spec explicitly forbids.

**Decision:**
- New `TestRunResult` table (`proxy/db/models.py`): one row per test outcome per run, any status, grouped by a `run_id` (uuid4 per sync call). Chosen over adding status columns to `Finding` because findings are human-actionable vulnerabilities while this is execution telemetry — different lifecycles.
- `proxy/findings.py::record_test_run(db, results)` logs every result; `POST /v1/findings/sync` now calls it alongside `sync_findings()`. `POST /v1/security-tests/run` stays stateless (the ad-hoc "check now" path).
- `run_id` grouping means "total tests" = the latest run's count, not a cumulative sum that would inflate on every sync. Also the grouping Phase 7's baseline comparison will need — built now because the alternative (timestamp-equality grouping) doesn't actually work.
- New `proxy/dashboard.py::build_dashboard_summary(db)` + `GET /v1/security-dashboard`. Aggregate-only: no `raw_input`/`raw_output`/evidence in the payload. Severity distribution is computed over *open findings* (current risk exposure), documented as such rather than left ambiguous.
- Frontend: `web/components/security/dashboard-summary.tsx` mounted above the existing Live test run table on `/security` (existing functionality preserved, no new nav entry). `getSecurityDashboard()` deliberately breaks the codebase's usual never-throw-return-empty pattern, returning a discriminated `{status: "ok" | "error"}` — collapsing a fetch failure into an empty result would make Phase 6's required empty and error states indistinguishable.

**Rationale:** The only honest way to satisfy "no fake metrics" for history-shaped metrics was to actually persist history. Everything else reuses what Phases 3-5 already built.

**Consequence:** 7 new tests (`tests/test_dashboard_phase6.py`), including a regression test that raw attack payloads never appear in the dashboard response. Full suite: 172 passed, 3 skipped (up from 165/3, zero regressions). Web: `tsc --noEmit` clean, vitest 13 passed. `docs/SECURITY_DASHBOARD.md` documents every metric's source. Note: `/dashboard` (the older Eval dashboard over `CallLog` proxy traffic, D-028) is untouched and remains a separate page — it answers "what is the proxy doing", not "how secure is it".

---

## D-046 — Security regression testing (phase_dev_upgrade.md Phase 7)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 7 requires baseline creation, comparison of a later run against it, detection of newly-failing/newly-passing tests, new/resolved findings, changed severity, and changed provider config — with an explicit instruction not to make a "security score" the sole source of truth, individual results must stay accessible.

**Decision:**
- New `Baseline` table (`run_id` pointer only, no duplicated data — reuses D-045's `TestRunResult.run_id` grouping, which is exactly why that grouping was built in Phase 6 rather than deferred).
- `proxy/regression.py::compare_runs()` is a pure function (two snapshot lists in, a diff dict out) — no DB/time dependency, so the comparison logic itself is trivially unit-testable without spinning up a session. `findings_delta()` separately pulls new/resolved findings since the baseline's timestamp, reusing D-044's `Finding` table rather than re-deriving finding state from the run diff.
- No score field anywhere in the report. The report is bucketed counts (regressions/new_failures/fixed/unchanged/other_changes/severity_changes/added_tests/removed_tests/provider_config_changed) plus `per_test`, a full baseline-vs-current row per test — literal compliance with "the underlying individual test results must remain accessible."
- 3 endpoints: `POST /v1/baselines` (409 if nothing has run yet — never creates an empty baseline), `GET /v1/baselines`, `GET /v1/regression-report` (404 no baseline / 409 no run to compare, both real distinguishable states, not generic 500s).
- `web/app/regression/page.tsx`: create-baseline button, summary cards, regressions/fixed/findings-delta sections, full per-test table. `createBaseline()`/`getRegressionReport()` return discriminated ok/error results (same pattern as D-045) so "no baseline yet" renders its own explained state rather than a blank page.

**Rationale:** Everything needed already existed after Phase 6 (`TestRunResult.run_id`, `Finding`) — Phase 7 is comparison logic and a pointer table, not new execution infrastructure.

**Consequence:** 18 new tests (`tests/test_regression_phase7.py`), covering the pure comparator (regression/fix/unchanged/added/removed/severity-change/provider-change detection) independently from the DB-backed baseline/endpoint flow. Full suite: 190 passed, 3 skipped (up from 172/3, zero regressions). Web: `tsc --noEmit` clean, vitest 13 passed (unchanged). `docs/REGRESSION.md` documents the model and both endpoints.

---

## D-047 — CI/CD for security tests (phase_dev_upgrade.md Phase 8)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 8 requires a developer-friendly CLI/API workflow: select a target and a test suite, execute, produce machine- and human-readable results, enforce a configurable (never hardcoded) failure threshold, detect regressions, document GitHub Actions integration, and never require exposing provider API keys in source code.

**Decision:**
- `proxy/ci.py`: pure policy evaluation (`CIPolicy`, `evaluate()`, `matching_results()`, `format_human_summary()`) — no HTTP, no subprocess, so the pass/fail logic is unit-tested directly. Every threshold (`fail_on_statuses`, `fail_on_severities`, `max_failures`, `max_regressions`) is a dataclass field the caller sets; nothing is decided inside `evaluate()` itself.
- `scripts/sentinel_ci.py`: thin CLI wrapper (argparse, stdlib) calling a target's `POST /v1/findings/sync` (records the run — reuses D-045's persistence, doesn't invent a second execution path) and optionally `GET /v1/regression-report` (D-046). Talks HTTP only — needs no provider API key, since the target instance already holds its own (D-041).
- `_select_tests(category)` added to `proxy/main.py`; `POST /v1/security-tests/run` and `POST /v1/findings/sync` both gained an optional `category` query param (comma-separated) — "selecting a test suite" actually skips execution of unselected categories, not just filters the display.
- `--json-out`/`--md-out` write the full result set + verdict (machine-readable) and the same Markdown the CLI prints to stdout (human-readable, `$GITHUB_STEP_SUMMARY`-ready).
- `.github/workflows/security-tests.yml`: separate from `ci.yml` (that runs the unit test suites; this runs SentinelAI's own security tests against a booted instance). Its `--fail-on-severity critical,high` is a sample policy in the workflow file, not special-cased in the CLI — editable per repo.
- Found and fixed a latent test-isolation bug while adding Phase 8's tests: `test_dashboard_phase6.py`/`test_regression_phase7.py`/`test_findings.py` only cleared their tables in `teardown_function`, not `setup_function` — harmless in isolation, but the shared `sqlite:///:memory:` engine (a process-wide singleton, `proxy/db/session.py`) let one file's leftover rows leak into another's "before anything has run" assertions depending on collection order. Fixed by clearing tables in both setup and teardown in all three files.

**Rationale:** HTTP-only, no in-process imports of `proxy.main`, mirrors how a real CI job or a developer's laptop would reach a deployed instance — the same reason D-046's regression endpoints are HTTP, not a Python API.

**Consequence:** 20 new tests (`tests/test_ci_phase8.py`) — pure policy logic, CLI with HTTP mocked, and the new `category` filter at the endpoint level — plus a real end-to-end smoke run against a live local `uvicorn` process (not just mocks) confirming exit code 0 on an all-passing suite. Full suite: 210 passed, 3 skipped (up from 190/3, zero regressions once the test-isolation fix landed). `docs/CI_CD.md` documents the policy flags, output formats, and the GitHub Actions workflow.

---

## D-048 — Agent security policy layer (phase_dev_upgrade.md Phase 9)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 9 asks to model an agent as Model/Tools/Permissions/Data sources/Actions, implement an explicit ALLOW/DENY/REQUIRE_APPROVAL tool-permission policy, track (agent, tool, requested action, policy decision, execution result), build the policy/evaluation layer first, and never implement real destructive actions as part of testing.

**Decision:**
- `proxy/agent_policy.py`: pure `evaluate(profile, request)`. Default deny; unregistered tool or data source → DENY; most-restrictive-wins among matching rules (DENY > REQUIRE_APPROVAL > ALLOW); canonicalized exact-match names; `*` only as a rule action wildcard, rejected in requests. (Tool-level wildcards in rules deliberately not supported — no need yet, and one less bypass surface.)
- Profiles come only from server-side YAML (`proxy/agent_profiles.yaml`, `AGENT_PROFILES_PATH` setting, default resolved relative to the package so it's CWD-independent) — same server-side-config principle as D-041. One clearly-labelled example profile ships with it.
- SentinelAI never executes a tool. `AgentActionLog.execution_result` records the policy-layer outcome (`blocked` / `allowed_not_executed` / `pending_approval` / `approved_not_executed` / `rejected`) — this is how "no destructive actions" is guaranteed structurally rather than by convention.
- Human approval is a separate step (`POST /v1/agent-actions/{id}/approve|reject`): only pending rows (409 otherwise — a DENY can't be approved into an ALLOW), approver required (422), approver ≠ requesting agent (403). Approval is never read from the evaluate request body.
- No UI and no `proxy/engine` plugin yet — explicitly deferred; spec asks for the policy layer first.

**Rationale:** Pure core + thin persistence mirrors D-042/D-046/D-047 — the security-relevant logic is unit-testable without HTTP or DB. Structural no-execution is stronger than a "please don't" flag.

**Consequence:** 32 new tests (`tests/test_agent_security_phase9.py`) covering authorized/unauthorized tool use, denied action, approval-required action, precedence, and 10+ bypass variants (case, whitespace, wildcard request, appended commands, prefix names, path smuggling, empty names, agent-supplied approval field, self-approval, approving a DENY, re-resolving). Full suite: 242 passed, 3 skipped (up from 210/3). `docs/AGENT_SECURITY.md`.

---

## D-049 — Runtime Gateway as a separate service (phase_dev_upgrade.md Phase 10)

**Date:** 2026-09-23
**Status:** Accepted (deployment shape: user said "go ahead" on the recommended option — separate app — 2026-09-23)

**Context:** Phase 10 requires a separate gateway subsystem (request/response inspection, policy, allow/block, logging, audit events, provider routing), not coupled to the dashboard, stateless where practical, no raw sensitive content stored unless configured, never logging keys/tokens/secrets. It adds a new runtime service, which CLAUDE.md's User-Controlled Changes section requires surfacing first — done, recommended separate app accepted.

**Decision:**
- New top-level `gateway/` package with its own FastAPI app (`gateway.main:app`, port 8002). Imports SentinelAI's inspectors (`check_injection`, `check_pii`, `redact_pii`) and provider layer (`build_provider`, `get_provider`) as a library; does not import `proxy.main`, the DB, findings, or dashboard.
- `gateway/pipeline.py::run_pipeline()` implements every stage; policy is a `GatewayPolicy` built from server-side settings (`GATEWAY_*`), actions `allow`/`redact`/`block` per direction.
- Stateless: no DB writes, no rate limiting, no session state (tested: 20 repeated calls identical, `CallLog` count unchanged).
- Audit events = JSON lines on `sentinelai.gateway.audit`, content as `{length, sha256}` only; raw text only when `GATEWAY_STORE_RAW_CONTENT=true`, and secrets redacted even then. Provider error messages withheld from both response and logs (tested with a key embedded in the upstream error).

**Also this session — regression protection for earlier work (user request):**
- Found a real Phase 2 regression: `web/components/playground/result-card.tsx` treated every 400 as an injection block, so D-041's new 400 `provider_credentials_missing` would have rendered as **"Not blocked"** with no output. Fixed by extracting `web/lib/classify-result.ts` (only a flagged injection is "blocked"; any other non-200 is "failed") + 5 vitest cases.
- `tests/test_playground_regression_guard.py`: parses the *web's* actual presets (`web/lib/sample-attacks.ts`) and `SYSTEM_PROMPT` (`web/lib/api.ts`) from source; asserts web presets == Python mirror, every preset is blocked with its documented patterns, benign prompts with the real system prompt pass, and the system prompt would self-trip if scanned (proves D-033's guard is load-bearing).
- Live-verified against a real proxy + real Groq key: all 4 presets 400 `injection_detected` with exact patterns; benign prompt 200 from Groq.

**Consequence:** 18 gateway integration tests + 8 playground guard tests; full suite 268 passed, 3 skipped (up from 242/3). Web: `tsc` clean, vitest 18 passed (up from 13). Live gateway smoke: benign ALLOW via Groq, injection BLOCK, request email redacted before reaching the model, unknown route 400. `docs/GATEWAY.md`. Deployment config (`deploy/render.yaml`) not yet updated for a third Python service — flagged, not done.

---

## D-050 — Continuous monitoring: security event model (phase_dev_upgrade.md Phase 11)

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Phase 11 requires tracking attack attempts, blocked requests, policy violations, new findings, regressions, and suspicious tool activity in an event model separate from findings (not every event is a vulnerability), filterable by time/severity/application/model/category/event type, with retention/config controls.

**Decision:**
- New `SecurityEvent` table + `proxy/events.py` (`record_event`, `query_events`, `purge_expired`, `events_config`). No status field — events are observations. Metadata only; never prompt/response text or the PII/secret itself.
- Emitters wired into existing flows in `proxy/main.py`: `/v1/generate` (injection → attack_attempt; rate-limit/oversize → request_blocked; inbound/outbound PII → policy_violation), `/v1/findings/sync` (new finding → finding_opened; regression vs newest baseline → regression_detected), agent endpoints (normal DENY → policy_violation; out-of-bounds request, self-approval, approving a DENY → suspicious_tool_activity).
- `PolicyDecision` (D-048) gained a machine-readable `code` + `OUT_OF_BOUNDS_CODES`, so "suspicious" is classified from codes, not by parsing reason strings.
- Gateway: optional `event_sink` in `run_pipeline`; `GATEWAY_RECORD_EVENTS` default **false**, preserving D-049's statelessness and its "writes nothing to the DB" test. Lazy import so the gateway doesn't touch the DB module unless enabled.
- Controls: `EVENTS_ENABLED`, `EVENTS_RETENTION_DAYS` (default 30, 0 = forever; applied on proxy start and via `POST /v1/events/retention/apply`; only events purged), `EVENTS_MIN_SEVERITY`. `GET /v1/events/config`.
- `record_event` never breaks the triggering request — failure logged + rolled back (explicit, per CLAUDE.md §11, not swallowed silently).
- UI: `web/app/monitoring/page.tsx`.

**Rationale:** Hooking existing decision points rather than adding a new inspection path means events can't drift from what the guardrails actually did.

**Consequence:** 26 new tests (`tests/test_monitoring_phase11.py`). Full suite 294 passed, 3 skipped (stable across repeated runs). Web `tsc` clean, vitest 18 passed. Live-verified: playground presets still 400, benign still 200 via Groq with no event, events recorded and filterable. **Known pre-existing issue flagged, not fixed:** backend returns naive-UTC timestamps (SQLite `DateTime`), and every web page (`findings`, `dashboard`, `regression`, `monitoring`) passes them to `new Date()`, which reads them as local time — displayed times are offset by the viewer's UTC offset. Root fix is either timezone-aware serialization in the backend or one shared web parse helper; touches several files, so left for an explicit decision.

---

## D-051 — Fix: naive-UTC timestamps displayed offset by viewer timezone

**Date:** 2026-09-23
**Status:** Fixed (root cause, not per-page patches)

**Context:** Flagged at the end of Phase 11: SQLite/SQLAlchemy `DateTime` columns store naive datetimes; `datetime.now(timezone.utc)` was written but read back without tzinfo, serialized without a UTC offset, and every web page's `new Date(iso_string)` then parsed it as *local* time — every displayed timestamp (findings, dashboard, regression, monitoring) was off by the viewer's UTC offset.

**Decision:** New `UTCDateTime` `TypeDecorator` (`proxy/db/models.py`) replacing every `DateTime` column (8 columns across 6 models): strips tzinfo on write (converting to UTC first if aware), re-attaches `timezone.utc` on read. Every timestamp the API serializes now carries an explicit `+00:00`, so `new Date(...)` on the web side parses correctly with no frontend change needed anywhere.

**Rationale:** A single type-level fix at the ORM boundary is smaller and can't be missed on a new column, unlike patching `new Date()` calls across 4+ web pages (or worse, only some of them).

**Consequence:** New `tests/test_timestamps_utc.py` (5 tests: API round-trip, non-UTC input normalized to the same instant, aware-in/aware-out equality). Full suite 298 passed at the time of this fix (up from 294/3).

---

## D-052 — Phase 8-12 follow-through: closed open items, remediation guidance, reports

**Date:** 2026-09-23
**Status:** Accepted

**Context:** Three items were flagged open after Phase 10/11 (deploy config, agent-security UI, agent engine plugin), plus a real gap found while scoping Phase 12: Findings never had the `remediation` field Phase 5 actually asked for. All closed together, then Phase 12 (reporting) built on top.

**Decision:**
- **`deploy/render.yaml`**: added `sentinelai-gateway` as its own Render web service — no disk (D-049's statelessness), own provider keys, `GATEWAY_RECORD_EVENTS` documented as requiring a shared `DATABASE_URL` if ever turned on (the proxy's local SQLite disk isn't shared). Pinned with a test asserting the service's `startCommand` module actually resolves to the gateway app, and its Groq key entry is `sync: false` with no committed value.
- **`proxy/engine/plugins/agent_policy_tests.py`**: 9 new engine tests replaying D-048's bypass attempts (case/whitespace tricks, wildcard request, appended command, tool-prefix, unregistered data source, default-deny, approval-required-stays-gated, a control ALLOW case) against a fixed reference profile — not the operator's live `agent_profiles.yaml`, so the suite is deterministic regardless of what a deployment configures. A mutation test (swap in an always-ALLOW evaluator) proves the plugin actually fails when the policy is broken, not just always-passes.
- **`web/app/agents/page.tsx`**: profile browser, live evaluate-an-action form, decision log with approve/reject (blocked client-side until an approver name is entered — server still enforces it).
- **`proxy/remediation.py`** + `remediation_for()`: static per-category guidance, added to `Finding` API responses (`finding_to_dict`) and to every report row.
- **Phase 12, `proxy/reports.py`**: executive + technical reports, built only from `test_run_results`/`findings`/`baselines`/`security_events` — generating one never runs a test. `scrub()` removes the server's configured provider keys by literal match plus runs `redact_pii` on every string, exempting `run_id` fields (digit-heavy uuids can false-match the phone regex). Executive report's `limitations` section is always populated and names INCONCLUSIVE/ERROR results explicitly — carries forward the spec's own "passing tests don't prove security" warning into the artifact itself, not just documentation.
- `GET /v1/reports/executive` / `GET /v1/reports/technical`, `?format=md` for Markdown; `web/app/reports/page.tsx`.

**Rationale:** Closing flagged debt before starting new work keeps `state.md`'s "open follow-ups" list from silently growing across phases (CLAUDE.md's own consistency rule). Remediation guidance and reports are naturally sequenced together — a report without remediation text would just restate raw evidence.

**Consequence:** 20 new tests total (9 agent-policy-plugin + 1 render.yaml pin + Phase 12 tests counted separately below is fine — see per-file breakdown in progress_log.md). Full suite 318 passed, 3 skipped, stable across 3 consecutive runs (up from 298/3). Web: `tsc --noEmit` clean, vitest 18 passed (unchanged — reports/agents pages read-only against mocked-free live endpoints, following the project's existing pattern of Playwright/live verification over component unit tests for full pages). Live-verified end to end against the real proxy + real Groq key: playground presets still blocked, a benign prompt still answered, a full findings-sync → baseline → executive+technical report cycle produced correct output with the real configured Groq key absent from both the JSON and 16KB Markdown output.

---

## Decision-writing rule

## D-053 — Production database: Supabase (Postgres), shared across proxy and gateway

**Date:** 2026-09-24
**Status:** Accepted

**Context:** D-009 named SQLite as the baseline "move to Supabase/Postgres only if the single-file approach becomes insufficient." User explicitly requested the move now: the app is being deployed to the cloud, and a local-disk SQLite file per Render service can't be a shared source of truth between `proxy` and `gateway`, nor does it fit a real production deployment. User also raised a secrets concern (no DB credentials in the CLI or anywhere insecure) — already true independently (D-047: the CLI is HTTP-only, never touches the DB), but the migration reinforces it: the connection string becomes a platform secret (`sync: false` in `deploy/render.yaml`), never a file in the repo.

**Decision:**
- `DATABASE_URL` becomes the production Supabase Postgres connection string, set as a Render dashboard secret, never committed. Local dev keeps the SQLite default in `.env.example` — no reason to require Supabase for local work or tests.
- `psycopg2-binary` added to `requirements.txt`.
- Real bug found and fixed in `proxy/db/session.py`: `connect_args={"check_same_thread": False}` was unconditional — that kwarg is SQLite-only (pysqlite) and `psycopg2` raises `TypeError` on it. Now only passed for `sqlite://` URLs (`_connect_args()`, tested).
- No SQLAlchemy model changes needed — `JSON`/`DateTime`/`String`/`Integer`/`Float` are all backend-portable; `UTCDateTime` (D-051) already works identically on Postgres (its docstring's SQLite framing was about why the bug existed, not a SQLite-only mechanism).
- Gateway's `DATABASE_URL` (new) is meant to be the *same* Supabase instance as the proxy's, so `GATEWAY_RECORD_EVENTS=true` becomes safe to turn on — shared truth was the actual blocker on that flag, not just "no DB".

**Rationale:** No architecture invented — SentinelAI's storage layer was already ORM-based and backend-agnostic in design; this makes it backend-agnostic in practice by fixing the one SQLite-specific line and wiring the secret path.

**Consequence:** `docs/SUPABASE.md` documents setup, rollback, and what doesn't change (SDK/CLI and web never touch the DB directly — HTTP only, unaffected). 2 new tests (`tests/test_db_backend_portability.py`) pin the `connect_args` branching so a future change can't silently reintroduce the SQLite-only kwarg for Postgres URLs. Existing SQLite-based test suite runs unmodified (`DATABASE_URL=sqlite:///:memory:` in tests, untouched). Actual Supabase project creation/connection-string handoff is the user's own action — this change is the code+config+docs side, not a live migration (no real Supabase credentials were available to this session to verify an actual connection end-to-end).

---

## D-054 — Fix: Presidio false-positives on non-PII entity types; redact_pii silently not redacting Presidio-only matches

**Date:** 2026-09-24
**Status:** Fixed (real, pre-existing production bug — found while diagnosing a GitHub Actions CI failure, not introduced by this session's other work)

**Context:** GitHub Actions CI was failing on `main` itself (confirmed: same job/step fails on the exact commit `main` was already at, before any of this session's branches existed). Reproduced locally by installing `requirements.txt` fresh into a clean venv (mirroring what CI's `pip install -r requirements.txt` does every run, vs. this session's long-lived local venv which had older resolved versions since `requirements.txt` pins no versions). The failure: `tests/test_monitoring_phase11.py::test_benign_request_emits_no_event` — asking "What is the capital of France?" produced a `policy_violation` / `sensitive_data_inbound` event. Root cause: `proxy/middleware/pii_scanner.py::_presidio_types()` treated *every* Presidio-detected entity type as PII with no filtering, including `LOCATION` — a fresh `presidio-analyzer` install correctly initializes (this session's stale local venv apparently had it silently failing to initialize, masking the issue) and flags country/city names as `LOCATION`. This is a real bug that would affect actual users in production, not a test-only artifact: any message mentioning a place, a date, a nationality, or containing a URL was being treated as containing sensitive data.

**Decision:**
- `_presidio_types()`/new `_presidio_results()` now filter to an explicit allowlist of genuinely identifying entity types (`person`, `email_address`, `phone_number`, `credit_card`, `us_ssn`, `ip_address`, etc.) — excluding Presidio's broad "context" categories (`LOCATION`, `DATE_TIME`, `NRP`, `URL`, and similar) that were never real PII.
- Second bug found and fixed in the same function while investigating: `redact_pii()` computed `redacted=True` from `check_pii().found` but only actually replaced text matching the four `PATTERNS` regexes — any PII detected *only* by Presidio (e.g. a person's name, which has no regex pattern) was left untouched in the returned text while the result still claimed `redacted=True`. This is live in both `gateway/pipeline.py`'s PII-redact policy path and `proxy/reports.py::scrub()`. Fixed: `redact_pii()` now builds a unified span list (regex matches + Presidio matches using Presidio's own `start`/`end` offsets) and does a single left-to-right substitution pass over the original text, so every claimed redaction is a real one.

**Rationale:** Filtering happens at the entity-type layer (a data allowlist), not by disabling Presidio or lowering its confidence threshold — keeps the detector's actual NER capability intact for the entity types that are genuinely identifying, per D-016's original intent.

**Consequence:** 7 new tests in `tests/test_pii_scanner.py` pin both fixes (LOCATION/DATE_TIME/NRP/URL not flagged, US_SSN still flagged, Presidio-only spans actually stripped, mixed regex+Presidio spans both stripped in one pass) — using a fake analyzer so the tests are deterministic regardless of which real Presidio/spaCy versions are installed in whatever venv runs them. Verified against both this session's long-lived local venv and a freshly-installed venv (matching what actually broke CI) — 327 passed, 3 skipped in both, no regressions. This fix is independent of and should land ahead of the V3 Phase 1 baseline and Supabase-migration branches in flight — it's a correctness/security fix unrelated to either.

---

## D-055 — Phase 2 (spec_V3.md): stateless JWT auth + User → Workspace → Project isolation

**Date:** 2026-09-24
**Status:** Accepted

**Context:** spec_V3.md's multi-tenant SaaS model (§9, §59, §67 Phase 2) requires that every caller be authenticated and that a request for one project's data can never return another project's data. Before this, every endpoint was open with no notion of a caller or a tenant boundary.

**Decision:**
- Auth is stateless JWT (PyJWT, HS256), bcrypt password hashing, no session store (`proxy/auth.py`). `EmailStr` was avoided in favor of a plain `str` + regex validator to skip adding the `email-validator` dependency for one field.
- Data model: `User` → one `Workspace` (auto-created on signup, no cross-user workspace sharing — nothing in Phase 2 asks for it) → many `Project`. Every existing content table (`CallLog`, `Finding`, `TestRunResult`, `AgentActionLog`, `SecurityEvent`, `Baseline`) gained a nullable `project_id` FK, added via an additive `ALTER TABLE` migration run after `create_all()` (no Alembic — matches the project's existing no-migration-tool convention).
- A global FastAPI middleware requires a bearer token on every route except `/health`, `/docs`, `/redoc`, `/openapi.json`, `/v1/auth/signup`, `/v1/auth/login`.
- Project isolation is enforced through one choke point, `proxy/projects.py::owned_project()` — 404 (never 403) on any mismatch, so a project ID's existence is never confirmed to someone who doesn't own it.
- Only the core data paths spec_V3.md §67 Phase 2 names were retrofitted to be project-scoped this pass: `/v1/generate`, `/v1/findings/*`, `/v1/security-dashboard`, `/v1/calls`. Agent policy (`/v1/agents/*`, `/v1/agent-actions/*`), baselines/regression (`/v1/baselines`, `/v1/regression-report`), events (`/v1/events*`), and reports (`/v1/reports/*`) remain globally-authenticated via the middleware but are **not yet project-scoped** — a deliberate, tracked scoping gap, not a silent one, left for a later phase since spec_V3.md doesn't require it in Phase 2.
- A known consequence of the baseline gap above: `/v1/findings/sync`'s regression-detection lookup still finds the newest baseline across *all* projects, not just the caller's — because `create_baseline()` doesn't set `project_id` yet. Scoping both together is the correct fix; scoping one without the other would silently break regression detection for every project.

**Rationale:** JWT over server-side sessions because the proxy is meant to run stateless behind a load balancer (spec_V3.md's cloud deployment target) with no shared session store. The `owned_project()` choke point exists so isolation logic is written once and reused, not re-implemented per endpoint.

**Consequence:** Breaking change for every existing unauthenticated caller (web playground, CLI, old test suite) — expected and necessary, not accidental. All 16 affected test files were retrofitted to sign up a user and create a project via a new shared `tests/auth_helpers.py::auth_headers_and_project()` helper; full suite is green (327 passed, 3 skipped, 0 failed, 0 regressions). `.env.example` and `deploy/render.yaml` gained `JWT_SECRET`/`JWT_EXPIRY_HOURS`; the app refuses to start in production without `JWT_SECRET` set. Frontend (web playground) login UI and updated API calls are not yet built — still open.

---

When an open decision is resolved:
1. Add a dated decision entry.
2. Mark the OD item resolved.
3. Record rejected alternatives if they materially affected the implementation.
4. Update `spec.md` if the decision changes a requirement or contract.
