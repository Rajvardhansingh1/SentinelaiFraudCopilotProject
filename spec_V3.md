# Sentinel AI — V3 Development Specification

## Document Purpose

This document defines the V3 development specification for the **existing Sentinel AI project**.

Sentinel AI has already been developed through the previous version. The functionality currently present in the repository is the baseline for V3.

**V3 is an upgrade of the existing product, not a greenfield rewrite.**

The coding agent must inspect and understand the existing implementation before making changes and must preserve existing working functionality unless a change is explicitly required by this specification.

---

# 1. Core Development Principle

Sentinel AI V3 must be developed **over the existing codebase**.

Do not:

* rebuild Sentinel from scratch
* replace working systems without justification
* remove existing features
* create a parallel implementation of functionality that already exists
* change architecture merely for stylistic reasons
* introduce unnecessary dependencies
* silently change public APIs
* silently change database schemas in destructive ways
* silently change authentication or authorization behavior
* automatically modify user projects

The existing Sentinel implementation is the source of truth.

Before implementing a V3 feature:

1. Inspect the existing implementation.
2. Identify what already exists.
3. Reuse existing components where appropriate.
4. Determine what must be extended.
5. Determine what must be refactored.
6. Preserve backward compatibility wherever practical.
7. Implement incrementally.
8. Test the existing functionality.
9. Test the new functionality.
10. Update documentation.

All rules in `CLAUDE.md` remain authoritative and apply to every instruction in this document.

---

# 2. V3 Product Definition

Sentinel AI V3 is an AI security assessment, monitoring, analysis, remediation-recommendation, and reporting platform.

The product should allow a user to:

* create an account
* log in
* create multiple projects
* test multiple AI models, applications, agents, APIs, and services
* connect projects through SDK/API/CLI/integrations
* use BYOK or Sentinel-managed inference where supported
* run security assessments
* identify vulnerabilities and suspicious behavior
* inspect evidence
* understand the likely cause and impact
* receive project-specific recommended solutions
* view findings centrally
* track findings over time
* retest after implementing fixes
* compare previous and current results
* generate security reports
* use Sentinel from local development environments
* use Sentinel in CI/CD
* connect APIs and other services
* optionally use a local-only execution mode where supported

The core user workflow is:

```text
CONNECT
   ↓
ASSESS
   ↓
DETECT
   ↓
ANALYZE
   ↓
EXPLAIN
   ↓
RECOMMEND
   ↓
REPORT
   ↓
USER IMPLEMENTS FIX
   ↓
RETEST
   ↓
VERIFY
```

Sentinel does not autonomously modify the user's project.

---

# 3. V3 Non-Goals

The following are explicitly outside the scope of Sentinel's autonomous behavior.

Sentinel must NOT:

* automatically modify source code
* automatically apply patches
* automatically edit configuration
* automatically change infrastructure
* automatically deploy changes
* automatically commit code
* automatically push code to Git repositories
* automatically change production systems
* claim that a vulnerability has been fixed without verification

Sentinel provides recommendations.

The user decides whether and how to implement those recommendations.

---

# 4. Existing Functionality Is Protected

Before starting V3 work, identify all functionality currently available in the repository.

Create a baseline inventory if one does not already exist.

The inventory should cover:

* authentication
* dashboard
* existing navigation
* existing AI/security tests
* model integrations
* provider handling
* BYOK functionality
* managed inference functionality
* findings
* evidence
* reports
* project handling
* API
* SDK
* CLI
* database/storage
* local execution
* cloud functionality
* existing integrations
* existing tests

V3 must preserve these capabilities.

If an existing feature must change because of V3 architecture, document:

* current behavior
* required new behavior
* reason for change
* migration approach
* backward compatibility considerations
* tests covering the change

---

# 5. V3 Architecture

The V3 architecture should maintain a clear distinction between:

```text
                    SENTINEL AI
                         │
              ┌──────────┴──────────┐
              │                     │
        CONTROL PLANE          EXECUTION PLANE
              │                     │
       Web Dashboard          Local SDK / CLI
       Authentication         CI/CD
       Projects               API
       Findings               Gateway
       Reports                Workers
       Configuration          Security Engine
              │                     │
              └──────────┬──────────┘
                         │
                    Sentinel API
                         │
                    Data / Events
```

The exact implementation should follow the existing codebase where practical.

Do not force a specific folder structure if the current architecture already provides clean equivalent boundaries.

---

# 6. Central Control Plane

The Sentinel web dashboard should act as the central control plane.

The primary user experience should not depend exclusively on a local dashboard.

The control plane should provide access to:

* account
* workspace
* projects
* targets
* test runs
* findings
* remediation recommendations
* evidence
* reports
* integrations
* API credentials
* project configuration
* monitoring data
* security history

The dashboard should be reachable independently of where the security test was executed.

For example:

```text
Local SDK
    ↓
Sentinel API
    ↓
Project
    ↓
Dashboard
```

and:

```text
CI/CD
    ↓
Sentinel API
    ↓
Project
    ↓
Dashboard
```

and:

```text
Application / API
    ↓
Sentinel API
    ↓
Project
    ↓
Dashboard
```

---

# 7. Authentication

V3 must provide a proper authenticated user experience.

Users should be able to:

* sign up
* sign in
* sign out
* recover/reset credentials where supported
* maintain a session
* access only authorized projects
* manage account settings

The existing authentication implementation should be reused if it is already sound.

Do not replace authentication simply to introduce a different library.

Authentication credentials must never be exposed to client-side logs or stored insecurely.

---

# 8. User → Workspace → Project Model

One user must be able to manage multiple independent Sentinel projects.

The conceptual hierarchy is:

```text
User
 │
 └── Workspace
      │
      ├── Project A
      │    ├── Targets
      │    ├── Test Runs
      │    ├── Findings
      │    ├── Events
      │    └── Reports
      │
      ├── Project B
      │    ├── Targets
      │    ├── Test Runs
      │    ├── Findings
      │    └── Reports
      │
      └── Project C
           ├── Targets
           ├── Test Runs
           ├── Findings
           └── Reports
```

A project represents an AI application, model, agent, API, service, or other logical security-assessment target.

Users should not need separate accounts for separate AI systems.

---

# 9. Project Isolation

Project data must be isolated.

A user must only be able to access projects for which they have authorization.

Project-level data includes:

* project metadata
* targets
* test runs
* findings
* evidence
* reports
* events
* project credentials
* integrations
* configuration

A request for Project A must never return Project B data.

Add authorization tests specifically for cross-project access attempts.

---

# 10. Project Creation

A new user should be able to create a project through a simple onboarding flow.

Example:

```text
Create your first project

Project name:
[ Customer Support Agent ]

What are you testing?

○ AI Model
○ AI Application
○ AI Agent
○ API / Service
```

The user should not be required to understand Sentinel's internal architecture.

Advanced configuration can happen later.

---

# 11. First-Time User Experience

The first-time experience should guide the user toward a successful first security assessment.

Preferred flow:

```text
Sign Up
   ↓
Create Project
   ↓
Choose Target Type
   ↓
Connect Target
   ↓
Choose Inference / Provider
   ↓
Choose Security Assessment
   ↓
Run Assessment
   ↓
View Findings
   ↓
View Recommended Solutions
```

The first successful assessment should require as little configuration as reasonably possible.

---

# 12. BYOK and Managed Inference

Preserve and improve the existing provider abstraction.

Where supported, users should have two options:

```text
Use my API key
        OR
Use Sentinel-managed inference
```

### BYOK

The user's provider credential must:

* remain server-side
* never be exposed in frontend code
* never be included in reports
* never be logged
* never be committed
* never appear in error messages
* only be accessible to the authorized execution path

### Sentinel-managed inference

The user should be able to perform supported Sentinel operations without supplying their own provider key.

The actual managed-provider implementation should follow the existing V3 infrastructure.

Do not hardcode managed credentials.

---

# 13. Provider Abstraction

The security engine must remain provider-agnostic.

Conceptually:

```text
Security Engine
      ↓
Provider Interface
      ↓
┌──────────────┬──────────────┬──────────────┐
│ Provider A   │ Provider B   │ Provider C   │
└──────────────┴──────────────┴──────────────┘
```

Provider-specific code should not leak throughout the security engine.

Adding another provider should require minimal changes to the core testing system.

---

# 14. Target Model

V3 should support a consistent concept of a security target.

A target may represent:

* model
* chatbot
* AI application
* agent
* API
* service
* connected runtime

The existing target model should be reused where possible.

Each target should have enough metadata to identify:

* project
* target type
* name
* environment
* provider/model where applicable
* configuration
* connection method
* status
* creation/update information

---

# 15. Security Assessment Engine

The existing security engine must remain the foundation.

V3 should continue to separate:

```text
TEST DEFINITION
      ↓
EXECUTION
      ↓
EVALUATION
      ↓
FINDING
      ↓
EVIDENCE
      ↓
REMEDIATION RECOMMENDATION
```

Do not collapse these concepts into a single result object if doing so would reduce traceability.

Every test execution should be reproducible where technically possible.

---

# 16. Test Result States

Security tests must distinguish:

```text
PASS
FAIL
ERROR
NOT_RUN
INCONCLUSIVE
```

Do not represent all non-pass states as vulnerabilities.

For example:

* `FAIL` means the tested security condition failed.
* `ERROR` means the test could not be reliably evaluated.
* `INCONCLUSIVE` means evidence was insufficient.
* `NOT_RUN` means the test was not executed.

The dashboard must represent these states accurately.

---

# 17. Findings

A finding should contain, where available:

* unique ID
* project
* target
* test ID
* category
* title
* severity
* status
* description
* evidence
* attack/input
* observed response
* impact
* likely root cause
* affected component
* affected file/path where confidently identifiable
* remediation recommendation
* remediation rationale
* timestamp
* model/provider information
* assessment/run ID

Findings must remain traceable to the test execution that generated them.

---

# 18. Finding Status

Support clear finding states.

At minimum:

```text
OPEN
IN_PROGRESS
RESOLVED
ACCEPTED_RISK
```

A finding should not automatically become `RESOLVED` merely because the user viewed the recommendation.

Resolution should be based on a subsequent verification/retest or an explicit user action such as accepting the risk.

---

# 19. Evidence

Every meaningful security finding should provide evidence.

Evidence may include:

* attack input
* model response
* tool interaction
* relevant event
* evaluation output
* timestamps
* target metadata
* test configuration

Sensitive content must be handled according to project security and privacy configuration.

Do not expose credentials or unrelated sensitive information in evidence.

---

# 20. Project-Aware Analysis

One of the main V3 goals is for Sentinel's remediation recommendations to understand the project context.

Where Sentinel has authorized access to relevant project information, it should use:

* project architecture
* target configuration
* framework
* model/provider
* agent structure
* tool definitions
* relevant APIs
* relevant configuration
* security controls
* relevant source-code context

to produce more specific recommendations.

Do not invent project details.

If Sentinel cannot verify a project detail, clearly indicate that it is uncertain.

---

# 21. Remediation Recommendations

Remediation is a core Sentinel feature.

Sentinel should not stop at:

> Vulnerability detected.

It should provide:

> Vulnerability detected + expected remediation based on the project context.

For each finding, where possible provide:

1. What Sentinel detected.
2. Evidence.
3. Security impact.
4. Likely root cause.
5. Expected remediation.
6. Why the remediation addresses the issue.
7. Relevant project components to review.
8. Additional recommended controls.
9. Verification/retest guidance.

---

# 22. Remediation Must Be Recommendations Only

Sentinel must NOT autonomously implement the recommended solution.

It must not:

* edit source code
* generate and apply patches
* modify project configuration
* commit code
* push code
* deploy changes
* change production systems

The user remains responsible for reviewing and implementing recommendations.

---

# 23. Distinguish Facts from Recommendations

Sentinel's output must clearly distinguish:

### Observed

What Sentinel actually observed.

### Analysis

What the evidence indicates.

### Recommendation

What Sentinel recommends changing.

For example:

```text
Observed:
The agent executed a tool after receiving attacker-controlled instructions.

Analysis:
The tool authorization decision appears to rely on model-controlled behavior.

Recommendation:
Move authorization for sensitive tool actions into an application-side
authorization layer.
```

Do not present inferred information as confirmed fact.

---

# 24. Confidence

Where useful, remediation recommendations should communicate confidence.

Possible categories:

```text
HIGH CONFIDENCE
LIKELY
REQUIRES INVESTIGATION
INSUFFICIENT EVIDENCE
```

Do not generate false certainty.

If Sentinel cannot confidently determine the root cause, say so and provide an investigation path.

---

# 25. Recommended Solutions Must Be Project-Specific

Avoid generic remediation whenever project context allows a more specific recommendation.

Instead of:

> Add authentication.

Prefer:

> The `/api/query` endpoint currently accepts requests without an observed authorization check. Review the API authentication middleware and ensure authenticated identity is enforced before the agent is invoked.

Only mention a specific file/component when Sentinel can confidently identify it.

---

# 26. Dashboard

The dashboard is the primary user-facing control plane.

At minimum, provide:

```text
Dashboard
Projects
Targets
Security Tests
Test Runs
Findings
Remediation
Monitoring
Reports
Integrations
Settings
```

The exact navigation should follow the existing UI where possible.

---

# 27. Dashboard Overview

A project dashboard should show real project data.

Example:

```text
Project: Customer Support Agent

Security Overview

Tests                 438
Passed                412
Failed                 21
Inconclusive             5

Open Findings           8

Critical                1
High                    3
Medium                  4
```

Also provide:

* recent test runs
* recent findings
* unresolved vulnerabilities
* recent regressions
* recent activity

Do not create fake metrics.

---

# 28. Finding Detail UI

A finding page should make the entire lifecycle understandable.

Recommended structure:

```text
Finding

Severity
Status

What Sentinel Found

Evidence

Why This Matters

Likely Cause

Affected Component

Recommended Solution

Why This Solution

Additional Recommendations

Verification / Retest

History
```

The user should not need to inspect raw logs to understand the finding.

Advanced evidence should still be accessible.

---

# 29. Remediation Center

Create a centralized view for remediation work.

Example:

```text
Remediation

Open Findings: 8

Critical
1

High
3

Medium
4
```

Allow filtering by:

* severity
* status
* project
* target
* category
* date

Each finding should show its recommended solution.

---

# 30. Retesting

After the user implements a recommendation outside Sentinel, they should be able to run the relevant test again.

The system should compare:

```text
Previous Result
      ↓
Current Result
      ↓
Comparison
```

Possible outcomes:

```text
RESOLVED
STILL DETECTED
CHANGED
INCONCLUSIVE
ERROR
```

Never mark a vulnerability as fixed without evidence.

---

# 31. Regression Detection

Sentinel should compare security assessments over time.

Detect:

* newly failing tests
* previously passing tests that now fail
* new findings
* resolved findings
* severity changes
* changed target configuration
* changed model/provider configuration

The user should be able to see:

```text
Previous Assessment
        ↓
Current Assessment
        ↓
Security Changes
```

---

# 32. Test History

Each project should maintain historical test runs.

Example:

```text
Test Runs

Sep 23   Production Assessment    438 tests
Sep 22   Pre-deployment           438 tests
Sep 21   Development               412 tests
Sep 20   Baseline                  400 tests
```

Opening a test run should expose:

* tests executed
* results
* findings
* configuration
* provider/model
* timestamp
* source of execution

---

# 33. Execution Sources

The central project should be able to receive results from different execution sources.

At minimum conceptually support:

```text
LOCAL SDK
CLI
API
CI/CD
GATEWAY
OTHER INTEGRATIONS
```

The source of every test run should be recorded.

Example:

```text
Source: LOCAL_SDK
Source: CI
Source: API
Source: GATEWAY
```

---

# 34. SDK / CLI

The SDK/CLI should connect a local project to a Sentinel project.

The expected workflow is:

```text
sentinel init
       ↓
Authenticate / connect
       ↓
Select Sentinel project
       ↓
Associate local project
       ↓
sentinel test
       ↓
Results synchronized with Sentinel
```

The exact command names should follow the existing SDK/CLI implementation.

Do not break existing commands.

---

# 35. Project Credentials

Local applications, CI jobs, and services must not use the user's login password to communicate with Sentinel.

Use scoped project/application credentials where appropriate.

Credentials should support:

* creation
* revocation
* rotation
* secure storage
* appropriate scope

Never display full secrets after their initial secure creation unless the existing architecture explicitly supports a secure mechanism.

---

# 36. API Integration

Sentinel should provide an API through which authorized integrations can submit or retrieve project data as supported.

The API must enforce:

* authentication
* authorization
* project isolation
* input validation
* rate limiting where appropriate
* audit logging
* secure error handling

Never expose another project's data.

---

# 37. CI/CD Integration

Support automated Sentinel testing in CI/CD.

Conceptually:

```text
GitHub / CI
    ↓
Sentinel Security Tests
    ↓
Results
    ↓
Sentinel Project
```

The CI integration should support:

* selecting project
* selecting test suite
* executing tests
* reporting results
* detecting regressions
* configurable pass/fail policies

Do not hardcode arbitrary security thresholds.

---

# 38. Local-Only Mode

Where supported, Sentinel should offer a local-only execution mode for users who do not want assessment data synchronized with Sentinel Cloud.

Conceptually:

```text
Application
    ↓
Local Sentinel Engine
    ↓
Local Storage
    ↓
Local Dashboard
```

The UI must make it clear whether the user is operating in:

```text
Cloud-connected mode
```

or:

```text
Local-only mode
```

Do not imply that local-only results are available in the cloud dashboard unless they have actually been synchronized.

---

# 39. Cloud-Connected Mode

In cloud-connected mode:

```text
Local / CI / API / Gateway
          ↓
      Sentinel API
          ↓
         Project
          ↓
       Dashboard
```

The dashboard should be able to show results independently of where the test was executed.

---

# 40. Reports

Reports are a major V3 deliverable.

A project report should include:

### Executive Summary

* project
* assessment period
* assessment scope
* number of tests
* result distribution
* open findings
* major security observations

### Findings

For every relevant finding:

* title
* severity
* evidence
* impact
* likely cause
* affected component
* recommended solution
* remediation rationale
* status

### Test Results

* test suites
* test counts
* pass/fail/error/inconclusive
* test configuration

### Regression

* newly introduced issues
* resolved issues
* changed findings

### Recommended Remediation Plan

Prioritized remediation recommendations based on the actual findings.

Reports must use actual stored project data.

Never fabricate metrics.

---

# 41. Report Formats

Support the formats already used by the existing application.

Where V3 adds new formats, implement them incrementally.

Potential formats include:

* web report
* PDF
* machine-readable JSON
* CSV where appropriate

Do not expose credentials or secrets in any report format.

---

# 42. Report Scope

Allow reports to be scoped appropriately.

Examples:

```text
Entire Project
Single Target
Single Assessment
Finding Set
Date Range
```

The exact options should depend on the existing data model.

---

# 43. Security Monitoring

Where runtime/event monitoring already exists or is being expanded, distinguish:

```text
EVENT
TEST RESULT
FINDING
```

These are not interchangeable.

An event does not automatically mean a vulnerability.

A finding should be generated according to the project's established evaluation logic.

---

# 44. Audit Trail

Important user/project actions should be auditable.

Examples:

* project created
* project configuration changed
* credential created
* credential revoked
* assessment started
* assessment completed
* finding status changed
* report generated
* integration connected
* integration disconnected

Do not log secrets.

---

# 45. Privacy and Data Minimization

Sentinel may process sensitive AI inputs and outputs.

The implementation should minimize stored content where possible.

Support clear configuration around:

* retention
* sensitive evidence
* logs
* project data
* assessment history

Never store secrets unnecessarily.

Never include secrets in:

* logs
* reports
* analytics
* error messages
* frontend state

---

# 46. Security Requirements

V3 must receive a security review before being considered complete.

Review at minimum:

* authentication
* authorization
* project isolation
* secret handling
* API security
* session management
* CSRF where applicable
* XSS
* injection risks
* SSRF where applicable
* file upload security where applicable
* dependency vulnerabilities
* logging
* sensitive-data exposure
* rate limiting
* abuse prevention
* tenant isolation

---

# 47. AI Security of Sentinel Itself

Sentinel is itself an AI-enabled security product.

Do not assume that Sentinel's AI-generated analysis is automatically trustworthy.

AI-generated recommendations must be treated as recommendations.

The system must preserve the underlying evidence so users can understand why the recommendation was produced.

Do not allow model-generated content to override:

* authentication
* authorization
* project isolation
* credential protection
* security policies

---

# 48. Error Handling

Errors must be understandable and safe.

Do not expose:

* stack traces containing secrets
* provider credentials
* internal tokens
* database credentials
* sensitive infrastructure information

The UI should distinguish:

```text
Authentication Error
Configuration Error
Provider Error
Test Error
Network Error
Permission Error
Internal Error
```

where practical.

---

# 49. Observability

V3 should provide sufficient logging and metrics to diagnose failures without exposing sensitive information.

Track operationally useful information such as:

* request IDs
* project IDs where safe
* test run IDs
* execution duration
* provider failures
* worker failures
* API errors

Do not log raw secrets.

Avoid logging raw user prompts/responses unless explicitly required and permitted by the project's privacy model.

---

# 50. Performance

Do not make the dashboard dependent on long-running security scans completing synchronously.

Where the existing architecture supports asynchronous execution:

```text
Start Assessment
       ↓
Create Job
       ↓
Worker
       ↓
Execute Tests
       ↓
Store Results
       ↓
Dashboard Updates
```

The UI should show meaningful progress.

---

# 51. Background Jobs

Long-running work should use the existing job/worker infrastructure where available.

Potential background jobs:

* security assessments
* report generation
* large test suites
* regression comparisons
* monitoring aggregation

Do not create a new worker architecture if the current application already provides a suitable one.

---

# 52. Frontend UX Principles

V3 should be:

* clear
* professional
* security-focused
* understandable to new users
* useful to technical users
* responsive
* accessible

New users should not need to understand Sentinel's internal architecture.

Advanced configuration should be progressively disclosed.

Always provide:

* loading states
* empty states
* error states
* success states
* confirmation where appropriate

---

# 53. Dashboard Information Hierarchy

The most important information should be visible first:

```text
Project
 ↓
Security posture
 ↓
Open findings
 ↓
Critical/high issues
 ↓
Recommended solutions
 ↓
Recent assessments
 ↓
Detailed evidence
```

Do not bury important unresolved vulnerabilities under technical configuration.

---

# 54. Project Switching

Users with multiple projects must be able to switch projects easily.

The active project must be clearly visible.

Example:

```text
Sentinel

[ Customer Support Agent ▼ ]

Dashboard
Findings
Tests
Reports
...
```

Changing the active project must update all project-scoped data.

Never accidentally display data from the previous project.

---

# 55. New Project Experience

Provide a simple:

```text
+ New Project
```

flow.

The project creation process should not require advanced security configuration.

Advanced integrations can be configured after project creation.

---

# 56. Integration Management

A project should have a clear integrations section.

Potential integrations include:

* SDK
* CLI
* API
* CI/CD
* Gateway
* other supported services

Each integration should display:

* connection status
* configuration status
* credential status where appropriate
* setup instructions
* revoke/disconnect option

---

# 57. Secrets and Credentials

Follow the existing project's secure secret-handling implementation.

At minimum:

```text
.env
```

must never be committed.

Only safe example configuration belongs in:

```text
.env.example
```

The coding agent must never place real credentials into:

* source code
* tests
* fixtures
* documentation
* screenshots
* reports
* commits

---

# 58. Testing Requirements

Every V3 subsystem must have automated tests.

At minimum test:

### Authentication

* signup
* login
* logout
* unauthorized access
* session expiration where applicable

### Authorization

* authorized project access
* unauthorized project access
* cross-project access attempt

### Projects

* create
* update
* access
* switch
* delete/archive where supported

### Security engine

* execution
* evaluation
* result states
* findings

### Remediation

* recommendation generation
* project context
* uncertainty handling
* no automatic code modification

### Retesting

* previous result
* new result
* comparison
* resolution

### Reports

* correct data
* correct scope
* no secret leakage

### API

* authentication
* authorization
* validation
* project isolation

### SDK/CLI

* authentication
* project association
* test execution
* result synchronization

---

# 59. Security Regression Tests

V3 must include tests specifically designed to prevent regressions in security boundaries.

At minimum:

```text
User A cannot access User B's project.

Project A credentials cannot access Project B.

Frontend cannot retrieve server-side provider secrets.

Reports cannot contain provider API keys.

Logs cannot contain provider API keys.

Unauthorized API requests cannot access project data.

Model-generated content cannot override authorization.

Finding recommendations cannot trigger code modification.
```

---

# 60. No Fake Data in Production Features

Do not implement dashboard metrics using hardcoded values.

Do not fabricate:

* findings
* test counts
* severity counts
* reports
* test results
* monitoring events

If there is no data, show an appropriate empty state.

---

# 61. Backward Compatibility

Existing users and existing local projects should continue to work wherever practical.

If a migration is necessary:

1. detect existing data
2. migrate safely
3. preserve historical results
4. validate migration
5. provide rollback/recovery where practical

Do not silently discard historical security data.

---

# 62. Database Changes

Before modifying the schema:

* inspect the existing schema
* understand relationships
* identify existing production assumptions
* create migrations
* preserve existing data
* add indexes where appropriate
* test migration paths

Do not drop existing tables or fields simply to simplify development.

---

# 63. API Compatibility

Do not silently break existing API contracts.

If an API must change:

* document the change
* preserve compatibility where practical
* version the API where appropriate
* add migration guidance
* update tests

---

# 64. Documentation

Update documentation whenever V3 changes user-visible behavior.

At minimum maintain:

```text
README.md
docs/ARCHITECTURE.md
docs/SECURITY.md
docs/API.md
docs/PROVIDERS.md
docs/TESTING.md
```

Only create files that are appropriate to the existing project.

Documentation must not contain real credentials.

---

# 65. Development Process

The coding agent must work incrementally.

For every significant V3 feature:

```text
INSPECT
   ↓
PLAN
   ↓
IMPLEMENT
   ↓
TEST
   ↓
SECURITY REVIEW
   ↓
VERIFY EXISTING FUNCTIONALITY
   ↓
DOCUMENT
```

Do not implement unrelated features in the same change.

---

# 66. Active Phase Control

This specification contains the complete V3 roadmap.

The coding agent must work only on the currently active phase.

At the top of this document, maintain:

```md
## ACTIVE PHASE

Phase 1 — V3 Baseline and Architecture Verification
```

The user will change the active phase when ready.

The coding agent must NOT automatically continue into future phases.

---

# 67. V3 Development Phases

## Phase 1 — Existing V3 Baseline Verification

Goal:

Understand exactly what has already been implemented before making V3 changes.

Tasks:

* inspect repository
* inspect architecture
* inspect database
* inspect authentication
* inspect project model
* inspect dashboard
* inspect security engine
* inspect findings
* inspect remediation
* inspect reports
* inspect API
* inspect SDK/CLI
* inspect provider integrations
* inspect tests

Create or update:

```text
docs/SENTINEL_V3_BASELINE.md
```

Do not modify application behavior unless required to fix a clearly identified V3 blocker.

Acceptance:

* existing functionality documented
* architecture understood
* tests run
* known gaps identified

---

# Phase 2 — Control Plane and Multi-Project Verification

Goal:

Ensure one authenticated user can securely manage multiple projects.

Tasks:

* verify authentication
* verify workspace/project relationship
* verify project isolation
* verify project switching
* verify project creation
* verify project-scoped navigation
* verify project-scoped API access
* verify project-scoped findings
* verify project-scoped reports

Acceptance:

* one user can manage multiple projects
* project data cannot leak between projects
* active project is always clear
* existing users remain functional

---

# Phase 3 — Target and Integration Model

Goal:

Make projects capable of representing different AI systems and execution sources.

Support where appropriate:

```text
Model
Application
Agent
API
Service
```

And execution sources:

```text
Local SDK
CLI
API
CI/CD
Gateway
```

Acceptance:

* target identity is clear
* execution source is recorded
* results remain associated with the correct project and target

---

# Phase 4 — Centralized Execution and Result Synchronization

Goal:

Ensure tests executed outside the dashboard can report into the central Sentinel project.

Support the existing architecture for:

```text
Local SDK
      ↓
Sentinel API
      ↓
Project
      ↓
Dashboard
```

and equivalent flows for CI/CD/API/integrations.

Acceptance:

* external test run appears in correct project
* historical result is retained
* source is identified
* unauthorized submissions are rejected

---

# Phase 5 — Remediation Intelligence

Goal:

Improve project-aware remediation recommendations.

For each finding, produce where possible:

* expected fix
* rationale
* affected component
* relevant file/path
* additional controls
* confidence

Recommendations must be grounded in available project evidence.

Do not allow Sentinel to modify the project.

Acceptance:

* recommendations are tied to actual findings
* recommendations distinguish facts from inference
* recommendations do not claim certainty without evidence
* no automatic source modification exists

---

# Phase 6 — Finding and Remediation Experience

Goal:

Make remediation easy to understand from the dashboard.

Implement/refine:

* findings list
* finding detail
* remediation center
* filtering
* status
* evidence
* recommended solutions
* retest entry point
* finding history

Acceptance:

A user can go from:

```text
Finding
→ Evidence
→ Recommended Solution
→ Retest
```

without leaving the Sentinel dashboard.

---

# Phase 7 — Retesting and Regression

Goal:

Allow users to verify whether implemented fixes actually work.

Implement/refine:

* retest
* before/after comparison
* regression detection
* finding resolution
* historical results

Acceptance:

Sentinel never marks a vulnerability as fixed without an appropriate verification result or explicit risk acceptance.

---

# Phase 8 — SDK / CLI / CI Integration

Goal:

Make Sentinel useful throughout development workflows.

Verify/refine:

* project initialization
* authentication
* project association
* security test execution
* result synchronization
* CI execution
* machine-readable output
* regression-aware CI status

Acceptance:

A developer can run Sentinel from their development environment or CI and see the resulting assessment in the appropriate project dashboard.

---

# Phase 9 — API and Service Integrations

Goal:

Allow APIs and other supported services to report into Sentinel.

Implement/refine:

* scoped credentials
* API authentication
* project authorization
* result ingestion
* event ingestion where appropriate
* audit logging
* rate limiting
* validation

Acceptance:

API-generated results appear in the correct project and are visible through the dashboard and reports.

---

# Phase 10 — Reporting

Goal:

Turn Sentinel data into professional security reports.

Implement/refine:

* project report
* assessment report
* finding report
* remediation section
* regression section
* executive summary
* technical details

Acceptance:

Reports contain only actual Sentinel data and never expose secrets.

---

# Phase 11 — Monitoring and Security History

Goal:

Provide meaningful historical visibility.

Implement/refine:

* security activity
* test history
* findings history
* regressions
* trends where meaningful
* filtering

Do not create misleading security scores.

Prefer transparent underlying measurements.

---

# Phase 12 — Production Security and Hardening

Goal:

Prepare V3 for real-world use.

Perform a complete review of:

* authentication
* authorization
* tenant/project isolation
* secret management
* API security
* session handling
* input validation
* dependency security
* logging
* privacy
* rate limiting
* error handling
* abuse scenarios
* data retention
* report security
* SDK credential security

Run automated and manual security tests.

---

# Phase 13 — Final V3 Product Validation

Perform a complete end-to-end validation using a clean user journey.

Test:

```text
New User
   ↓
Sign Up
   ↓
Login
   ↓
Create Project
   ↓
Connect Target
   ↓
Choose Provider
   ↓
Run Assessment
   ↓
Findings
   ↓
Recommended Solutions
   ↓
Generate Report
   ↓
User Implements Fix
   ↓
Retest
   ↓
Regression Comparison
   ↓
Resolved Finding
```

Then test:

```text
Second Project
```

to ensure project isolation.

Then test:

```text
Local SDK
CI/CD
API
```

to ensure external execution results reach the correct project.

---

# 68. V3 Acceptance Criteria

V3 should not be considered complete until all of the following are true.

## User

* [ ] User can create an account.
* [ ] User can log in.
* [ ] User can maintain a secure session.
* [ ] User can access authorized projects only.

## Projects

* [ ] One user can manage multiple projects.
* [ ] Projects are isolated.
* [ ] User can switch projects.
* [ ] Project data is scoped correctly.

## Testing

* [ ] Existing security tests continue to work.
* [ ] New tests use the existing security engine.
* [ ] Results are reproducible where possible.
* [ ] Test states are correctly represented.

## Findings

* [ ] Findings contain evidence.
* [ ] Findings are traceable to tests.
* [ ] Findings have status.
* [ ] Findings have severity.
* [ ] Findings provide remediation where possible.

## Remediation

* [ ] Recommendations use project context.
* [ ] Recommendations distinguish facts from inference.
* [ ] Recommendations explain expected fixes.
* [ ] Sentinel does not modify user code.
* [ ] Sentinel does not deploy changes.
* [ ] Users can retest after implementing fixes.

## Dashboard

* [ ] Dashboard is centralized.
* [ ] Dashboard shows project data.
* [ ] Dashboard shows findings.
* [ ] Dashboard shows recommendations.
* [ ] Dashboard shows test history.
* [ ] Dashboard shows reports.
* [ ] Dashboard supports multiple projects.

## Integrations

* [ ] SDK works.
* [ ] CLI works where supported.
* [ ] API integration works.
* [ ] CI/CD integration works.
* [ ] Execution source is recorded.

## Reports

* [ ] Reports contain real data.
* [ ] Reports contain findings.
* [ ] Reports contain recommended solutions.
* [ ] Reports contain remediation status.
* [ ] Reports do not contain secrets.

## Security

* [ ] Project isolation tested.
* [ ] Authentication tested.
* [ ] Authorization tested.
* [ ] Secrets protected.
* [ ] API credentials protected.
* [ ] Logs reviewed for sensitive data.
* [ ] Dependency security reviewed.
* [ ] Error handling reviewed.

---

# 69. Agent Stop Conditions

The coding agent must stop and request user review before:

* replacing the authentication architecture
* replacing the database
* introducing a major infrastructure service
* changing the fundamental control-plane/execution-plane architecture
* deleting existing functionality
* breaking an existing API
* changing credential storage
* introducing autonomous source-code modification
* introducing autonomous deployment
* making irreversible data migrations
* changing the product's core security boundary

Do not make these decisions silently.

---

# 70. Definition of Done

A V3 feature is complete only when:

```text
Implementation
     ↓
Automated Tests
     ↓
Security Tests
     ↓
Existing Functionality Verified
     ↓
UI Verified
     ↓
API Verified
     ↓
Documentation Updated
     ↓
No Secret Exposure
     ↓
Git Diff Reviewed
     ↓
Acceptance Criteria Met
```

A feature is not complete merely because the code compiles or the UI renders.

---

# 71. Final Product Principle

Sentinel V3 should ultimately provide this experience:

```text
                    SENTINEL AI
                         │
                         ▼
                    YOUR PROJECT
                         │
                         ▼
                   SECURITY TEST
                         │
                         ▼
                     FINDINGS
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           EVIDENCE            IMPACT
              │                     │
              └──────────┬──────────┘
                         ▼
                EXPECTED SOLUTION
                         │
                         ▼
                    USER FIXES
                         │
                         ▼
                      RETEST
                         │
                         ▼
                   VERIFICATION
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           RESOLVED             STILL OPEN
                         │
                         ▼
                       REPORT
```

Sentinel's responsibility is to provide accurate security evidence, useful analysis, project-aware recommended solutions, and verification.

The user remains in control of implementing changes.

---

# 72. Agent Instruction

Before beginning any V3 phase, read:

1. `CLAUDE.md`
2. this `SpecV3_dev.md`
3. the existing repository
4. relevant existing documentation
5. relevant existing tests

Then identify the active phase.

Work ONLY on the active phase.

Do not begin later phases automatically.

For every phase:

1. inspect
2. plan
3. implement
4. test
5. security-review
6. verify existing functionality
7. document
8. report what changed

At the end of a phase, STOP.

Do not continue into the next phase without explicit user approval.

The user controls phase progression.

---

# ACTIVE PHASE

Phase 1 — Existing V3 Baseline and Architecture Verification

Status:

NOT STARTED

The coding agent must not begin Phase 2 until the user explicitly approves Phase 1.
