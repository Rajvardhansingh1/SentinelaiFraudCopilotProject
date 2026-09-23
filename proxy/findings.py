"""Phase 5 (D-044): Findings subsystem, built on top of proxy/engine's
TestResult. A Finding is generated only from a FAIL result — a FAIL means a
guardrail that should have caught an attack didn't (a real gap). ERROR
(test-execution bug) and INCONCLUSIVE (no classifier exists yet) are not
findings; they're test-health signals, tracked as TestResult, not vulnerabilities."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from proxy.db.models import Finding, TestRunResult
from proxy.engine.models import TestResult, TestStatus
from proxy.remediation import remediation_for

FindingStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED", "RETEST_REQUIRED"]
_VALID_STATUSES: set[str] = {"OPEN", "ACKNOWLEDGED", "RESOLVED", "RETEST_REQUIRED"}
OPEN_LIKE_STATUSES = {"OPEN", "ACKNOWLEDGED", "RETEST_REQUIRED"}


class FindingPatch(BaseModel):
    status: FindingStatus


def _finding_fields(result: TestResult) -> dict:
    return {
        "test_id": result.test_id,
        "category": result.category,
        "severity": result.severity.value,
        "title": f"{result.name} — guardrail bypassed",
        "description": result.detail,
        "affected_target": "SentinelAI",
        "evidence": {
            "raw_input": result.evidence.raw_input,
            "raw_output": result.evidence.raw_output,
            "provider": result.evidence.provider,
            "model": result.evidence.model,
            "status_code": result.evidence.status_code,
        },
        "reproduction": result.reproduction,
        "provider": result.evidence.provider,
        "model": result.evidence.model,
    }


def finding_to_dict(f: Finding) -> dict:
    return {
        "id": f.id,
        "project_id": f.project_id,
        "test_id": f.test_id,
        "category": f.category,
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "affected_target": f.affected_target,
        "evidence": f.evidence,
        "reproduction": f.reproduction,
        "provider": f.provider,
        "model": f.model,
        "status": f.status,
        "remediation": remediation_for(f.category),
        "created_at": f.created_at,
        "updated_at": f.updated_at,
    }


def sync_findings(db: Session, results: list[TestResult], project_id: int | None = None) -> list[Finding]:
    """For every FAIL result, open a new Finding unless one is already open
    (OPEN/ACKNOWLEDGED/RETEST_REQUIRED) for that test_id *within the same
    project* — avoids duplicate spam on repeated runs while keeping two
    projects' findings for the same test_id independent (Phase 2, D-055).
    A RESOLVED finding for a test that fails again gets a fresh Finding row
    (its own history), never overwritten."""
    created: list[Finding] = []
    for result in results:
        if result.status != TestStatus.FAIL:
            continue
        existing_open = (
            db.query(Finding)
            .filter(
                Finding.test_id == result.test_id,
                Finding.status.in_(OPEN_LIKE_STATUSES),
                Finding.project_id == project_id,
            )
            .first()
        )
        if existing_open:
            continue
        finding = Finding(status="OPEN", project_id=project_id, **_finding_fields(result))
        db.add(finding)
        created.append(finding)
    if created:
        db.commit()
        for f in created:
            db.refresh(f)
    return created


def record_test_run(db: Session, results: list[TestResult], project_id: int | None = None) -> str:
    """Phase 6 (D-045): logs every result (any status) under one shared
    run_id, so the dashboard has real history — separate from `Finding`,
    which only tracks FAILs needing human action. Phase 2 (D-055): tagged
    with project_id so per-project dashboards/history are possible."""
    run_id = str(uuid.uuid4())
    for result in results:
        db.add(
            TestRunResult(
                run_id=run_id,
                project_id=project_id,
                test_id=result.test_id,
                category=result.category,
                severity=result.severity.value,
                status=result.status.value,
                provider=result.evidence.provider,
                model=result.evidence.model,
                executed_at=result.executed_at,
            )
        )
    db.commit()
    return run_id
