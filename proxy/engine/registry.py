"""Plugin registry — the engine's only extension point. A new attack category
is a new plugin module calling `register()`; proxy/engine/runner.py and
proxy/main.py never need to know it exists."""

from __future__ import annotations

from typing import Callable

from proxy.engine.models import SecurityTest

_test_builders: list[Callable[[], list[SecurityTest]]] = []


def register(builder: Callable[[], list[SecurityTest]]) -> Callable[[], list[SecurityTest]]:
    _test_builders.append(builder)
    return builder


def all_tests() -> list[SecurityTest]:
    tests: list[SecurityTest] = []
    for builder in _test_builders:
        tests.extend(builder())
    return tests
