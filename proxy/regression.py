"""Phase 7 (D-046): security regression testing. A baseline pins one
`TestRunResult.run_id`; a later run is compared against it.

Deliberately produces **no single "security score"** — phase_dev_upgrade.md
warns against making a score the source of truth, so the report is counts
plus the full per-test detail, and every individual result stays reachable
(`per_test` below, and `GET /v1/security-tests/run` / the Findings pages)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from proxy.db.models import Baseline, Finding, TestRunResult


class BaselineCreate(BaseModel):
    name: str
    run_id: str | None = None


def row_to_snapshot(row: TestRunResult) -> dict:
    return {
        "test_id": row.test_id,
        "category": row.category,
        "severity": row.severity,
        "status": row.status,
        "provider": row.provider,
        "model": row.model,
    }


def compare_runs(baseline: list[dict], current: list[dict]) -> dict:
    """Pure comparison — no DB, no time. `baseline`/`current` are lists of
    row_to_snapshot() dicts."""
    base_by_id = {r["test_id"]: r for r in baseline}
    curr_by_id = {r["test_id"]: r for r in current}

    regressions: list[dict] = []
    new_failures: list[dict] = []
    fixed: list[dict] = []
    unchanged: list[dict] = []
    other_changes: list[dict] = []
    severity_changes: list[dict] = []
    per_test: list[dict] = []

    for test_id, curr in curr_by_id.items():
        base = base_by_id.get(test_id)
        entry = {
            "test_id": test_id,
            "category": curr["category"],
            "baseline_status": base["status"] if base else None,
            "current_status": curr["status"],
            "baseline_severity": base["severity"] if base else None,
            "current_severity": curr["severity"],
        }
        per_test.append(entry)

        if base is None:
            if curr["status"] == "FAIL":
                new_failures.append(entry)
            continue

        if base["severity"] != curr["severity"]:
            severity_changes.append(entry)

        if base["status"] == curr["status"]:
            unchanged.append(entry)
        elif base["status"] == "PASS" and curr["status"] == "FAIL":
            regressions.append(entry)
        elif base["status"] == "FAIL" and curr["status"] == "PASS":
            fixed.append(entry)
        else:
            other_changes.append(entry)

    added_tests = sorted(set(curr_by_id) - set(base_by_id))
    removed_tests = sorted(set(base_by_id) - set(curr_by_id))

    baseline_config = sorted({(r["provider"], r["model"]) for r in baseline})
    current_config = sorted({(r["provider"], r["model"]) for r in current})

    return {
        "regressions": regressions,
        "new_failures": new_failures,
        "fixed": fixed,
        "unchanged": unchanged,
        "other_changes": other_changes,
        "severity_changes": severity_changes,
        "added_tests": added_tests,
        "removed_tests": removed_tests,
        "provider_config_changed": baseline_config != current_config,
        "baseline_config": [{"provider": p, "model": m} for p, m in baseline_config],
        "current_config": [{"provider": p, "model": m} for p, m in current_config],
        "per_test": sorted(per_test, key=lambda e: e["test_id"]),
    }


def findings_delta(db: Session, since: datetime, project_id: int | None = None) -> dict:
    """Findings opened or resolved since the baseline was taken. Read-only —
    resolving a finding never deletes it (D-044), so both lists stay truthful."""
    new_q = db.query(Finding).filter(Finding.created_at > since)
    resolved_q = db.query(Finding).filter(Finding.status == "RESOLVED", Finding.updated_at > since)
    if project_id is not None:
        new_q = new_q.filter(Finding.project_id == project_id)
        resolved_q = resolved_q.filter(Finding.project_id == project_id)
    return {
        "new_findings": [
            {"id": f.id, "test_id": f.test_id, "severity": f.severity, "title": f.title} for f in new_q.all()
        ],
        "resolved_findings": [
            {"id": f.id, "test_id": f.test_id, "severity": f.severity, "title": f.title} for f in resolved_q.all()
        ],
    }


def latest_run_id(db: Session, project_id: int | None = None) -> str | None:
    query = db.query(TestRunResult)
    if project_id is not None:
        query = query.filter(TestRunResult.project_id == project_id)
    row = query.order_by(TestRunResult.executed_at.desc()).first()
    return row.run_id if row else None


def run_snapshot(db: Session, run_id: str) -> list[dict]:
    rows = db.query(TestRunResult).filter(TestRunResult.run_id == run_id).all()
    return [row_to_snapshot(r) for r in rows]


def create_baseline(db: Session, name: str, run_id: str | None = None, project_id: int | None = None) -> Baseline | None:
    """Pins a baseline to a run. Defaults to the most recent recorded run
    *in this project* (Phase 2/7, D-055). Returns None if there is no run to
    baseline (caller turns that into a clear error — never a silently empty
    baseline)."""
    target_run_id = run_id or latest_run_id(db, project_id=project_id)
    if target_run_id is None:
        return None
    run_query = db.query(TestRunResult).filter(TestRunResult.run_id == target_run_id)
    if project_id is not None:
        run_query = run_query.filter(TestRunResult.project_id == project_id)
    if not run_query.first():
        return None
    baseline = Baseline(name=name, run_id=target_run_id, project_id=project_id)
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def baseline_to_dict(b: Baseline) -> dict:
    return {"id": b.id, "name": b.name, "run_id": b.run_id, "project_id": b.project_id, "created_at": b.created_at}


def build_regression_report(db: Session, baseline: Baseline, run_id: str) -> dict:
    baseline_rows = run_snapshot(db, baseline.run_id)
    current_rows = run_snapshot(db, run_id)
    report = compare_runs(baseline_rows, current_rows)
    report["baseline"] = baseline_to_dict(baseline)
    report["current_run_id"] = run_id
    report["findings"] = findings_delta(db, baseline.created_at, project_id=baseline.project_id)
    return report
