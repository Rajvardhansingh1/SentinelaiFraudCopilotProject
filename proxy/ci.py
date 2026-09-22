"""Phase 8 (D-047): CI failure-policy evaluation. Pure functions — no HTTP,
no subprocess — so the pass/fail logic is unit-testable without a live
server. `scripts/sentinel_ci.py` is the thin HTTP-calling wrapper around this."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CIPolicy:
    """Every threshold here comes from the caller (CLI flags) — nothing is
    hardcoded inside evaluate() itself. Defaults are just this dataclass's
    defaults, visible and overridable, not buried logic."""

    fail_on_statuses: frozenset[str] = frozenset({"FAIL"})
    fail_on_severities: frozenset[str] | None = None  # None = any severity counts
    max_failures: int = 0
    max_regressions: int = 0


def matching_results(results: list[dict], policy: CIPolicy) -> list[dict]:
    matches = []
    for r in results:
        if r["status"] not in policy.fail_on_statuses:
            continue
        if policy.fail_on_severities is not None and r["severity"] not in policy.fail_on_severities:
            continue
        matches.append(r)
    return matches


def evaluate(results: list[dict], policy: CIPolicy, regression_report: dict | None = None) -> dict:
    matches = matching_results(results, policy)
    reasons: list[str] = []
    should_fail = False

    if len(matches) > policy.max_failures:
        should_fail = True
        reasons.append(f"{len(matches)} result(s) matched the failure policy (max allowed: {policy.max_failures})")

    regression_count = 0
    if regression_report is not None:
        regression_count = len(regression_report.get("regressions", []))
        if regression_count > policy.max_regressions:
            should_fail = True
            reasons.append(f"{regression_count} regression(s) detected (max allowed: {policy.max_regressions})")

    return {
        "should_fail": should_fail,
        "reasons": reasons,
        "matching_results": matches,
        "regression_count": regression_count,
        "total_results": len(results),
    }


def format_human_summary(results: list[dict], verdict: dict, target: str) -> str:
    lines = ["# SentinelAI CI Security Report", "", f"Target: `{target}`", f"Total tests: {len(results)}", ""]

    status_counts: dict[str, int] = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")

    lines.append("")
    lines.append("## Result: " + ("FAIL" if verdict["should_fail"] else "PASS"))
    for reason in verdict["reasons"]:
        lines.append(f"- {reason}")

    if verdict["matching_results"]:
        lines.append("")
        lines.append("## Tests matching the failure policy")
        for r in verdict["matching_results"]:
            lines.append(f"- `{r['test_id']}` ({r['category']}, {r['severity']}): {r['status']} — {r['detail']}")

    if verdict["regression_count"] > 0:
        lines.append("")
        lines.append(f"## Regressions detected: {verdict['regression_count']}")

    return "\n".join(lines)
