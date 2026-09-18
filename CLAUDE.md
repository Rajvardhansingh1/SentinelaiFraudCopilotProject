# SentinelAI + Fraud Copilot — Claude Code Instructions

## 1. Project Context

You are working on **SentinelAI + Fraud Copilot**.

This is a two-layer system:

- **SentinelAI** — a reusable, domain-agnostic FastAPI proxy that sits between callers and LLM providers and applies request/response guardrails and evaluation.
- **Fraud Copilot** — a LangGraph multi-agent expense/invoice fraud-detection application built on SentinelAI.

The complete original project definition is in:

**`Project 1 Spec — SentinelAI + Fraud Copilot.md`**

This is the original project specification supplied for this project.

## 2. Original Project Specification — Important Rule

The original file:

**`Project 1 Spec — SentinelAI + Fraud Copilot.md`**

is the primary reference for the project's intended:
- functionality
- architecture
- requirements
- scope
- features
- technology choices
- data/evaluation requirements
- deployment plan
- build order

Do **not** modify the original specification during normal development.

`spec.md` is the structured **spec-driven-development implementation document** derived from the original specification. It organizes the work into development phases, requirements, acceptance criteria, test gates, and traceability.

### When there is confusion or doubt

If there is any:
- confusion
- doubt
- ambiguity
- missing detail
- apparent discrepancy
- disagreement between project documents
- disagreement between documentation and implementation

**go back to the original `Project 1 Spec — SentinelAI + Fraud Copilot.md` first.**

Do not silently invent, reinterpret, remove, or change the original project's intended behavior.

If the original specification resolves the question, follow it.

If the original specification does **not** resolve the question:
1. Check `decision.md` for an existing decision.
2. If no decision exists, identify the issue as an open decision.
3. Do not silently choose an architecture-changing behavior.
4. Record the eventual decision in `decision.md`.
5. Update `spec.md` if the decision changes an implementation requirement or contract.
6. Activate the enviornement using conda activate FraudCopilotProject. Before doing anything. 

The original specification is the reference for the **intended project**. The generated `spec.md` is the reference for **how that project is being developed through SDD**.

## 3. Mandatory Files to Understand

Before starting a meaningful development task, inspect:

1. `state.md` — current project state and exact continuation point.
2. `spec.md` — structured development specification.
3. `decision.md` — accepted decisions, conflicts, and open decisions.
4. `progress_log.md` — chronological implementation history.
5. `testing.md` — testing strategy and quality gates.

When there is uncertainty about what the project is supposed to do, read:

**`Project 1 Spec — SentinelAI + Fraud Copilot.md`**

Use `project_explanation.md` when deeper architectural understanding is useful.

Use `README.md` for the human-facing project overview.

Do not scan the entire repository automatically. Read the minimum relevant context, then inspect the source files involved in the task.

## 4. Specification-First Development

Development is **spec-driven**.

For every task:

1. Identify the relevant phase in `state.md`.
2. Identify the relevant requirement in `spec.md`.
3. Read that section.
4. Check `decision.md` for decisions affecting the requirement.
5. If anything is unclear or appears inconsistent, consult the original project specification.
6. Inspect the existing implementation.
7. Implement only what is currently in scope.
8. Test against the acceptance criteria.
9. Update project memory after meaningful progress.

### Important distinction

`CLAUDE.md` defines **how the agent works**.

`spec.md` defines the **structured development requirements**.

`Project 1 Spec — SentinelAI + Fraud Copilot.md` defines the **original intended project**.

Never treat a generated interpretation as permission to contradict the original specification.

## 5. Critical Architecture Invariants

These are high-level rules reflected in the project specification:

- SentinelAI is domain-agnostic.
- Fraud Copilot is the application layer built on SentinelAI.
- Every Fraud Copilot **LLM call** must pass through SentinelAI.
- Fraud Copilot agents must never call an LLM provider directly.
- PaddleOCR/RapidOCR OCR runs locally.
- OpenCV/EXIF forensic processing runs locally.
- OCR text is untrusted input when it enters an LLM call.
- Structured LLM outputs use Pydantic validation.
- Invalid structured output is retried once before failure, according to the original specification.
- Fraud verdicts must never automatically approve or reject a claim.
- A human reviewer makes the final approve/reject decision.
- The evaluation dataset uses synthetic data.
- Metrics must be measured before being presented as project results.
- Secrets must never be committed.

If implementation pressure conflicts with these rules, consult the original specification before changing behavior.

## 6. Development Phases

Follow the phase order defined in `spec.md`, which is derived from the original specification:

1. Project Foundation
2. Core SentinelAI Proxy
3. Evaluation Layer
4. Red-Team Playground
5. Fraud Copilot Agents
6. Synthetic Dataset & Evaluation
7. Review UI & Evaluation Dashboard
8. Deployment & Hardening

Do not assume a phase is complete because its code exists.

A phase is complete only when its requirements, acceptance criteria, and test gate are satisfied and the project-memory files are updated.

## 7. Development Workflow

### Before coding
- Read `state.md`.
- Read the relevant section of `spec.md`.
- Read relevant entries in `decision.md`.
- If there is any uncertainty, consult the original project specification.
- Inspect existing code.
- Identify dependencies and acceptance criteria.
- Determine what is in scope and out of scope.
- Activate Enviornment FraudCopilotProject using conda activate FraudCopilotProject.

### While coding
- Activate Enviornment FraudCopilotProject using conda activate FraudCopilotProject.
- Make the smallest coherent change.
- Preserve module boundaries.
- Keep interfaces explicit.
- Prefer simple, understandable code.
- Do not implement speculative future-phase functionality.
- Do not bypass SentinelAI for convenience.
- Do not weaken tests to make implementation pass.
- Do not introduce secrets or real client/company data.

### After coding
- Run relevant tests.
- Run security checks when appropriate.
- Verify implementation against `spec.md`.
- If behavior differs from the original specification, resolve that discrepancy before considering the task complete.
- Update `progress_log.md`.
- Update `state.md`.
- Update `decision.md` only when a durable decision/conflict was resolved.
- Update `testing.md` when the testing strategy changes.

## 8. Documentation Responsibilities

### `Project 1 Spec — SentinelAI + Fraud Copilot.md`
**Original project specification.**

Reference it whenever the intended behavior, architecture, scope, or requirements are uncertain.

Do not modify it during normal development.

### `spec.md`
**Structured SDD implementation specification.**

Contains:
- requirements
- development phases
- acceptance criteria
- test gates
- cross-phase invariants
- requirement traceability

It must remain consistent with the original specification.

### `decision.md`
**Why a durable design choice was made.**

Record:
- decision ID
- context
- options considered
- decision
- rationale
- consequences
- status

Record conflicts and their resolutions here.

### `state.md`
**Where the project is now.**

Maintain:
- active phase
- active spec
- completed phases
- implementation state
- blockers
- known defects
- exact next starting point

### `progress_log.md`
**What happened over time.**

Append chronological entries:
- date
- phase/spec
- work completed
- files changed
- tests/validation
- problems/blockers
- decisions
- next step

### `testing.md`
**How the project is tested.**

Maintain the testing strategy, test matrix, security tests, evaluation methodology, and quality gates.

### `project_explanation.md`
**How the system works.**

Use for detailed human-readable architecture and data-flow explanation.

### `README.md`
**How humans understand and run the project.**

Keep it aligned with the actual implementation.

## 9. Handling Discrepancies

Discrepancy handling is mandatory.

If two documents, documentation and code, or two requirements appear to conflict:

1. Identify the exact conflict.
2. Consult the original project specification.
3. Check whether `decision.md` already resolves it.
4. If resolved, follow the accepted decision.
5. If unresolved, record it as an open decision.
6. Do not silently choose a behavior that changes the project's intended architecture or scope.
7. If the resolution changes requirements, update `spec.md`.
8. Record the development impact in `progress_log.md`.
9. Update `state.md` with the resulting state.

### Interpretation precedence

Use this order when determining intended behavior:

1. Explicit user instruction in the current task.
2. Original project specification: `Project 1 Spec — SentinelAI + Fraud Copilot.md`.
3. Accepted decision in `decision.md`.
4. `spec.md` where it faithfully implements the original specification.
5. Existing tested implementation.
6. Other project documentation.
7. General engineering assumptions.

If the higher-priority source conflicts with a lower-priority source, **do not silently ignore the discrepancy**. Resolve it explicitly.

## 10. Scope Control

Do not:
- add features merely because they seem useful
- replace technologies without a recorded decision
- redesign the architecture silently
- claim metrics before measuring them
- turn the system into an autonomous fraud adjudicator
- allow direct agent-to-provider LLM calls
- use real client/company data
- create unnecessary abstractions

If a better alternative is discovered, record it as a decision before changing the project.

## 11. Error and Failure Handling

Failures must be explicit.

Do not:
- silently swallow provider errors
- present incomplete results as final
- hide rate-limit failures
- bypass guardrails
- convert failed validation into unvalidated output
- treat missing evidence as positive evidence

Follow the original specification and the relevant `spec.md` requirement.

If neither defines the behavior, create/resolve a decision before locking the behavior into implementation.

## 12. Security Rules

Treat all of these as untrusted:

- visitor prompts
- uploaded images
- OCR text
- LLM output
- external API responses
- user-provided filenames/content

Pay particular attention to:
- prompt injection
- image-embedded prompt injection
- PII
- API secrets
- malicious uploads
- path traversal
- unsafe configuration
- log leakage
- rate-limit bypasses

Never put secrets in source code, tests, documentation, logs, or committed sample data.

## 13. Skills

### Global skills

Use these when available and relevant:

- **Ponytail** — simpler, smaller, safer implementation changes.
- **Caveman** — concise agent communication and reduced unnecessary token usage.
- **Frontend Design** — intentional visual/product design for the Streamlit application.
- **UI/UX Pro Max** — UI/UX systems, dashboard hierarchy, interaction states, accessibility.
- **Playwright / Playwright CLI** — browser-level UI and end-to-end validation.
- **Security Review** — security analysis for proxy, uploads, secrets, PII, APIs, and adversarial inputs.
- **Superpowers / structured TDD workflow** — planning, test-driven development, debugging, and systematic implementation.

Do not allow a skill to override the original specification, `spec.md`, accepted decisions, or explicit user instructions.

### Project-local skills

Project-specific skills belong in:

`.claude/skills/<skill-name>/SKILL.md`

When a local skill exists:
1. Read its `SKILL.md` when relevant.
2. Use it only for its stated purpose.
3. Add it to the Skills section here.
4. Keep detailed instructions in the local skill file.

Keep local skills separate so this file remains concise.

## 14. Phase Completion Protocol

Before marking a phase complete:

1. All phase requirements in `spec.md` are implemented.
2. The implementation remains consistent with the original project specification.
3. All acceptance criteria pass.
4. The phase test gate passes.
5. Relevant security tests pass.
6. No unresolved release-blocking defect remains.
7. Documentation reflects the actual implementation.
8. `progress_log.md` contains completion evidence.
9. `state.md` points to the next phase/spec.
10. `decision.md` contains durable decisions made during the phase.

Never mark a phase complete merely because the code runs.

## 15. Session Handoff Protocol

At the end of every meaningful coding session:

### `progress_log.md`
Record what actually happened.

### `state.md`
Record:
- current phase
- completed work
- current blockers
- known defects
- exact next task

### `decision.md`
Update only for durable architectural/design decisions or conflict resolutions.

### `spec.md`
Update only when an implementation requirement, contract, acceptance criterion, or phase definition has explicitly changed.

### Original project specification
Do not modify it during ordinary development.

The goal is for another agent to continue by reading `state.md`, then the relevant `spec.md` section, while being able to return to the original specification whenever there is uncertainty.

## 16. Final Rule

**Do not guess when the project documentation can answer the question.**

Use:

```text
state.md
   ↓
spec.md
   ↓
decision.md
   ↓
testing.md
   ↓
If anything is unclear:
   ↓
Project 1 Spec — SentinelAI + Fraud Copilot.md
   ↓
existing implementation
   ↓
implement
   ↓
test
   ↓
update project memory
```

The agent's job is to implement the project faithfully, preserve consistency with the original specification, explicitly resolve genuine ambiguities, and leave enough project memory for the next development session to continue safely.
