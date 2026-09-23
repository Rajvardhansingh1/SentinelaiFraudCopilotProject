"""Phase 9 (D-048): persistence + human approval for agent policy decisions.
The pure decision logic lives in proxy/agent_policy.py."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.orm import Session

from proxy.agent_policy import ActionRequest, AgentProfile, Decision, PolicyDecision, canon, evaluate
from proxy.db.models import AgentActionLog

_RESULT_BY_DECISION = {
    Decision.ALLOW: "allowed_not_executed",
    Decision.DENY: "blocked",
    Decision.REQUIRE_APPROVAL: "pending_approval",
}


class ActionRequestIn(BaseModel):
    tool: str
    action: str
    data_source: str | None = None


class ApprovalIn(BaseModel):
    approver: str


class ApprovalError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def evaluate_and_record(
    db: Session, profile: AgentProfile, request: ActionRequest, project_id: int | None = None
) -> tuple[PolicyDecision, AgentActionLog]:
    decision = evaluate(profile, request)
    row = AgentActionLog(
        project_id=project_id,
        agent_id=profile.agent_id,
        tool=canon(request.tool),
        action=canon(request.action),
        data_source=canon(request.data_source) if request.data_source else None,
        decision=decision.decision.value,
        reason=decision.reason,
        execution_result=_RESULT_BY_DECISION[decision.decision],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return decision, row


def resolve_approval(db: Session, log_id: int, approver: str, approve: bool) -> AgentActionLog:
    row = db.query(AgentActionLog).filter(AgentActionLog.id == log_id).first()
    if row is None:
        raise ApprovalError(404, "action_not_found", "No such agent action.")
    if row.execution_result != "pending_approval":
        raise ApprovalError(409, "not_pending", f"Action is '{row.execution_result}', not pending approval.")
    who = canon(approver)
    if not who:
        raise ApprovalError(422, "approver_required", "An approver identity is required.")
    if who == row.agent_id:
        raise ApprovalError(403, "self_approval_forbidden", "An agent cannot approve its own action.")
    row.approved_by = who
    row.execution_result = "approved_not_executed" if approve else "rejected"
    db.commit()
    db.refresh(row)
    return row


def action_log_to_dict(r: AgentActionLog) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "agent_id": r.agent_id,
        "tool": r.tool,
        "action": r.action,
        "data_source": r.data_source,
        "decision": r.decision,
        "reason": r.reason,
        "execution_result": r.execution_result,
        "approved_by": r.approved_by,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
