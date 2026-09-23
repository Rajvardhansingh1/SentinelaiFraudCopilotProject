"""Phase 6 (D-045): security dashboard aggregation. Reads only what's actually
been persisted (proxy/db/models.py TestRunResult + Finding) — no fabricated
numbers. Deliberately aggregate-only: no raw attack_input/raw_output here
(that stays behind the Security Tests / Findings detail pages), per Phase 6's
"do not expose secrets or sensitive test payloads unnecessarily"."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from proxy.db.models import Finding, TestRunResult
from proxy.findings import OPEN_LIKE_STATUSES

_RECENT_ACTIVITY_LIMIT = 20


def _latest_run_id(db: Session, project_id: int | None) -> str | None:
    q = db.query(TestRunResult)
    if project_id is not None:
        q = q.filter(TestRunResult.project_id == project_id)
    row = q.order_by(TestRunResult.executed_at.desc()).first()
    return row.run_id if row else None


def build_dashboard_summary(db: Session, project_id: int | None = None) -> dict:
    """Phase 2 (D-055): project_id filters everything to one project's data
    when given; None (used only by internal/legacy callers) means unscoped."""
    latest_run_id = _latest_run_id(db, project_id)
    latest_rows: list[TestRunResult] = (
        db.query(TestRunResult).filter(TestRunResult.run_id == latest_run_id).all() if latest_run_id else []
    )
    status_counts = Counter(r.status for r in latest_rows)

    findings_q = db.query(Finding).filter(Finding.status.in_(OPEN_LIKE_STATUSES))
    if project_id is not None:
        findings_q = findings_q.filter(Finding.project_id == project_id)
    open_findings = findings_q.all()
    severity_distribution = Counter(f.severity for f in open_findings)

    activity_q = db.query(TestRunResult)
    affected_q = db.query(TestRunResult.provider, TestRunResult.model)
    if project_id is not None:
        activity_q = activity_q.filter(TestRunResult.project_id == project_id)
        affected_q = affected_q.filter(TestRunResult.project_id == project_id)
    recent_activity = activity_q.order_by(TestRunResult.executed_at.desc()).limit(_RECENT_ACTIVITY_LIMIT).all()
    affected = {(r.provider, r.model) for r in affected_q.distinct()}

    return {
        "last_run_at": latest_rows[0].executed_at if latest_rows else None,
        "total_tests": len(latest_rows),
        "passed": status_counts.get("PASS", 0),
        "failed": status_counts.get("FAIL", 0),
        "errors": status_counts.get("ERROR", 0),
        "not_run": status_counts.get("NOT_RUN", 0),
        "inconclusive": status_counts.get("INCONCLUSIVE", 0),
        "open_findings": len(open_findings),
        "severity_distribution": dict(severity_distribution),
        "recent_activity": [
            {
                "test_id": r.test_id,
                "category": r.category,
                "severity": r.severity,
                "status": r.status,
                "provider": r.provider,
                "model": r.model,
                "executed_at": r.executed_at,
                "execution_source": r.execution_source,
            }
            for r in recent_activity
        ],
        "affected_models": [{"provider": p, "model": m} for p, m in sorted(affected)],
    }
