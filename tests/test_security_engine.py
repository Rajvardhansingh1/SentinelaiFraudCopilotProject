from proxy.engine.models import RawExecution, SecurityTest, Severity
from proxy.engine.models import TestStatus as Status
from proxy.engine.registry import all_tests, register
from proxy.engine.runner import run_suite, run_test


def _ok_test(test_id="t1"):
    return SecurityTest(
        id=test_id,
        name="ok test",
        category="unit",
        description="always passes",
        severity=Severity.LOW,
        attack_input="hello",
        expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input=t.attack_input, raw_output="ran", provider="fake", model="fake"),
        evaluate=lambda ev: (Status.PASS, "looked fine"),
    )


def test_run_test_returns_pass_with_evidence_and_reproduction():
    result = run_test(_ok_test())
    assert result.status == Status.PASS
    assert result.evidence.raw_output == "ran"
    assert result.reproduction["attack_input"] == "hello"
    assert result.reproduction["provider"] == "fake"
    assert result.executed_at is not None


def test_run_test_error_when_run_raises():
    test = SecurityTest(
        id="t-run-fail",
        name="run raises",
        category="unit",
        description="d",
        severity=Severity.LOW,
        attack_input="x",
        expected_behavior="n/a",
        run=lambda t: (_ for _ in ()).throw(RuntimeError("boom")),
        evaluate=lambda ev: (Status.PASS, "unreachable"),
    )
    result = run_test(test)
    assert result.status == Status.ERROR
    assert "boom" in result.detail


def test_run_test_error_when_evaluate_raises():
    test = SecurityTest(
        id="t-eval-fail",
        name="evaluate raises",
        category="unit",
        description="d",
        severity=Severity.LOW,
        attack_input="x",
        expected_behavior="n/a",
        run=lambda t: RawExecution(raw_input="x", raw_output="ran", provider="fake", model="fake"),
        evaluate=lambda ev: (_ for _ in ()).throw(ValueError("bad evaluator")),
    )
    result = run_test(test)
    assert result.status == Status.ERROR
    assert "bad evaluator" in result.detail
    # Execution's own evidence must still be preserved even though evaluation failed.
    assert result.evidence.raw_output == "ran"


def test_run_suite_runs_every_test_independently():
    results = run_suite([_ok_test("a"), _ok_test("b")])
    assert [r.test_id for r in results] == ["a", "b"]
    assert all(r.status == Status.PASS for r in results)


def test_registry_accumulates_across_plugins():
    before = len(all_tests())

    @register
    def _extra():
        return [_ok_test("registry-probe")]

    after = all_tests()
    assert len(after) == before + 1
    assert any(t.id == "registry-probe" for t in after)


def test_builtin_injection_tests_are_registered_and_unique():
    import proxy.engine.plugins  # noqa: F401 — triggers registration

    tests = all_tests()
    ids = [t.id for t in tests if t.category == "prompt_injection"]
    assert len(ids) >= 4
    assert len(ids) == len(set(ids)), "duplicate test ids"


def test_builtin_injection_tests_pass_against_the_real_detector():
    """Regression guard: the engine's migrated tests must still catch the same
    attacks proxy/redteam/attack_library.py already protects against."""
    import proxy.engine.plugins  # noqa: F401

    tests = [t for t in all_tests() if t.category == "prompt_injection"]
    results = run_suite(tests)
    failures = [r for r in results if r.status != Status.PASS]
    assert not failures, f"injection tests regressed: {[(f.test_id, f.status, f.detail) for f in failures]}"


def test_every_migrated_test_has_required_metadata():
    import proxy.engine.plugins  # noqa: F401

    for test in all_tests():
        assert test.id
        assert test.name
        assert test.category
        assert test.description
        assert isinstance(test.severity, Severity)
        assert test.attack_input
        assert test.expected_behavior
