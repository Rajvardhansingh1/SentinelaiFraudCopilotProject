from scripts.run_eval_suite import (
    end_to_end_latency,
    field_extraction_accuracy,
    hallucination_distribution,
    injection_catch_rate,
    policy_violation_accuracy,
    tamper_detection_precision_recall,
)


def _result(vendor="Acme", date="2026-01-01", total="42.5", extracted=None):
    return {
        "ground_truth": {"vendor": vendor, "date": date, "total": total},
        "extracted_fields": extracted if extracted is not None else {"vendor": vendor, "date": date, "total": total},
    }


def test_field_extraction_accuracy_all_correct():
    results = [_result(), _result()]
    acc = field_extraction_accuracy(results)
    assert acc["vendor"] == 1.0
    assert acc["date"] == 1.0
    assert acc["total"] == 1.0


def test_field_extraction_accuracy_partial_mismatch():
    results = [_result(), _result(extracted={"vendor": "Wrong", "date": "2026-01-01", "total": "42.5"})]
    acc = field_extraction_accuracy(results)
    assert acc["vendor"] == 0.5
    assert acc["date"] == 1.0


def test_field_extraction_accuracy_skips_failed_extraction():
    results = [{"ground_truth": {"vendor": "Acme", "date": "2026-01-01", "total": "42.5"}, "extracted_fields": None}]
    acc = field_extraction_accuracy(results)
    assert acc["vendor"] == 0.0


def test_tamper_detection_precision_recall():
    results = [
        {"ground_truth": {"genuine_or_tampered": "tampered"}, "forensics_result": {"tamper_likelihood": "high"}},
        {"ground_truth": {"genuine_or_tampered": "tampered"}, "forensics_result": {"tamper_likelihood": "low"}},
        {"ground_truth": {"genuine_or_tampered": "genuine"}, "forensics_result": {"tamper_likelihood": "low"}},
        {"ground_truth": {"genuine_or_tampered": "genuine"}, "forensics_result": {"tamper_likelihood": "high"}},
    ]
    metrics = tamper_detection_precision_recall(results)
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5


def test_policy_violation_accuracy():
    results = [
        {"ground_truth": {"expected_policy_violation": "True"}, "policy_verdict": {"compliant": False}},
        {"ground_truth": {"expected_policy_violation": "False"}, "policy_verdict": {"compliant": True}},
        {"ground_truth": {"expected_policy_violation": "True"}, "policy_verdict": {"compliant": True}},
    ]
    assert policy_violation_accuracy(results) == 2 / 3


def test_hallucination_distribution_empty():
    assert hallucination_distribution([]) == {"count": 0}


def test_hallucination_distribution_skips_none_report_guardrails():
    results = [
        {"report_guardrails": {"hallucination": {"score": 0.4}}},
        {"report_guardrails": None},  # extraction failed upstream, no downstream call ran
    ]
    dist = hallucination_distribution(results)
    assert dist["count"] == 1
    assert dist["mean"] == 0.4


def test_hallucination_distribution_computes_stats():
    results = [
        {"report_guardrails": {"hallucination": {"score": 0.0}}},
        {"report_guardrails": {"hallucination": {"score": 1.0}}},
    ]
    dist = hallucination_distribution(results)
    assert dist["count"] == 2
    assert dist["mean"] == 0.5


def test_end_to_end_latency_computes_percentiles():
    results = [{"latency_ms": 100}, {"latency_ms": 200}, {"latency_ms": 300}]
    lat = end_to_end_latency(results)
    assert lat["count"] == 3
    assert lat["mean_ms"] == 200


def test_injection_catch_rate():
    class FakeResult:
        def __init__(self, flagged):
            self.flagged = flagged

    def fake_check(prompt):
        return FakeResult(flagged="bad" in prompt)

    rate = injection_catch_rate(["bad prompt", "good prompt"], fake_check)
    assert rate["caught"] == 1
    assert rate["catch_rate"] == 0.5
