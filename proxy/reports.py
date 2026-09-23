"""Phase 12 (D-052): executive and technical security reports.

Built only from what SentinelAI has actually stored (test_run_results,
findings, baselines, security_events) plus the registered test definitions
for attack inputs. Generating a report never runs a test and never invents a
number — an empty period produces an explicitly empty report.

Every string in every report passes through `scrub()` before it's returned:
PII/secret patterns are redacted and the server's configured provider keys
are replaced literally, so a credential can't reach a report even if one
was captured in stored evidence."""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import proxy.engine.plugins  # noqa: F401 — registers test definitions
from proxy.agent_policy import load_profiles
from proxy.config import settings
from proxy.db.models import Baseline, Finding, SecurityEvent, TestRunResult
from proxy.engine.registry import all_tests
from proxy.findings import OPEN_LIKE_STATUSES
from proxy.middleware.pii_scanner import redact_pii
from proxy.regression import compare_runs, run_snapshot
from proxy.remediation import remediation_for

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
_KEY_FINDINGS_LIMIT = 10


# --- secret hygiene ---


def _configured_secrets() -> list[str]:
    return [k for k in (settings.groq_api_key, settings.gemini_api_key) if k and len(k) >= 8]


# SentinelAI-generated uuids — can't carry a secret, and a digit-heavy uuid
# can false-match the phone regex, which would break reproduction ids.
_ID_KEYS = {"run_id", "latest_run_id"}


def scrub(value, key: str | None = None):
    if isinstance(value, str):
        if key in _ID_KEYS:
            return value
        for secret in _configured_secrets():
            value = value.replace(secret, "[REDACTED_CONFIGURED_KEY]")
        return redact_pii(value)[0]
    if isinstance(value, dict):
        return {k: scrub(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    return value


# --- period helpers ---


def _in_period(query, column, since: datetime | None, until: datetime | None):
    if since:
        query = query.filter(column >= since)
    if until:
        query = query.filter(column <= until)
    return query


def _latest_run(db: Session, since, until, project_id: int | None = None) -> list[TestRunResult]:
    query = db.query(TestRunResult)
    if project_id is not None:
        query = query.filter(TestRunResult.project_id == project_id)
    newest = _in_period(query, TestRunResult.executed_at, since, until).order_by(
        TestRunResult.executed_at.desc()
    ).first()
    if newest is None:
        return []
    run_query = db.query(TestRunResult).filter(TestRunResult.run_id == newest.run_id)
    if project_id is not None:
        run_query = run_query.filter(TestRunResult.project_id == project_id)
    return run_query.all()


def _period(db: Session, since, until, project_id: int | None = None) -> dict:
    query = db.query(TestRunResult)
    if project_id is not None:
        query = query.filter(TestRunResult.project_id == project_id)
    runs = _in_period(query, TestRunResult.executed_at, since, until)
    first = runs.order_by(TestRunResult.executed_at.asc()).first()
    last = runs.order_by(TestRunResult.executed_at.desc()).first()
    return {
        "requested_since": since,
        "requested_until": until,
        "first_test_activity": first.executed_at if first else None,
        "last_test_activity": last.executed_at if last else None,
        "test_runs": runs.with_entities(TestRunResult.run_id).distinct().count(),
    }


# --- executive ---


def build_executive_report(db: Session, since: datetime | None = None, until: datetime | None = None, project_id: int | None = None) -> dict:
    latest = _latest_run(db, since, until, project_id=project_id)
    status_counts = Counter(r.status for r in latest)

    findings_query = db.query(Finding)
    events_query = db.query(SecurityEvent)
    baseline_query = db.query(Baseline)
    if project_id is not None:
        findings_query = findings_query.filter(Finding.project_id == project_id)
        events_query = events_query.filter(SecurityEvent.project_id == project_id)
        baseline_query = baseline_query.filter(Baseline.project_id == project_id)

    open_findings = findings_query.filter(Finding.status.in_(OPEN_LIKE_STATUSES)).all()
    key = sorted(open_findings, key=lambda f: (-_SEVERITY_RANK.get(f.severity, 0), f.created_at))[:_KEY_FINDINGS_LIMIT]

    all_findings = findings_query.all()
    new_in_period = _in_period(findings_query, Finding.created_at, since, until).count()
    resolved_in_period = _in_period(
        findings_query.filter(Finding.status == "RESOLVED"), Finding.updated_at, since, until
    ).count()

    major_changes: dict = {
        "baseline": None,
        "regressions": [],
        "fixed": [],
        "provider_config_changed": None,
        "findings_opened_in_period": new_in_period,
        "findings_resolved_in_period": resolved_in_period,
    }
    baseline = baseline_query.order_by(Baseline.created_at.desc()).first()
    if baseline is not None and latest and baseline.run_id != latest[0].run_id:
        diff = compare_runs(run_snapshot(db, baseline.run_id), run_snapshot(db, latest[0].run_id))
        major_changes.update(
            baseline=baseline.name,
            regressions=[r["test_id"] for r in diff["regressions"]],
            fixed=[r["test_id"] for r in diff["fixed"]],
            provider_config_changed=diff["provider_config_changed"],
        )

    events = _in_period(events_query, SecurityEvent.created_at, since, until).all()

    limitations = ["Passing tests show these specific attacks were caught — they do not prove the system is secure."]
    if status_counts.get("INCONCLUSIVE"):
        limitations.append(f"{status_counts['INCONCLUSIVE']} test(s) INCONCLUSIVE: no automated classifier exists for that category.")
    if status_counts.get("ERROR"):
        limitations.append(f"{status_counts['ERROR']} test(s) ERROR: the test itself failed to run; results for those are unknown.")
    if not latest:
        limitations.append("No recorded test runs in this period.")

    report = {
        "report_type": "executive",
        "generated_at": datetime.now(timezone.utc),
        "period": _period(db, since, until, project_id=project_id),
        "scope": {
            "tests_in_latest_run": len(latest),
            "categories": sorted({r.category for r in latest}),
            "providers_models": sorted({f"{r.provider}/{r.model}" for r in latest}),
            "agents_configured": sorted(load_profiles(settings.agent_profiles_path)),
            "applications_observed": sorted({e.application for e in events if e.application}),
        },
        "latest_run": (
            {"run_id": latest[0].run_id, "executed_at": latest[0].executed_at, "status_counts": dict(status_counts)}
            if latest
            else None
        ),
        "key_findings": [
            {"id": f.id, "title": f.title, "severity": f.severity, "category": f.category, "status": f.status,
             "remediation": remediation_for(f.category)}
            for f in key
        ],
        "severity_distribution": dict(Counter(f.severity for f in open_findings)),
        "major_changes": major_changes,
        "remediation_status": dict(Counter(f.status for f in all_findings)),
        "security_events": dict(Counter(e.event_type for e in events)),
        "limitations": limitations,
    }
    return scrub(report)


# --- technical ---


def build_technical_report(db: Session, since: datetime | None = None, until: datetime | None = None, project_id: int | None = None) -> dict:
    definitions = {t.id: t for t in all_tests()}
    latest = _latest_run(db, since, until, project_id=project_id)

    test_cases = []
    for r in sorted(latest, key=lambda r: (r.category, r.test_id)):
        d = definitions.get(r.test_id)
        test_cases.append(
            {
                "test_id": r.test_id,
                "name": d.name if d else None,
                "category": r.category,
                "severity": r.severity,
                "description": d.description if d else None,
                "attack_input": d.attack_input if d else None,
                "expected_behavior": d.expected_behavior if d else None,
                "result": r.status,
                "provider": r.provider,
                "model": r.model,
                "executed_at": r.executed_at,
                "reproduction": {
                    "run_id": r.run_id,
                    "command": f"POST /v1/security-tests/run?category={r.category}",
                    "definition_available": d is not None,
                },
                "remediation": remediation_for(r.category),
            }
        )

    findings_query = db.query(Finding)
    if project_id is not None:
        findings_query = findings_query.filter(Finding.project_id == project_id)
    findings = _in_period(findings_query, Finding.created_at, since, until).order_by(Finding.created_at.desc()).all()
    report = {
        "report_type": "technical",
        "generated_at": datetime.now(timezone.utc),
        "period": _period(db, since, until, project_id=project_id),
        "latest_run_id": latest[0].run_id if latest else None,
        "test_cases": test_cases,
        "findings": [
            {
                "id": f.id,
                "test_id": f.test_id,
                "title": f.title,
                "category": f.category,
                "severity": f.severity,
                "status": f.status,
                "description": f.description,
                "affected_target": f.affected_target,
                "evidence": f.evidence,
                "reproduction": f.reproduction,
                "provider": f.provider,
                "model": f.model,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
                "remediation": remediation_for(f.category),
            }
            for f in findings
        ],
        "notes": [] if latest else ["No recorded test runs in this period."],
    }
    return scrub(report)


# --- markdown ---


def _ts(value) -> str:
    return value.isoformat() if isinstance(value, datetime) else (value or "—")


def executive_markdown(r: dict) -> str:
    p = r["period"]
    lines = [
        "# SentinelAI Security Report — Executive Summary",
        "",
        f"Generated: {_ts(r['generated_at'])}",
        f"Testing period: {_ts(p['first_test_activity'])} → {_ts(p['last_test_activity'])} ({p['test_runs']} recorded run(s))",
        "",
        "## Assessment scope",
        f"- Tests in latest run: {r['scope']['tests_in_latest_run']}",
        f"- Categories: {', '.join(r['scope']['categories']) or '—'}",
        f"- Providers/models: {', '.join(r['scope']['providers_models']) or '—'}",
        f"- Agents configured: {', '.join(r['scope']['agents_configured']) or '—'}",
        "",
        "## Latest run",
    ]
    if r["latest_run"]:
        lines += [f"- {k}: {v}" for k, v in sorted(r["latest_run"]["status_counts"].items())]
    else:
        lines.append("- No recorded test runs in this period.")
    lines += ["", "## Key findings"]
    lines += [f"- [{f['severity']}] {f['title']} ({f['status']}) — {f['remediation']}" for f in r["key_findings"]] or ["- No open findings."]
    lines += ["", "## Severity distribution (open findings)"]
    lines += [f"- {k}: {v}" for k, v in sorted(r["severity_distribution"].items())] or ["- None."]
    mc = r["major_changes"]
    lines += [
        "",
        "## Major changes",
        f"- Baseline: {mc['baseline'] or 'none'}",
        f"- Regressions: {', '.join(mc['regressions']) or 'none'}",
        f"- Fixed: {', '.join(mc['fixed']) or 'none'}",
        f"- Provider/model config changed: {mc['provider_config_changed'] if mc['provider_config_changed'] is not None else 'n/a'}",
        f"- Findings opened / resolved in period: {mc['findings_opened_in_period']} / {mc['findings_resolved_in_period']}",
        "",
        "## Remediation status",
    ]
    lines += [f"- {k}: {v}" for k, v in sorted(r["remediation_status"].items())] or ["- No findings recorded."]
    lines += ["", "## Security events in period"]
    lines += [f"- {k}: {v}" for k, v in sorted(r["security_events"].items())] or ["- None."]
    lines += ["", "## Limitations"] + [f"- {x}" for x in r["limitations"]]
    return "\n".join(lines)


def technical_markdown(r: dict) -> str:
    p = r["period"]
    lines = [
        "# SentinelAI Security Report — Technical",
        "",
        f"Generated: {_ts(r['generated_at'])}",
        f"Testing period: {_ts(p['first_test_activity'])} → {_ts(p['last_test_activity'])}",
        f"Latest run: {r['latest_run_id'] or '—'}",
        "",
        "## Test cases",
    ]
    if not r["test_cases"]:
        lines.append("No recorded test runs in this period.")
    for t in r["test_cases"]:
        lines += [
            "",
            f"### {t['test_id']} — {t['result']}",
            f"- Category / severity: {t['category']} / {t['severity']}",
            f"- Attack input: `{t['attack_input']}`" if t["attack_input"] else "- Attack input: definition no longer registered",
            f"- Expected: {t['expected_behavior'] or '—'}",
            f"- Provider/model: {t['provider']} / {t['model']}",
            f"- Executed: {_ts(t['executed_at'])}",
            f"- Reproduce: `{t['reproduction']['command']}` (run {t['reproduction']['run_id']})",
            f"- Remediation: {t['remediation']}",
        ]
    lines += ["", "## Findings"]
    if not r["findings"]:
        lines.append("No findings opened in this period.")
    for f in r["findings"]:
        lines += [
            "",
            f"### #{f['id']} {f['title']} [{f['severity']}, {f['status']}]",
            f"- Test: {f['test_id']} ({f['category']}) on {f['affected_target']}",
            f"- Evidence: input `{f['evidence'].get('raw_input')}` → output `{f['evidence'].get('raw_output')}`",
            f"- Provider/model: {f['provider']} / {f['model']}",
            f"- Opened / updated: {_ts(f['created_at'])} / {_ts(f['updated_at'])}",
            f"- Reproduction: {f['reproduction']}",
            f"- Remediation: {f['remediation']}",
        ]
    return "\n".join(lines)


def technical_csv(r: dict) -> str:
    """Phase 10 (§41): a machine-readable format alongside JSON/Markdown —
    one row per finding, for import into a spreadsheet or ticket tracker."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "test_id", "title", "category", "severity", "status", "affected_target", "created_at", "updated_at", "remediation"])
    for f in r["findings"]:
        writer.writerow([f["id"], f["test_id"], f["title"], f["category"], f["severity"], f["status"],
                          f["affected_target"], _ts(f["created_at"]), _ts(f["updated_at"]), f["remediation"]])
    return buf.getvalue()
