# SentinelAI Agent Security (D-048, phase_dev_upgrade.md Phase 9)

## Model

```
Agent (agent_id)
├── Model        (model id, informational)
├── Tools        (registered tool names)
├── Permissions  (rules: tool + action -> ALLOW | DENY | REQUIRE_APPROVAL)
├── Data sources (registered data source names)
└── Actions      (each request: tool + action [+ data_source])
```

Profiles live in server-side config only — `proxy/agent_profiles.yaml`
(override with `AGENT_PROFILES_PATH`). A request can never supply or modify
its own profile or rules.

## SentinelAI decides, it never executes

The policy layer returns a decision and records it. There is no code path
that runs a tool — so testing it cannot trigger a destructive action. The
caller executes (or doesn't) based on the decision.

## Evaluation rules (`proxy/agent_policy.py::evaluate`, pure)

1. **Default deny** — no matching rule → DENY.
2. Tool not registered to the agent → DENY (unauthorized tool).
3. A referenced data source not registered to the agent → DENY.
4. Most restrictive matching rule wins: **DENY > REQUIRE_APPROVAL > ALLOW**.
5. Names canonicalized (strip + lowercase) on both sides, then matched
   **exactly** — no prefix matching. `*` is honored as an action wildcard in
   a *rule*, never in a *request*.
6. Approval is never read from the request. It's a separate human step
   against a pending decision; the approver can't be the requesting agent.

## Bypass attempts covered by tests

Case/whitespace changes to evade a DENY, wildcard in the request, appended
commands (`read;delete`), prefix-of-a-registered-tool names, path-style
smuggling, empty names, an agent-supplied `approved: true` field,
self-approval, approving a DENY after the fact, re-resolving a resolved
action.

## Tracking

Every evaluation writes an `agent_action_logs` row: agent, tool, requested
action, data source, policy decision, reason, and `execution_result`:

| Decision | execution_result |
|---|---|
| ALLOW | `allowed_not_executed` |
| DENY | `blocked` |
| REQUIRE_APPROVAL | `pending_approval` → `approved_not_executed` or `rejected` |

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /v1/agents` | Profiles from config |
| `POST /v1/agents/{agent_id}/evaluate` | `{tool, action, data_source?}` → decision, recorded. 404 unknown agent |
| `GET /v1/agent-actions?agent_id=` | Decision log |
| `POST /v1/agent-actions/{id}/approve` / `reject` | `{approver}`. 409 if not pending, 403 self-approval, 422 blank approver |

## Not built (yet)

No UI page, and agent-policy bypass cases aren't registered as
`proxy/engine` security-test plugins — so they don't appear in the
dashboard/CI yet. Both are straightforward follow-ups; the spec asked for
the policy/evaluation layer first.
