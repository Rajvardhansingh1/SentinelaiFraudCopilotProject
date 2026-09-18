from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "frontend" / "app.py")


def test_playground_renders_and_blocks_attack(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    def fake_call_generate(session_id, user_content, timeout=15.0):
        return 400, {
            "error": {"code": "injection_detected", "message": "blocked"},
            "guardrails": {"injection": {"flagged": True, "matched_patterns": ["ignore_instructions"]}},
            "output": None,
        }

    monkeypatch.setattr("frontend.components.redteam_playground.call_generate", fake_call_generate)
    monkeypatch.setattr("frontend.app.ping_proxy", lambda: True)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.selectbox[0].select("Instruction override").run()
    at.button[0].click().run()

    assert any("Blocked" in md.value for md in at.error)
