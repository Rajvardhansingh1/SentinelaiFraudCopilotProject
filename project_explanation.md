# Project Explanation — SentinelAI + Fraud Copilot

## 1. Why the project exists

The project is intentionally both an AI application and an AI infrastructure component.

A normal fraud-agent demo could show OCR → agents → fraud verdict. This project adds a reusable trust layer underneath the agents. The result demonstrates that LLM usage is treated as an infrastructure boundary rather than as an unquestioned dependency.

The central idea:

```text
                 Reusable platform
              ┌─────────────────────┐
              │      SentinelAI      │
              │ safety + evaluation  │
              └──────────┬──────────┘
                         │
                         │ protects
                         ▼
              ┌─────────────────────┐
              │   Fraud Copilot     │
              │ application agents  │
              └─────────────────────┘
```

## 2. SentinelAI

SentinelAI is a FastAPI proxy between callers and an LLM provider.

A caller should not do:

```text
Agent → Groq/Gemini
```

It should do:

```text
Agent → SentinelAI → Groq/Gemini
```

This gives one request-level control point.

### Request path

```text
Request
  ↓
Injection / jailbreak check
  ↓
PII + secret scan
  ↓
Request validation
  ↓
Rate limit
  ↓
Sanitized request
  ↓
LLM provider
```

### Response path

```text
Raw LLM response
  ↓
Schema validation
  ↓
PII + secret scan
  ↓
Hallucination / grounding evaluation
  ↓
Logging
  ↓
Validated response + metadata
```

The exact order of middleware is an implementation detail that must be finalized before Phase 1 is considered complete.

## 3. Why OCR text is a security boundary

An uploaded receipt can contain adversarial text.

For example, a tiny piece of text inside an image could attempt to instruct the downstream model to ignore a policy.

The image is processed locally:

```text
Image
  ↓
OCR
  ↓
Raw text
```

The raw OCR text is not trusted simply because it came from an image.

When it becomes input to an LLM call:

```text
OCR text → SentinelAI → injection detection → LLM
```

This makes image-embedded prompt injection a concrete demonstration of the guardrail platform.

## 4. Fraud Copilot

The application has four logical stages.

### Extractor

Local OCR identifies text.

An LLM call, routed through SentinelAI, converts OCR text into structured receipt data:

```text
vendor
date
line_items
total
```

The structured result is Pydantic validated.

### Forensics

This stage does not require an LLM.

OpenCV performs error-level analysis and image processing. EXIF metadata is also checked for inconsistencies.

Output is forensic evidence and a tamper-likelihood signal.

ELA should be treated as evidence, not mathematical proof that an image was edited.

### Policy Checker

The extracted fields and forensic evidence are combined with a YAML policy.

The LLM is used through SentinelAI to interpret/check the extracted information against policy rules and identify triggered rules.

### Report Writer

The final LLM stage synthesizes:

- extracted fields
- forensic signals
- policy result
- grounding evidence

The result is a structured audit report plus guardrail metadata.

## 5. LangGraph role

LangGraph orchestrates state movement between agents.

Conceptually:

```text
Receipt
  ↓
Extractor
  ↓
Forensics
  ↓
Policy Checker
  ↓
Report Writer
  ↓
Human Review
```

Each node has a clear input/output contract.

The graph is orchestration. SentinelAI remains the LLM trust boundary.

## 6. Hallucination evaluation

The project defines two evaluation modes.

### Grounded mode

Used when supporting context exists.

```text
Response
  ↓
Atomic claims
  ↓
Retrieve grounding context
  ↓
Entailment evaluation
  ↓
supported / contradicted / unsupported
  ↓
unsupported ÷ total
```

For the fraud application, OCR receipt text is part of the grounding context.

### Ungrounded mode

When no grounding context exists, the baseline calls for self-consistency sampling.

Multiple generations are compared to estimate consistency.

The exact model, threshold, sampling count, and aggregation formula are intentionally left as an implementation decision until the evaluation layer is built.

## 7. Guardrail metadata

A fraud verdict should not appear as a naked label.

The UI should expose relevant evidence such as:

- confidence
- grounding sources
- hallucination percentage
- injection status
- policy evidence
- forensic signals

The purpose is to make the model's output inspectable.

## 8. Human-in-the-loop design

The system produces a recommendation/verdict for review.

It does not execute the final business decision.

The UI therefore needs to distinguish:

```text
System assessment
        ↓
Evidence + guardrail metadata
        ↓
Human reviewer
        ↓
Approve / Reject
```

This distinction must remain visible in the UI.

## 9. Evaluation dataset

The source specification calls for approximately 40–60 genuine receipts/invoices plus matched tampered versions.

Tampering examples:
- edited amount
- swapped date
- spliced line item

Each sample receives a label in `labels.csv`.

This allows measured evaluation rather than a demonstration based on a handful of manually selected examples.

## 10. Metrics

The project should report:

- field-level extraction accuracy
- tamper detection precision
- tamper detection recall
- policy-violation detection accuracy
- hallucination percentage distribution
- injection catch rate
- end-to-end latency

No metric should appear in documentation as a project result until the evaluation suite has actually measured it.

## 11. Deployment

Baseline plan:

```text
FastAPI proxy → Render or Railway
Streamlit UI  → Hugging Face Spaces
Chroma        → embedded/persisted
Logs          → SQLite initially
LLM           → Groq + Gemini
CI            → GitHub Actions
```

Free-tier limitations are part of the demo design rather than hidden.

The UI should expose cold starts and quota states.

## 12. Important technical limitations

### Injection detector
A curated pattern library can miss novel attacks. A lightweight classifier can improve coverage but also introduce false positives/negatives.

### PII scanner
Detection is not the same as correct business handling. The response behavior must be explicitly specified.

### ELA
ELA is a forensic signal, not definitive proof of manipulation.

### Hallucination score
A numeric score depends on the claim decomposition and evaluation method. It must be interpreted as an evaluation signal rather than ground truth.

### Free-tier LLMs
Availability, latency, quotas, and model behavior can change.

### Streamlit
Streamlit is chosen for speed and demoability. It may be replaced later if richer product UX becomes a requirement.

## 13. What makes the architecture interview-relevant

The project demonstrates:

- LLM gateway/proxy design
- agent orchestration
- deterministic vs LLM responsibilities
- prompt-injection defense
- PII/security handling
- structured output contracts
- RAG/grounding
- evaluation
- observability
- synthetic evaluation data
- human-in-the-loop AI
- deployment constraints
- failure handling

The strongest architectural story is not that the model detects fraud by itself. It is that the application treats LLM calls as controlled, observable, evaluatable dependencies.
