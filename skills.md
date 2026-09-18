# Recommended Skills — SentinelAI + Fraud Copilot

This file is a registry, not a replacement for `CLAUDE.md`.

## Global skills

### 1. Ponytail
**Use for:** smaller, simpler, lower-token code changes.

Keep enabled globally if already installed.

### 2. Caveman
**Use for:** concise agent communication and reduced unnecessary output.

Do not let terseness remove required test/implementation work.

### 3. Anthropic Frontend Design
**Use for:** designing/refining the Streamlit-facing product experience and avoiding generic AI-generated UI.

Suggested install:
```text
npx skills add anthropics/skills@frontend-design
```

### 4. UI/UX Pro Max
**Use for:** design-system decisions, dashboard visual hierarchy, charts, accessibility, and interactive states.

Suggested install:
```text
npx ui-ux-pro-max-cli init --ai claude
```

### 5. Playwright
**Use for:** browser-level testing and interactive UI validation.

Official Playwright CLI skill installation:
```text
playwright-cli install --skills -g
```

### 6. Security Review
**Use for:** proxy endpoints, file uploads, secrets, PII, third-party APIs, adversarial inputs, deployment.

Prefer a security-review skill that actually examines the relevant source/dependencies rather than treating the skill name as a guarantee.

### 7. Superpowers / structured engineering workflow
**Use for:** brainstorming, planning, TDD, systematic debugging, code review, and phase execution.

This is especially useful for large phase changes; it should not override `spec.md`.

## Project-local skills

Potential local skills to create later:

- `sentinelai-guardrail-contracts`
- `fraud-agent-contracts`
- `evaluation-methodology`
- `streamlit-review-ui`
- `synthetic-receipt-generation`

Do not create these until repeated project-specific instructions justify them.

## Skill governance

Before installing third-party agent skills:
1. Inspect the repository.
2. Read its `SKILL.md`.
3. Check what commands/scripts it can execute.
4. Prefer well-maintained/openly documented projects.
5. Run a security review for skills that can execute code or modify files.
6. Record important adopted skills in `CLAUDE.md`.
