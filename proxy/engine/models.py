"""Core data model for SentinelAI's security testing engine (phase_dev_upgrade.md
Phase 3). Separates TEST DEFINITION -> EXECUTION -> EVALUATION -> RESULT/EVIDENCE.
No attack-specific logic lives here — that belongs in proxy/engine/plugins/*."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(str, Enum):
    """A security product must never collapse these into a single boolean
    (phase_dev_upgrade.md Phase 4) — the engine carries all five from the start."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    NOT_RUN = "NOT_RUN"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class RawExecution:
    """EXECUTION's output and the test's EVIDENCE — what actually happened,
    before any pass/fail judgement is applied."""

    raw_input: str
    raw_output: Any
    provider: str
    model: str
    status_code: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SecurityTest:
    """TEST DEFINITION. `run` performs EXECUTION (calls a provider/detector and
    returns evidence); `evaluate` performs EVALUATION (judges that evidence).
    A plugin owns both — the engine (runner.py) never branches on attack type."""

    id: str
    name: str
    category: str
    description: str
    severity: Severity
    attack_input: str
    expected_behavior: str
    run: Callable[["SecurityTest"], RawExecution]
    evaluate: Callable[[RawExecution], tuple[TestStatus, str]]


@dataclass(frozen=True)
class TestResult:
    """EVALUATION output, carrying everything Phase 5's Findings subsystem
    will need without re-running the test: id, evidence, timestamp, severity,
    model/provider, reproducibility."""

    test_id: str
    name: str
    category: str
    severity: Severity
    status: TestStatus
    detail: str
    evidence: RawExecution
    executed_at: datetime
    reproduction: dict[str, Any]
