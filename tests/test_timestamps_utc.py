"""D-051 regression: every API timestamp must carry an explicit UTC offset.
SQLite drops tzinfo; before the fix rows came back naive and the web read
them as local time, shifting every displayed time by the viewer's offset."""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from proxy.db.models import SecurityEvent
from proxy.db.session import SessionLocal, init_db
from proxy.events import record_event
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse


class FakeProvider:
    def generate(self, messages):
        return LLMResponse("ok", 1, 1, 1, "m", "fake")


def _is_utc_aware(value: str) -> bool:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.utcoffset() == timedelta(0)


def teardown_function():
    app.dependency_overrides.clear()
    rate_limiter.reset()


def test_call_log_timestamps_are_utc_aware():
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    client = TestClient(app)
    client.post("/v1/generate", json={"session_id": "tz", "operation": "playground",
                                      "messages": [{"role": "user", "content": "hi"}]})
    rows = client.get("/v1/calls").json()
    assert rows and all(_is_utc_aware(r["created_at"]) for r in rows)


def test_finding_run_and_dashboard_timestamps_are_utc_aware():
    client = TestClient(app)
    client.post("/v1/findings/sync")
    dash = client.get("/v1/security-dashboard").json()
    assert _is_utc_aware(dash["last_run_at"])
    assert all(_is_utc_aware(r["executed_at"]) for r in dash["recent_activity"])


def test_event_timestamps_are_utc_aware_and_round_trip_exactly():
    init_db()
    db = SessionLocal()
    stamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    event = record_event(db, event_type="attack_attempt", severity="high", category="c", source="t", summary="tz")
    event.created_at = stamp
    db.commit()
    db.refresh(event)
    assert event.created_at == stamp  # aware in, same aware instant out
    db.query(SecurityEvent).delete()
    db.commit()
    db.close()


def test_non_utc_input_is_normalized_to_the_same_instant():
    init_db()
    db = SessionLocal()
    ist = timezone(timedelta(hours=5, minutes=30))
    local = datetime(2026, 1, 2, 8, 34, 5, tzinfo=ist)  # == 03:04:05 UTC
    event = record_event(db, event_type="attack_attempt", severity="high", category="c", source="t", summary="tz2")
    event.created_at = local
    db.commit()
    db.refresh(event)
    assert event.created_at == local
    assert event.created_at.utcoffset() == timedelta(0)
    db.query(SecurityEvent).delete()
    db.commit()
    db.close()
