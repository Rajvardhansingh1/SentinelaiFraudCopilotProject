"""Phase 9 (D-048): agent security — explicit tool/permission policy layer.

An agent is modeled as: model, tools, permissions (rules), data sources, and
the actions it requests. SentinelAI only *decides* (ALLOW / DENY /
REQUIRE_APPROVAL) and records the decision; it never executes a tool. That
is the "no destructive actions as part of testing" guarantee — there is no
execution path here to misuse.

Evaluation rules (pure, no I/O):
1. Default deny — no matching rule means DENY.
2. The tool must be registered to the agent, else DENY (unauthorized tool).
3. A referenced data source must be registered to the agent, else DENY.
4. Among matching rules the most restrictive wins: DENY > REQUIRE_APPROVAL > ALLOW.
5. Names are canonicalized (strip + lower) on both sides, and matched exactly —
   no prefix matching, and a wildcard is only honored in a *rule*, never in a
   *request*. Closes case/whitespace/suffix/wildcard bypass tricks.
6. Approval is never read from the request. It's a separate step recorded
   against a PENDING decision, and the approver can't be the requesting agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


# Most restrictive first — rule 4.
_PRECEDENCE = [Decision.DENY, Decision.REQUIRE_APPROVAL, Decision.ALLOW]

WILDCARD = "*"


def canon(name: str) -> str:
    return name.strip().lower()


@dataclass(frozen=True)
class PolicyRule:
    tool: str
    action: str  # may be WILDCARD in a rule
    decision: Decision


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    model: str
    tools: frozenset[str]
    data_sources: frozenset[str]
    rules: tuple[PolicyRule, ...]


@dataclass(frozen=True)
class ActionRequest:
    tool: str
    action: str
    data_source: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    # Machine-readable why (D-050) — lets monitoring tell a normal denial
    # from an out-of-bounds probe without parsing `reason`.
    code: str = ""


# Requests reaching outside the agent's declared shape — suspicious, not just denied.
OUT_OF_BOUNDS_CODES = {"empty_name", "wildcard_request", "unregistered_tool", "unregistered_data_source"}


def evaluate(profile: AgentProfile, request: ActionRequest) -> PolicyDecision:
    tool = canon(request.tool)
    action = canon(request.action)

    if not tool or not action:
        return PolicyDecision(Decision.DENY, "Empty tool or action name.", "empty_name")
    if WILDCARD in action or WILDCARD in tool:
        return PolicyDecision(Decision.DENY, "Wildcards are not allowed in a request, only in policy rules.", "wildcard_request")
    if tool not in profile.tools:
        return PolicyDecision(
            Decision.DENY, f"Tool '{tool}' is not registered to agent '{profile.agent_id}'.", "unregistered_tool"
        )
    if request.data_source is not None and canon(request.data_source) not in profile.data_sources:
        return PolicyDecision(
            Decision.DENY,
            f"Data source '{canon(request.data_source)}' is not registered to agent '{profile.agent_id}'.",
            "unregistered_data_source",
        )

    matched = {r.decision for r in profile.rules if r.tool == tool and r.action in (action, WILDCARD)}
    for decision in _PRECEDENCE:
        if decision in matched:
            return PolicyDecision(decision, f"Matched {decision.value} rule for {tool}.{action}.", f"rule_{decision.value.lower()}")
    return PolicyDecision(Decision.DENY, f"No rule permits {tool}.{action} (default deny).", "default_deny")


def profile_from_dict(data: dict) -> AgentProfile:
    return AgentProfile(
        agent_id=canon(data["agent_id"]),
        model=data["model"],
        tools=frozenset(canon(t) for t in data.get("tools", [])),
        data_sources=frozenset(canon(d) for d in data.get("data_sources", [])),
        rules=tuple(
            PolicyRule(tool=canon(r["tool"]), action=canon(r["action"]), decision=Decision(r["decision"]))
            for r in data.get("rules", [])
        ),
    )


def load_profiles(path: str | Path) -> dict[str, AgentProfile]:
    """Server-side config only (Phase 2 principle) — profiles are never
    accepted from a request body. A missing file means no agents, not a crash."""
    p = Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    profiles = [profile_from_dict(a) for a in raw.get("agents", [])]
    return {prof.agent_id: prof for prof in profiles}


def profile_to_dict(p: AgentProfile) -> dict:
    return {
        "agent_id": p.agent_id,
        "model": p.model,
        "tools": sorted(p.tools),
        "data_sources": sorted(p.data_sources),
        "rules": [{"tool": r.tool, "action": r.action, "decision": r.decision.value} for r in p.rules],
    }
