# SentinelAI Continuous Monitoring (D-050, phase_dev_upgrade.md Phase 11)

## Events are not findings

`SecurityEvent` (`security_events` table) is a separate model from
`Finding`. An event is an *observation* — it has no status workflow and
creating one never creates or changes a Finding. A blocked attack attempt is
the guardrail working, not a vulnerability. Findings (D-044) remain the only
place vulnerabilities live.

## Event types and where they come from

| event_type | Emitted by | When |
|---|---|---|
| `attack_attempt` | proxy `/v1/generate`, gateway | Injection detector flagged the input (`details.blocked`) |
| `request_blocked` | proxy, gateway | Rate limit, oversized input, or a PII `block` policy |
| `policy_violation` | proxy, gateway, agent policy | PII/secrets inbound or in model output; a normal agent-policy denial |
| `finding_opened` | `/v1/findings/sync` | A new Finding opened (once per finding, not per run) |
| `regression_detected` | `/v1/findings/sync` | A test that PASSed in the latest baseline FAILs now |
| `suspicious_tool_activity` | agent policy | Unregistered tool/data source, wildcard/empty request, self-approval, approving a DENY |

Not events: benign requests, agent ALLOW / REQUIRE_APPROVAL decisions.

## No raw content

Summaries and details carry metadata only — pattern names, PII *types*,
ids, codes, lengths. Never prompt text, model output, or the PII/secret
itself (tested for each emitter).

## Filtering — `GET /v1/events`

`since`, `until` (ISO time), `severity` (comma list), `min_severity`,
`application`, `model`, `category` (comma list), `event_type` (comma list),
`limit` (max 1000). `application` is the proxy `operation`, the gateway's
`application` label, or the agent id.

## Retention and configuration

| Setting | Default | Effect |
|---|---|---|
| `EVENTS_ENABLED` | `true` | Master switch |
| `EVENTS_RETENTION_DAYS` | `30` | Older events purged on proxy start and via `POST /v1/events/retention/apply`. `0` = keep forever. Only events — findings/test history untouched |
| `EVENTS_MIN_SEVERITY` | `info` | Events below this aren't recorded |
| `GATEWAY_RECORD_EVENTS` | `false` | Gateway writes events. Off keeps the gateway stateless (D-049) |

`GET /v1/events/config` reports the active values.

Recording never breaks the triggering request: a failed write is logged and
rolled back, and the response is unaffected (tested).

## UI

`web/app/monitoring/page.tsx` — time window, event type, minimum severity,
category, application, model filters; distinct error vs. empty states;
active config shown in the header.
