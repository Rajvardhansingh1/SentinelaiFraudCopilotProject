"""EXECUTION + EVALUATION orchestration. Never crashes on a bad test: a plugin's
`run`/`evaluate` raising becomes an ERROR result, not an uncaught exception
(CLAUDE.md S11 — failures must be explicit)."""

from __future__ import annotations

from datetime import datetime, timezone

from proxy.engine.models import RawExecution, SecurityTest, TestResult, TestStatus


def run_test(test: SecurityTest) -> TestResult:
    try:
        evidence = test.run(test)
    except Exception as exc:
        return TestResult(
            test_id=test.id,
            name=test.name,
            category=test.category,
            severity=test.severity,
            status=TestStatus.ERROR,
            detail=f"Execution raised: {exc}",
            evidence=RawExecution(raw_input=test.attack_input, raw_output=None, provider="none", model="none"),
            executed_at=datetime.now(timezone.utc),
            reproduction={"attack_input": test.attack_input},
        )

    try:
        status, detail = test.evaluate(evidence)
    except Exception as exc:
        status, detail = TestStatus.ERROR, f"Evaluation raised: {exc}"

    return TestResult(
        test_id=test.id,
        name=test.name,
        category=test.category,
        severity=test.severity,
        status=status,
        detail=detail,
        evidence=evidence,
        executed_at=datetime.now(timezone.utc),
        reproduction={"attack_input": test.attack_input, "provider": evidence.provider, "model": evidence.model},
    )


def run_suite(tests: list[SecurityTest]) -> list[TestResult]:
    return [run_test(t) for t in tests]
