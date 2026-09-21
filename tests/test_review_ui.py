import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from frontend.db.models import Base, ReviewDecision

APP_PATH = str(Path(__file__).resolve().parent.parent / "frontend" / "app.py")

FAKE_STATE = {
    "extracted_fields": {"vendor": "Acme", "date": "2026-01-01", "line_items": [], "total": 42.5},
    "forensics_result": {"tamper_likelihood": "low", "ela_score": 0.001, "exif_consistent": True, "exif_flags": []},
    "policy_verdict": {"compliant": True, "triggered_rules": []},
    "report_text": "The vendor is Acme, total 42.50.",
    "report_guardrails": {"hallucination": {"score": 0.1, "mode": "grounded"}},
    "errors": [],
}


def _isolated_session_factory():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session, path, engine


def _run_to_review_screen(monkeypatch, Session):
    monkeypatch.setattr("frontend.components.review_screen.run_on_receipt", lambda session_id, path: FAKE_STATE)
    monkeypatch.setattr("frontend.components.review_screen.get_session", lambda: Session())
    monkeypatch.setattr("frontend.app.ping_proxy", lambda: True)

    at = AppTest.from_file(APP_PATH)
    at.run(timeout=15)
    at.sidebar.radio[0].set_value("Review Receipt").run(timeout=15)

    genuine_button = next(b for b in at.button if "genuine" in b.label.lower())
    genuine_button.click().run(timeout=15)
    run_button = next(b for b in at.button if b.label == "Run analysis")
    run_button.click().run(timeout=15)
    return at


def test_review_screen_renders_evidence_after_running_sample(monkeypatch):
    Session, path, engine = _isolated_session_factory()
    try:
        at = _run_to_review_screen(monkeypatch, Session)
        assert not at.exception
        headers = {h.value for h in at.subheader}
        assert {"Extraction evidence", "Forensics evidence", "Policy evidence", "System Assessment (not a decision)", "Human Review — Final Decision"} <= headers
    finally:
        engine.dispose()
        os.remove(path)


def test_no_decision_recorded_without_clicking_approve_or_reject(monkeypatch):
    Session, path, engine = _isolated_session_factory()
    try:
        _run_to_review_screen(monkeypatch, Session)
        s = Session()
        try:
            assert s.query(ReviewDecision).count() == 0
        finally:
            s.close()
    finally:
        engine.dispose()
        os.remove(path)


def test_approve_records_a_review_decision(monkeypatch):
    Session, path, engine = _isolated_session_factory()
    try:
        at = _run_to_review_screen(monkeypatch, Session)
        approve_button = next(b for b in at.button if b.label == "Approve")
        approve_button.click().run(timeout=15)

        s = Session()
        try:
            rows = s.query(ReviewDecision).all()
            assert len(rows) == 1
            assert rows[0].human_decision == "approved"
        finally:
            s.close()
    finally:
        engine.dispose()
        os.remove(path)


def test_reject_records_a_rejected_decision(monkeypatch):
    Session, path, engine = _isolated_session_factory()
    try:
        at = _run_to_review_screen(monkeypatch, Session)
        reject_button = next(b for b in at.button if b.label == "Reject")
        reject_button.click().run(timeout=15)

        s = Session()
        try:
            rows = s.query(ReviewDecision).all()
            assert len(rows) == 1
            assert rows[0].human_decision == "rejected"
        finally:
            s.close()
    finally:
        engine.dispose()
        os.remove(path)
