import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unittest.mock import patch

from frontend.lib.dashboard_data import (
    cost_summary,
    fetch_calls,
    guardrail_catch_counts,
    hallucination_scores,
    latency_summary,
    traffic_by_operation,
)
from proxy.db.models import Base, CallLog


class FakeCall:
    def __init__(self, operation, guardrails, cost_estimate_usd, latency_ms):
        self.operation = operation
        self.guardrails = guardrails
        self.cost_estimate_usd = cost_estimate_usd
        self.latency_ms = latency_ms


def test_traffic_by_operation():
    calls = [FakeCall("playground", {}, 0, 10), FakeCall("playground", {}, 0, 10), FakeCall("extract", {}, 0, 10)]
    counts = traffic_by_operation(calls)
    assert counts == {"playground": 2, "extract": 1}


def test_guardrail_catch_counts():
    calls = [
        FakeCall("x", {"injection": {"flagged": True}, "pii": {"found": False}}, 0, 10),
        FakeCall("x", {"injection": {"flagged": False}, "pii": {"found": True}}, 0, 10),
    ]
    counts = guardrail_catch_counts(calls)
    assert counts == {"injection": 1, "pii": 1}


def test_hallucination_scores_skips_missing():
    calls = [FakeCall("x", {"hallucination": {"score": 0.3}}, 0, 10), FakeCall("x", {}, 0, 10)]
    assert hallucination_scores(calls) == [0.3]


def test_cost_summary():
    calls = [FakeCall("x", {}, 0.01, 10), FakeCall("x", {}, 0.03, 10)]
    summary = cost_summary(calls)
    assert summary["total_usd"] == 0.04
    assert round(summary["avg_usd"], 4) == 0.02


def test_cost_summary_empty():
    assert cost_summary([]) == {"total_usd": 0.0, "avg_usd": 0.0}


def test_fetch_calls_returns_empty_list_instead_of_raising_on_db_error():
    with patch("frontend.lib.dashboard_data.get_session") as mock_get_session:
        mock_get_session.return_value.query.side_effect = RuntimeError("db locked")
        assert fetch_calls() == []


def test_latency_summary():
    calls = [FakeCall("x", {}, 0, 100), FakeCall("x", {}, 0, 200)]
    summary = latency_summary(calls)
    assert summary["avg_ms"] == 150


def test_dashboard_metrics_match_real_stored_calllog_rows():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        s = Session()
        s.add(CallLog(session_id="s1", operation="playground", provider="fake", model="m", latency_ms=50, guardrails={"injection": {"flagged": True}}))
        s.add(CallLog(session_id="s1", operation="extract", provider="fake", model="m", latency_ms=100, guardrails={}))
        s.commit()

        rows = s.query(CallLog).order_by(CallLog.created_at.desc()).all()
        s.close()

        counts = traffic_by_operation(rows)
        assert counts == {"playground": 1, "extract": 1}
        catches = guardrail_catch_counts(rows)
        assert catches["injection"] == 1
    finally:
        engine.dispose()
        os.remove(path)
