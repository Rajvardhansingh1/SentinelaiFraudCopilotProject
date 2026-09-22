"""Regression guard for the Red-Team Playground's trial prompts and their
guardrail checks, as the *web* frontend actually sends them.

Reads web/lib/sample-attacks.ts and web/lib/api.ts's SYSTEM_PROMPT directly
from source, so any drift between the web presets, the Python mirror, and
the live detector fails here — not in front of a user."""

import os
import re
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from frontend.data.sample_attacks import SAMPLE_ATTACKS as PY_ATTACKS
from proxy.main import app, get_provider
from proxy.middleware import rate_limiter
from proxy.provider import LLMResponse

WEB = Path(__file__).parent.parent / "web" / "lib"


def _web_presets() -> list[dict]:
    src = (WEB / "sample-attacks.ts").read_text(encoding="utf-8")
    block = src.split("export const SAMPLE_ATTACKS", 1)[1].split("export const GENERIC_FALLBACK_RESPONSE", 1)[0]
    ids = re.findall(r'^\s{4}id: "([^"]+)"', block, re.M)
    prompts = re.findall(r'^\s{4}prompt: "([^"]+)"', block, re.M)
    patterns = [re.findall(r'"([^"]+)"', p) for p in re.findall(r"matched_patterns: \[([^\]]*)\]", block)]
    assert len(ids) == len(prompts) == len(patterns) > 0, "could not parse web/lib/sample-attacks.ts"
    return [{"id": i, "prompt": p, "patterns": pat} for i, p, pat in zip(ids, prompts, patterns)]


def _web_system_prompt() -> str:
    src = (WEB / "api.ts").read_text(encoding="utf-8")
    expr = src.split("export const SYSTEM_PROMPT =", 1)[1].split(";", 1)[0]
    return "".join(re.findall(r'"([^"]*)"', expr))


WEB_PRESETS = _web_presets()
SYSTEM_PROMPT = _web_system_prompt()


class FakeProvider:
    def generate(self, messages):
        return LLMResponse("ack", 1, 1, 5, "fake-model", "fake")


@pytest.fixture
def client():
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    yield TestClient(app)
    app.dependency_overrides.clear()
    rate_limiter.reset()


def _generate(client, session_id, content):
    return client.post(
        "/v1/generate",
        json={
            "session_id": session_id,
            "operation": "playground",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
            "schema_name": None,
            "grounding_context": None,
        },
    )


def test_web_presets_match_python_mirror():
    py = {a["id"]: (a["prompt"], a["cached_response"]["guardrails"]["injection"]["matched_patterns"]) for a in PY_ATTACKS}
    web = {a["id"]: (a["prompt"], a["patterns"]) for a in WEB_PRESETS}
    assert web == py


@pytest.mark.parametrize("preset", WEB_PRESETS, ids=lambda p: p["id"])
def test_each_web_preset_is_blocked_with_its_documented_patterns(client, preset):
    resp = _generate(client, f"guard-{preset['id']}", preset["prompt"])
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "injection_detected"
    assert body["guardrails"]["injection"]["flagged"] is True
    # The cached fallback the UI shows on 429 must never claim a pattern the live detector doesn't.
    assert set(preset["patterns"]).issubset(body["guardrails"]["injection"]["matched_patterns"])


@pytest.mark.parametrize(
    "prompt",
    ["What is the capital of France?", "Summarize the benefits of unit testing in two sentences."],
)
def test_benign_prompt_with_real_web_system_prompt_is_not_blocked(client, prompt):
    """D-033 regression: the playground's own anti-jailbreak system prompt must
    never self-trip the detector."""
    resp = _generate(client, "guard-benign", prompt)
    assert resp.status_code == 200
    assert resp.json()["guardrails"]["injection"]["flagged"] is False


def test_web_system_prompt_would_trip_detector_if_scanned():
    """Proves the D-033 guard above is meaningful: the system prompt really does
    contain attack-pattern phrasing, so scanning it would break every request."""
    from proxy.middleware.injection_detector import check_injection

    assert check_injection(SYSTEM_PROMPT).flagged is True
