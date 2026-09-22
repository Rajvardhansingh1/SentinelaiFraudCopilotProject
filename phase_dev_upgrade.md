# Phase 0
You are working on the existing Sentinel AI codebase.

Do NOT modify the application yet.

Your first task is to perform a complete technical audit of the existing project.

Understand what Sentinel AI currently does before proposing any expansion.

Inspect:

- repository structure
- frontend
- backend
- APIs
- database/storage
- authentication
- AI/model integrations
- security testing logic
- existing detection/evaluation logic
- configuration
- environment variables
- Docker/deployment
- tests
- CI/CD
- logging
- error handling
- dependencies
- README and documentation

Identify:

1. What functionality already exists.
2. What is production-ready vs prototype-level.
3. Current architecture and data flow.
4. Current AI/provider architecture.
5. Current security architecture.
6. Current secret-handling model.
7. Current testing coverage.
8. Technical debt.
9. Architectural bottlenecks.
10. Features that can be extended cleanly.
11. Features that require refactoring first.
12. Anything that should NOT be changed.

Do not implement anything.

Create:

docs/SENTINEL_CURRENT_STATE.md

Include:

- Executive summary
- Architecture
- Component map
- Data flow
- Existing features
- Existing APIs
- Existing model/provider integrations
- Storage/data model
- Security model
- Secret handling
- Test coverage
- Known technical debt
- Risks
- Recommended refactoring
- Recommended expansion points

Do not assume that features exist when they do not.

At the end, give me a concise summary of your findings.

Do not modify application code.

# Phase 1 : Stabilize the existing Sentinel
Now implement ONLY the stabilization work identified in the audit.

Do not add major new product functionality yet.

Goals:

1. Preserve all existing functionality.
2. Fix critical architectural problems that block expansion.
3. Establish reliable tests around existing behavior.
4. Improve error handling where necessary.
5. Establish clean boundaries between existing components.
6. Harden secret handling.
7. Remove obvious unsafe credential exposure.
8. Improve configuration handling.
9. Establish a reliable development/test workflow.

Before changing each subsystem:

- explain what you found
- explain why the change is necessary
- make the smallest safe change

After implementation:

- run the full existing test suite
- run lint/type checks
- run relevant security checks
- verify existing UI flows
- verify existing model functionality

Update the documentation.

Do not implement the future Sentinel expansion yet.

# Phase 2 : Provider abstraction + BYOK

Implement the model/provider abstraction for Sentinel AI.

IMPORTANT:
Build this on top of the existing model integration.
Do not rewrite unrelated Sentinel functionality.

Requirements:

1. Create a clean provider interface.
2. Decouple the security engine from provider-specific SDK code.
3. Preserve the existing provider behavior.
4. Add support for provider configuration through server-side configuration.
5. Support BYOK architecture.
6. Keep all API keys server-side.
7. Never expose provider credentials to the browser.
8. Never log credentials.
9. Never commit credentials.
10. Provide safe configuration errors when credentials are missing.

Design the abstraction so additional providers can be added without changing the core security engine.

Document:

- provider interface
- request/response abstraction
- credential handling
- error handling
- adding a new provider

Add tests for:

- valid provider configuration
- missing credentials
- invalid credentials
- provider errors
- provider timeout
- normal successful inference
- credential non-exposure

# Phase 3 : Build the Security Engine

Build the next Sentinel AI subsystem: a reusable security testing engine.

Do not build the entire future platform at once.

The engine should provide a common framework for:

- security test definitions
- test execution
- model interaction
- response evaluation
- finding generation
- severity
- evidence
- reproducibility
- test metadata

Separate:

TEST DEFINITION
→ EXECUTION
→ EVALUATION
→ FINDING
→ EVIDENCE

Do not hardcode individual attack types into the core engine.

Create an extensible test/plugin architecture.

Every security test should have:

- unique ID
- name
- category
- description
- severity
- attack/input
- expected behavior
- evaluation logic
- result
- evidence
- timestamp
- model/provider information
- reproducibility information

Add automated tests for the engine itself.

Do not yet implement every attack category.
Implement the framework and migrate the existing Sentinel tests into it without breaking them.


# Phase 4 — Attack library

Then:

Expand Sentinel's security test library using the new testing engine.

Implement attacks incrementally.

Start with:

1. Prompt injection
2. Jailbreak attempts
3. System prompt extraction
4. Sensitive information disclosure
5. Unsafe output behavior

For each category:

- implement multiple test cases
- provide deterministic evaluation where possible
- capture evidence
- assign severity according to documented rules
- make results reproducible
- add regression tests

Do not claim that a model is secure simply because tests pass.

The UI should distinguish:

PASS
FAIL
ERROR
NOT RUN
INCONCLUSIVE

Do not collapse these states into a single boolean.

That last part is particularly important for a security product.

# Phase 5 — Findings + Evidence

Then:

Build the Sentinel Findings subsystem on top of the existing security engine.

A finding must contain:

- finding ID
- test ID
- category
- severity
- title
- description
- affected target
- evidence
- reproduction information
- timestamp
- model/provider information
- status
- remediation guidance

Support finding states such as:

OPEN
ACKNOWLEDGED
RESOLVED
RETEST_REQUIRED

Do not delete historical security evidence when a finding is resolved.

Create a finding detail UI.

A user should be able to go from:

Finding
→ Test
→ Attack
→ Model response
→ Evidence
→ Reproduce

Add tests for the complete flow.

# Phase 6 — Security dashboard

Only after the underlying data exists:

Build the Sentinel security dashboard using real data from the existing backend.

Do not create fake/demo metrics.

Dashboard should show:

- total tests
- tests passed
- tests failed
- errors
- open findings
- severity distribution
- recent security activity
- affected models/applications
- security test history

Provide clear empty states when there is no data.

Provide loading states.

Provide error states.

Do not expose secrets or sensitive test payloads unnecessarily.

Preserve existing Sentinel UI functionality.

# Phase 7 — Regression testing

This is one of the most important expansions.

Add Sentinel security regression testing.

The system should allow a user to establish a security baseline.

A later test run should be compared against the baseline.

Detect:

- newly failing tests
- previously passing tests that now fail
- newly introduced findings
- resolved findings
- changed severity
- changed model/provider configuration

Display a clear regression report.

Do not define "security score" as the sole source of truth.

The underlying individual test results must remain accessible.

Add tests for:

- baseline creation
- comparison
- regression detection
- resolved vulnerabilities
- unchanged results
- test additions/removals

# Phase 8 — CI/CD

Add Sentinel CI/CD support.

Create a developer-friendly CLI/API workflow for running security tests automatically.

The CI workflow should support:

- selecting a target
- selecting a test suite
- executing tests
- generating machine-readable results
- generating human-readable results
- configurable failure thresholds
- detecting security regressions

A CI job must fail only according to explicitly configured policy.

Do not hardcode arbitrary thresholds.

Document GitHub Actions integration.

Do not require users to expose provider API keys in source code.

# Phase 9 — Agent security

This is where I'd expand Sentinel beyond basic LLM testing.

Add an agent security subsystem.

Model an AI agent as:

Agent
├── Model
├── Tools
├── Permissions
├── Data sources
└── Actions

Implement an explicit tool/permission model.

Support policies such as:

ALLOW
DENY
REQUIRE_APPROVAL

Track:

- agent
- tool
- requested action
- policy decision
- execution result

Do not implement actual destructive actions as part of testing.

Build the policy/evaluation layer first.

Add tests for:

- authorized tool use
- unauthorized tool use
- denied action
- approval-required action
- policy bypass attempts

# Phase 10 — Runtime Gateway

Don't build this early.

It's a much bigger architectural step.

Eventually:

Application
     ↓
Sentinel Gateway
     ↓
Model / Agent

Then give the agent:

Implement the Sentinel Runtime Gateway as a separate subsystem.

Do not tightly couple gateway functionality to the existing dashboard.

The gateway must support:

- request inspection
- response inspection
- policy evaluation
- allow/block decisions
- logging
- audit events
- provider routing

Keep the gateway stateless where practical.

Do not store raw sensitive content unless explicitly configured.

Never log API keys, authentication tokens, or secrets.

Create integration tests covering:

request
→ inspection
→ policy
→ provider
→ response
→ response policy
→ final decision

# Phase 11 — Monitoring

Add continuous Sentinel monitoring.

Track security events such as:

- attack attempts
- blocked requests
- policy violations
- new findings
- regressions
- suspicious tool activity

Create an event model separate from findings.

Do not treat every event as a vulnerability.

Provide filtering by:

- time
- severity
- application
- model
- category
- event type

Add retention/configuration controls.

# Phase 12 — Reports

Finally:

Build Sentinel security reporting.

Generate an executive-level report and a technical report.

Executive report:

- assessment scope
- testing period
- key findings
- severity distribution
- major changes
- remediation status

Technical report:

- test cases
- attack inputs
- results
- evidence
- model/provider
- timestamps
- reproducibility information
- remediation guidance

Reports must be generated from actual stored Sentinel data.

Do not fabricate metrics or findings.

Ensure sensitive credentials and secrets can never appear in reports.