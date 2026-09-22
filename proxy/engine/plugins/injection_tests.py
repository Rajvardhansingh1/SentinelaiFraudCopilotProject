"""Migrates the existing Sentinel injection/jailbreak tests (the playground's
4 sample attacks, already regression-tested against proxy/redteam/attack_library.py
in tests/test_sample_attacks.py) into the engine, without changing their
behavior. Prompts are imported from frontend/data/sample_attacks.py — the
existing source of truth — not re-typed here."""

from __future__ import annotations

from frontend.data.sample_attacks import SAMPLE_ATTACKS
from proxy.engine.models import Severity
from proxy.engine.plugins._common import injection_pattern_test
from proxy.engine.registry import register

# Same attacks, rated by what a successful bypass would let through in Fraud
# Copilot's context (D-002/D-004): approving a fraudulent claim outright is
# worse than merely leaking the system prompt. See docs/SECURITY_ENGINE.md's
# severity rubric.
_SEVERITY_BY_ID: dict[str, Severity] = {
    "instruction_override": Severity.HIGH,
    "dan_jailbreak": Severity.CRITICAL,
    "policy_override": Severity.CRITICAL,
    "developer_mode": Severity.MEDIUM,
}


@register
def build_injection_tests() -> list:
    return [
        injection_pattern_test(
            id=attack["id"],
            name=attack["label"],
            category="prompt_injection",
            description=f"Detector must flag: {attack['label']}",
            severity=_SEVERITY_BY_ID.get(attack["id"], Severity.MEDIUM),
            attack_input=attack["prompt"],
        )
        for attack in SAMPLE_ATTACKS
    ]
